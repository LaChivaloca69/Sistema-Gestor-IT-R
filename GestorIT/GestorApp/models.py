import re
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
# ------------ MODELOS DE AREAS, PUESTOS Y PERSONAL ------------

# Ubicacion
class Area(models.Model):
    nombre_area = models.CharField(max_length=100)
    descripcion_area = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_area


class Puesto(models.Model):
    nombre_puesto = models.CharField(max_length=100)
    descripcion_puesto = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_puesto


class Personal(models.Model):
    numero_empleado = models.CharField(max_length=30, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personal_profile',
    )
    admin_requested = models.BooleanField(default=False, verbose_name="Solicita admin")
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    puesto = models.ForeignKey(Puesto, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_ingreso = models.DateField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.numero_empleado} - {self.nombre} {self.apellido_paterno}"


@receiver(post_delete, sender=Personal)
def delete_user_for_personal(sender, instance, **kwargs):
    if instance.user_id:
        get_user_model().objects.filter(pk=instance.user_id).delete()

# ------------ MODELO DE PROVEEDORES------------
class Proveedor(models.Model):
    nombre_proveedor = models.CharField(max_length=150)
    contacto = models.CharField(max_length=150, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_proveedor

# ------------ MODELOS DE UBICACION, EDIFICIO ------------
class Edificio(models.Model):
    nombre_edificio = models.CharField(max_length=100)
    descripcion_edificio = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_edificio


class ZonaEdificio(models.Model):
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='zonas')
    nombre_zona = models.CharField(max_length=100)
    descripcion_zona = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.edificio.nombre_edificio} - {self.nombre_zona}"


class Ubicacion(models.Model):
    edificio = models.ForeignKey(Edificio, on_delete=models.PROTECT)
    zona = models.ForeignKey(ZonaEdificio, on_delete=models.PROTECT)
    pasillo = models.CharField(max_length=50, blank=True, null=True)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.edificio} / {self.zona} / {self.referencia or 'Sin referencia'}"

# ------------ MODELOS DE EQUIPO(CATEGORIA, ESTADO, TIPO, ETC) ------------
class CategoriaEquipo(models.Model):
    nombre_categoria = models.CharField(max_length=100)
    descripcion_categoria = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_categoria


class EstadoEquipo(models.TextChoices):
    DISPONIBLE = "Disponible", "Disponible"
    ASIGNADO = "Asignado", "Asignado"
    EN_MANTENIMIENTO = "En Mantenimiento", "En Mantenimiento"
    BAJA = "Baja", "Baja"


class Equipo(models.Model):
    codigo_inventario = models.CharField(max_length=50, unique=True)
    numero_serie = models.CharField(max_length=100, unique=True, blank=True, null=True)
    categoria = models.ForeignKey(CategoriaEquipo, on_delete=models.PROTECT)
    marca = models.CharField(max_length=80, blank=True, null=True)
    modelo = models.CharField(max_length=80, blank=True, null=True)
    descripcion_equipo = models.CharField(max_length=255, blank=True, null=True)
    imagen = models.ImageField(upload_to='equipos', blank=True, null=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    estado_equipo = models.CharField(max_length=30, choices=EstadoEquipo.choices, default=EstadoEquipo.DISPONIBLE)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_alta = models.DateField(default=timezone.now)
    fecha_baja = models.DateField(blank=True, null=True)
    motivo_baja = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.codigo_inventario


class TipoMovimiento(models.TextChoices):
    DADA_DE_ALTA = "Dada de alta", "Dada de alta"
    DADA_DE_BAJA = "Dada de baja", "Dada de baja"
    ASIGNACION = "Asignacion de equipo", "Asignacion de equipo"
    CAMBIO_ASIGNACION = "Cambio de asignacion", "Cambio de asignacion"
    MANTENIMIENTO = "En mantenimiento", "En mantenimiento"
    CAMBIO_UBICACION = "Cambio de ubicacion", "Cambio de ubicacion"


class MovimientoEquipo(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    origen = models.CharField(max_length=150, blank=True, null=True)
    destino = models.CharField(max_length=150, blank=True, null=True)
    responsable = models.ForeignKey(Personal, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class EstadoAsignacion(models.TextChoices):
    ACTIVA = "Activa", "Activa"
    DEVUELTA = "Devuelta", "Devuelta"
    EXTRAVIADA = "Extraviada", "Extraviada"


class AsignacionEquipo(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='asignaciones')
    personal = models.ForeignKey(Personal, on_delete=models.CASCADE, related_name='equipos_asignados')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_devolucion = models.DateTimeField(blank=True, null=True)
    estado_asignacion = models.CharField(max_length=20, choices=EstadoAsignacion.choices, default=EstadoAsignacion.ACTIVA)
    observaciones = models.CharField(max_length=255, blank=True, null=True)

# ------------ MODELOS DE MANTENIMIENTO ------------
class TipoMantenimiento(models.TextChoices):
    PREVENTIVO = "Preventivo", "Preventivo"
    CORRECTIVO = "Correctivo", "Correctivo"
    PREDICTIVO = "Predictivo", "Predictivo"


class EstadoMantenimiento(models.TextChoices):
    PROGRAMADO = "Programado", "Programado"
    EN_PROCESO = "En Proceso", "En Proceso"
    COMPLETADO = "Completado", "Completado"
    CANCELADO = "Cancelado", "Cancelado"


class Mantenimiento(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='mantenimientos')
    tipo_mantenimiento = models.CharField(max_length=20, choices=TipoMantenimiento.choices)
    estado_mantenimiento = models.CharField(max_length=20, choices=EstadoMantenimiento.choices, default=EstadoMantenimiento.PROGRAMADO)
    fecha_programada = models.DateField()
    tecnico_responsable = models.CharField(max_length=150, blank=True, null=True)
    costo_mantenimiento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion_falla = models.CharField(max_length=255, blank=True, null=True)

    def folio_mantenimiento(self):
        if not self.pk:
            return "MAN---"
        fecha = self.fecha_programada or timezone.localdate()
        return f"MAN{self.pk:03d}-{fecha.strftime('%m%d%y')}"

    def __str__(self):
        return self.folio_mantenimiento()


class AgendaMantenimiento(models.Model):
    mantenimiento = models.OneToOneField(
        Mantenimiento,
        on_delete=models.CASCADE,
        related_name='cierre',
    )
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    acciones_realizadas = models.TextField(blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    proxima_fecha_mantenimiento = models.DateField(blank=True, null=True)


# ------------ TICKETS DE SUPPORT, CHECKS Y BITACORA ------------
# Support y Bitacora models se encuentran al final del archivo para evitar conflictos con migraciones que eliminan campos de Equipo.
class TipoTicketSupport(models.TextChoices):
    ADMINISTRACION = "ADMINISTRACION", "ADMINISTRACION"
    BPCS = "BPCS", "BPCS"
    HARDWARE = "HARDWARE", "HARDWARE"
    HELPDESK = "HELPDESK", "HELPDESK"
    TELEFONIA = "TELEFONIA", "TELEFONIA"
    SOFTWARE = "SOFTWARE", "SOFTWARE"


class TipoEquipoSupport(models.TextChoices):
    COMPUTADORA = "Computadora", "Computadora"
    LAPTOP = "Laptop", "Laptop"
    IMPRESORA = "Impresora", "Impresora"
    TELEFONO = "Telefono", "Telefono"
    ESCANER = "Escaner", "Escaner"
    TABLET = "Tablet", "Tablet"
    OTRO = "Otro", "Otro"


class EstadoSupport(models.TextChoices):
    ABIERTO = "Abierto", "Abierto"
    EN_REVISION = "En Revision", "En Revision"
    EN_PROCESO = "En Proceso", "En Proceso"
    CERRADO = "Cerrado", "Cerrado"


class PrioridadSupport(models.TextChoices):
    BAJA = "Baja", "Baja"
    MEDIA = "Media", "Media"
    ALTA = "Alta", "Alta"
    URGENTE = "Urgente", "Urgente"



class TicketIT(models.Model):
    FOLIO_PREFIX = 'SPR0-'
    FOLIO_WIDTH = 6

    folio_ticket = models.CharField(max_length=30, unique=True)
    fecha_support = models.DateTimeField(default=timezone.now)
    requerimiento = models.CharField(max_length=180, default='')
    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_support',
        verbose_name='Area',
    )
    puesto = models.ForeignKey(
        Puesto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_support_puesto',
        verbose_name='Puesto',
    )
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_support_solicitados',
        verbose_name='Solicitado por',
    )
    tipo_ticket = models.CharField(max_length=30, choices=TipoTicketSupport.choices, default=TipoTicketSupport.HELPDESK)
    sub_tipo_ticket = models.CharField(max_length=150, blank=True, null=True)
    prioridad = models.CharField(max_length=10, choices=PrioridadSupport.choices, default=PrioridadSupport.MEDIA)
    equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_equipo = models.ForeignKey(CategoriaEquipo, on_delete=models.PROTECT, null=True, blank=True)
    otro_tipo_equipo = models.CharField(max_length=120, blank=True, null=True)
    detalle = models.CharField(max_length=255, blank=True, null=True)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='support', blank=True, null=True)
    status = models.CharField(max_length=20, choices=EstadoSupport.choices, default=EstadoSupport.ABIERTO)

    class Meta:
        verbose_name = 'Support'
        verbose_name_plural = 'Support'

    @classmethod
    def _next_folio_ticket(cls):
        folios = cls.objects.filter(
            folio_ticket__startswith=cls.FOLIO_PREFIX
        ).order_by('-folio_ticket').values_list('folio_ticket', flat=True)

        for folio in folios:
            suffix = folio[len(cls.FOLIO_PREFIX):]
            if suffix.isdigit():
                next_number = int(suffix) + 1
                return f'{cls.FOLIO_PREFIX}{next_number:0{cls.FOLIO_WIDTH}d}'

        return f'{cls.FOLIO_PREFIX}{1:0{cls.FOLIO_WIDTH}d}'

    def clean(self):
        if self.folio_ticket:
            folio = self.folio_ticket.upper()
            if not re.fullmatch(r'SPR0-\d{6}', folio):
                # Permite editar registros legacy sin cambiarles el folio.
                if not self.pk:
                    raise ValidationError({'folio_ticket': 'El folio del Support debe tener formato SPR0-000001.'})
                original_folio = TicketIT.objects.filter(pk=self.pk).values_list('folio_ticket', flat=True).first()
                if not original_folio or original_folio.upper() != folio:
                    raise ValidationError({'folio_ticket': 'El folio del Support debe tener formato SPR0-000001.'})
        if self.tipo_equipo and self.tipo_equipo.nombre_categoria.strip().lower() == "otro":
            if not self.otro_tipo_equipo:
                raise ValidationError({'otro_tipo_equipo': 'Especifica el tipo de equipo cuando seleccionas "Otro".'})

    def save(self, *args, **kwargs):
        if not self.tipo_equipo or self.tipo_equipo.nombre_categoria.strip().lower() != "otro":
            self.otro_tipo_equipo = None

        if self.folio_ticket:
            self.folio_ticket = self.folio_ticket.upper()
            super().save(*args, **kwargs)
            return

        # Genera folio automatico y reintenta ante colision de concurrencia.
        for _ in range(3):
            self.folio_ticket = self._next_folio_ticket()
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.folio_ticket = None

        raise IntegrityError('No se pudo generar un folio unico para Support.')

    def __str__(self):
        return self.folio_ticket


class SeguimientoTicket(models.Model):
    ticket = models.OneToOneField(TicketIT, on_delete=models.CASCADE, related_name='ticket_check')
    folio_check = models.CharField(max_length=30, blank=True, null=True)
    fecha_check = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='checks_resueltos',
    )
    solucion = models.TextField(default='')
    observacion = models.TextField(blank=True, null=True)
    ya_terminado = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Check'
        verbose_name_plural = 'Check'

    def clean(self):
        if self.folio_check:
            folio = self.folio_check.upper()
            if not (re.fullmatch(r'SPR0-\d{6}', folio) or folio.startswith('SPRT-')):
                raise ValidationError({'folio_check': 'El folio de Check debe tener formato SPR0-000001.'})
        if self.ticket_id and self.folio_check and self.folio_check.upper() != self.ticket.folio_ticket:
            raise ValidationError({'folio_check': 'El folio de Check debe coincidir con el folio del Support seleccionado.'})

    def save(self, *args, **kwargs):
        if self.ticket_id and self.ticket and self.ticket.folio_ticket:
            self.folio_check = self.ticket.folio_ticket
        if self.folio_check:
            self.folio_check = self.folio_check.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.folio_check or f'Check {self.pk}'


class Bitacora(models.Model):
    folio_bitacora = models.CharField(max_length=30, unique=True)
    fecha_bitacora = models.DateTimeField(default=timezone.now)
    situacion = models.CharField(max_length=180)
    descripcion_situacion = models.TextField()

    class Meta:
        verbose_name = 'Bitacora'
        verbose_name_plural = 'Bitacora'

    def clean(self):
        if self.folio_bitacora and not self.folio_bitacora.upper().startswith('BIT-'):
            raise ValidationError({'folio_bitacora': 'El folio de Bitacora debe iniciar con BIT-.'})

    def save(self, *args, **kwargs):
        if self.folio_bitacora:
            self.folio_bitacora = self.folio_bitacora.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.folio_bitacora


class Answer(models.Model):
    bitacora = models.ForeignKey(Bitacora, on_delete=models.CASCADE, related_name='answers')
    folio_answer = models.CharField(max_length=30)
    fecha_answer = models.DateTimeField(default=timezone.now)
    solucion = models.CharField(max_length=180)
    descripcion_solucion = models.TextField()

    class Meta:
        verbose_name = 'Answer'
        verbose_name_plural = 'Answer'

    def clean(self):
        if self.folio_answer and not self.folio_answer.upper().startswith('BIT-'):
            raise ValidationError({'folio_answer': 'El folio de Answer debe iniciar con BIT-.'})
        if self.bitacora_id and self.folio_answer and self.folio_answer.upper() != self.bitacora.folio_bitacora:
            raise ValidationError({'folio_answer': 'El folio de Answer debe coincidir con el folio de la Bitacora seleccionada.'})

    def save(self, *args, **kwargs):
        if self.bitacora_id and self.bitacora and self.bitacora.folio_bitacora:
            self.folio_answer = self.bitacora.folio_bitacora
        if self.folio_answer:
            self.folio_answer = self.folio_answer.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.folio_answer} - {self.solucion}'


# ------------ MODELOS DE PRESUPUESTOS Y COMPRAS ------------
class EstadoPresupuesto(models.TextChoices):
    BORRADOR = "Borrador", "Borrador"
    EN_PROCESO = "En Proceso", "En Proceso"
    TERMINADO = "Terminado", "Terminado"
    CANCELADO = "Cancelado", "Cancelado"


class Presupuesto(models.Model):
    folio_presupuesto = models.CharField(max_length=30, unique=True)
    cliente_o_area = models.CharField(max_length=150)
    elaborado_por = models.CharField(max_length=150)
    numero_pedimiento = models.CharField(max_length=50, null=True)
    numero_importacion = models.CharField(max_length=50, null=True)
    fecha_compra = models.DateField(null=True)
    archivo_pdf = models.FileField(upload_to='presupuestos', blank=True, null=True)
    estado_presupuesto = models.CharField(
        max_length=30,
        choices=EstadoPresupuesto.choices,
        default=EstadoPresupuesto.BORRADOR,
    )
    notas = models.CharField(max_length=255, blank=True, null=True)


class DetallePresupuesto(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='detalles')
    concepto = models.CharField(max_length=150)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    importe = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class CompraMaterial(models.Model):
    folio_compra = models.CharField(max_length=30, unique=True)
    fecha_compra = models.DateField()
    archivo_pdf = models.FileField(upload_to='compras_material', blank=True, null=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    solicitado_por = models.CharField(max_length=150, blank=True, null=True)
    estado_compra = models.CharField(
        max_length=30,
        choices=(
            ("Solicitada", "Solicitada"),
            ("En Proceso", "En Proceso"),
            ("Terminado", "Terminado"),
            ("Cancelada", "Cancelada"),
        ),
        default="Solicitada",
    )
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class DetalleCompraMaterial(models.Model):
    compra = models.ForeignKey(CompraMaterial, on_delete=models.CASCADE, related_name='detalles')
    concepto = models.CharField(max_length=150)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    importe = models.DecimalField(max_digits=12, decimal_places=2, default=0)