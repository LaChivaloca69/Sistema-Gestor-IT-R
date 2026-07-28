import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
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
# --- Categoria de equipo ------
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

# --- Equipo ------
class Equipo(models.Model):
    codigo_inventario = models.CharField(max_length=50, unique=True)
    numero_serie = models.CharField(max_length=100, unique=True, blank=True, null=True)
    categoria = models.ForeignKey(CategoriaEquipo, on_delete=models.PROTECT)
    marca = models.CharField(max_length=80, blank=True, null=True)
    modelo = models.CharField(max_length=80, blank=True, null=True)
    # numero de pedimiento es un campo opcional que puede ser nulo o vacío
    Numero_Pedimiento = models.CharField(max_length=15, blank=True, null=True)
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

    @property
    def asignacion_activa(self):
        return (
            self.asignaciones.filter(estado_asignacion=EstadoAsignacion.ACTIVA)
            .select_related('personal')
            .order_by('-fecha_asignacion')
            .first()
        )

    @property
    def puede_asignarse(self):
        if not self.activo:
            return False
        return self.estado_equipo not in {
            EstadoEquipo.BAJA,
            EstadoEquipo.EN_MANTENIMIENTO,
        }

    @property
    def puede_devolver(self):
        if self.estado_equipo == EstadoEquipo.BAJA:
            return False
        return self.asignacion_activa is not None

    @property
    def puede_dar_de_baja(self):
        return self.estado_equipo not in {
            EstadoEquipo.BAJA,
            EstadoEquipo.EN_MANTENIMIENTO,
        }

    @property
    def puede_reactivar(self):
        return self.estado_equipo == EstadoEquipo.BAJA

    @property
    def puede_cambiar_ubicacion(self):
        return self.estado_equipo != EstadoEquipo.BAJA

    @property
    def puede_eliminar_fisico(self):
        if self.asignaciones.exists() or self.mantenimientos.exists():
            return False
        if self.ticketit_set.exists():
            return False
        return not self.movimientos.exclude(
            tipo_movimiento=TipoMovimiento.DADA_DE_ALTA
        ).exists()


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

    @property
    def tiene_cierre(self):
        try:
            return self.cierre is not None
        except ObjectDoesNotExist:
            return False

    @property
    def puede_iniciar(self):
        return self.estado_mantenimiento == EstadoMantenimiento.PROGRAMADO

    @property
    def puede_cancelar(self):
        return self.estado_mantenimiento in {
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        }

    @property
    def puede_completar(self):
        return self.estado_mantenimiento in {
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        } and not self.tiene_cierre

    @property
    def puede_reabrir(self):
        return self.estado_mantenimiento in {
            EstadoMantenimiento.COMPLETADO,
            EstadoMantenimiento.CANCELADO,
        }

    def iniciar(self, save=True):
        if not self.puede_iniciar:
            raise ValidationError('Solo se puede iniciar un mantenimiento Programado.')
        self.estado_mantenimiento = EstadoMantenimiento.EN_PROCESO
        if save:
            self.save(update_fields=['estado_mantenimiento'])
        return self.estado_mantenimiento

    def cancelar(self, save=True):
        if not self.puede_cancelar:
            raise ValidationError('Solo se puede cancelar un mantenimiento Programado o En Proceso.')
        self.estado_mantenimiento = EstadoMantenimiento.CANCELADO
        if save:
            self.save(update_fields=['estado_mantenimiento'])
        return self.estado_mantenimiento

    def marcar_completado(self, save=True):
        self.estado_mantenimiento = EstadoMantenimiento.COMPLETADO
        if save:
            self.save(update_fields=['estado_mantenimiento'])
        return self.estado_mantenimiento

    def reabrir(self, save=True):
        if not self.puede_reabrir:
            raise ValidationError('Solo se pueden reabrir mantenimientos Completados o Cancelados.')
        if self.estado_mantenimiento == EstadoMantenimiento.COMPLETADO and self.tiene_cierre:
            # Queda En Proceso para permitir actualizar el cierre o continuar trabajo.
            self.estado_mantenimiento = EstadoMantenimiento.EN_PROCESO
        else:
            self.estado_mantenimiento = EstadoMantenimiento.PROGRAMADO
        if save:
            self.save(update_fields=['estado_mantenimiento'])
        return self.estado_mantenimiento

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


# Horas calendario para respuesta/atencion segun prioridad (aviso en panel, sin email).
SLA_HORAS_POR_PRIORIDAD = {
    PrioridadSupport.URGENTE: 4,
    PrioridadSupport.ALTA: 24,
    PrioridadSupport.MEDIA: 72,
    PrioridadSupport.BAJA: 168,
}


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
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_support_asignados',
        verbose_name='Asignado a',
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

    @property
    def puede_marcar_en_revision(self):
        return self.status == EstadoSupport.ABIERTO and not self.seguimientos.exists()

    @property
    def puede_reabrir(self):
        return self.status == EstadoSupport.CERRADO

    @property
    def tiene_seguimientos(self):
        return self.seguimientos.exists()

    @property
    def puede_eliminar(self):
        return not self.tiene_seguimientos

    @property
    def sla_horas_objetivo(self):
        return SLA_HORAS_POR_PRIORIDAD.get(self.prioridad, SLA_HORAS_POR_PRIORIDAD[PrioridadSupport.MEDIA])

    @property
    def sla_fecha_limite(self):
        if not self.fecha_support:
            return None
        return self.fecha_support + timedelta(hours=self.sla_horas_objetivo)

    @property
    def sla_aplica(self):
        return self.status != EstadoSupport.CERRADO

    @property
    def sla_vencido(self):
        if not self.sla_aplica:
            return False
        limite = self.sla_fecha_limite
        if not limite:
            return False
        return timezone.now() > limite

    @property
    def sla_estado(self):
        if not self.sla_aplica:
            return "cerrado"
        if self.sla_vencido:
            return "vencido"
        limite = self.sla_fecha_limite
        if not limite:
            return "ok"
        restante = limite - timezone.now()
        # Aviso "por vencer" si queda menos del 25% del SLA o menos de 4 horas.
        umbral = min(timedelta(hours=4), timedelta(hours=self.sla_horas_objetivo) * 0.25)
        if restante <= umbral:
            return "por_vencer"
        return "ok"

    def refresh_status_from_followups(self, save=True):
        """
        Flujo automatico:
        - Sin seguimientos: Abierto (o En Revision si ya se tomo el ticket)
        - Ultimo seguimiento abierto: En Proceso
        - Ultimo seguimiento concluido: Cerrado
        """
        ultimo_seguimiento = self.seguimientos.order_by('-fecha_check', '-pk').first()

        if ultimo_seguimiento is None:
            if self.status == EstadoSupport.EN_REVISION:
                nuevo_status = EstadoSupport.EN_REVISION
            else:
                nuevo_status = EstadoSupport.ABIERTO
        elif ultimo_seguimiento.ya_terminado:
            nuevo_status = EstadoSupport.CERRADO
        else:
            nuevo_status = EstadoSupport.EN_PROCESO

        if self.status != nuevo_status:
            self.status = nuevo_status
            if save:
                self.save(update_fields=['status'])

        return self.status

    def marcar_en_revision(self, save=True):
        if not self.puede_marcar_en_revision:
            raise ValidationError(
                'Solo se puede marcar En Revision un ticket Abierto sin seguimientos.'
            )
        self.status = EstadoSupport.EN_REVISION
        if save:
            self.save(update_fields=['status'])
        return self.status

    def reabrir(self, usuario=None, motivo=''):
        if not self.puede_reabrir:
            raise ValidationError('Solo se pueden reabrir tickets Cerrados.')

        texto = (motivo or '').strip() or 'Ticket reabierto.'
        SeguimientoTicket(
            ticket=self,
            usuario=usuario,
            avance_realizado=texto,
            pendiente='',
            proximo_paso='',
            solucion='',
            observacion='Reapertura del ticket.',
            ya_terminado=False,
        ).save()
        self.refresh_from_db(fields=['status'])
        return self.status

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
    ticket = models.ForeignKey(TicketIT, on_delete=models.CASCADE, related_name='seguimientos')
    folio_check = models.CharField(max_length=30, blank=True, null=True)
    fecha_check = models.DateTimeField(default=timezone.now)
    avance_realizado = models.TextField(blank=True, null=True)
    pendiente = models.TextField(blank=True, null=True)
    proximo_paso = models.TextField(blank=True, null=True)
    fecha_proximo_seguimiento = models.DateField(blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='checks_resueltos',
    )
    solucion = models.TextField(default='')
    observacion = models.TextField(blank=True, null=True)
    ya_terminado = models.BooleanField(default=False)

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
        if self.ya_terminado and not (self.solucion or '').strip():
            raise ValidationError({'solucion': 'Indica la solucion al concluir el seguimiento.'})

    def save(self, *args, **kwargs):
        previous_ticket_id = None
        if self.pk:
            previous_ticket_id = type(self).objects.filter(pk=self.pk).values_list('ticket_id', flat=True).first()

        if self.ticket_id and self.ticket and self.ticket.folio_ticket:
            self.folio_check = self.ticket.folio_ticket
        if self.folio_check:
            self.folio_check = self.folio_check.upper()
        super().save(*args, **kwargs)

        if self.ticket_id:
            self.ticket.refresh_status_from_followups()

        if previous_ticket_id and previous_ticket_id != self.ticket_id:
            previous_ticket = TicketIT.objects.filter(pk=previous_ticket_id).first()
            if previous_ticket:
                previous_ticket.refresh_status_from_followups()

    def delete(self, *args, **kwargs):
        ticket = self.ticket
        super().delete(*args, **kwargs)
        if ticket:
            ticket.refresh_status_from_followups()

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


# ------------ MODELOS DE ORDENES DE COMPRA ------------
class EstadoOrdenCompra(models.TextChoices):
    BORRADOR = "Borrador", "Borrador"
    EN_PROCESO = "En Proceso", "En Proceso"
    TERMINADO = "Terminado", "Terminado"
    CANCELADO = "Cancelado", "Cancelado"


# Alias legacy para no romper imports antiguos durante la migracion.
EstadoPresupuesto = EstadoOrdenCompra


class OrigenOrdenCompra(models.TextChoices):
    CREADO = "CREADO", "Creado en sistema"
    SUBIDO = "SUBIDO", "Subido existente"


class TipoMoneda(models.TextChoices):
    MXN = "MXN", "Pesos (MXN)"
    USD = "USD", "Dolares (USD)"


class IvaOpcion(models.TextChoices):
    OCHO = "8", "8%"
    DIECISEIS = "16", "16%"
    OTRO = "OTRO", "Otro"


class TipoPlantillaDocumento(models.TextChoices):
    DOCX = "DOCX", "Word (.docx)"
    XLSX = "XLSX", "Excel (.xlsx)"
    PDF = "PDF", "PDF"


class PlantillaDocumento(models.Model):
    """Plantilla reutilizable (Word, Excel o PDF) para generar ordenes de compra.

    ``campos`` guarda la lista de nombres de campo detectados automaticamente
    al subir el archivo (marcadores ``{{campo}}`` en docx/xlsx, o nombres de
    los campos de formulario AcroForm en un PDF).
    """

    nombre = models.CharField(max_length=150)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    tipo_archivo = models.CharField(max_length=10, choices=TipoPlantillaDocumento.choices)
    archivo = models.FileField(upload_to='plantillas_orden_compra')
    campos = models.JSONField(default=list, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class OrdenCompra(models.Model):
    FOLIO_PREFIX = 'OC-'
    FOLIO_WIDTH = 6

    folio_orden = models.CharField(max_length=30, unique=True, blank=True)
    elaborado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_compra_elaboradas',
    )
    origen = models.CharField(
        max_length=10,
        choices=OrigenOrdenCompra.choices,
        default=OrigenOrdenCompra.CREADO,
    )
    fecha = models.DateField(default=timezone.now, blank=True, null=True)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_compra',
    )
    tipo_moneda = models.CharField(
        max_length=3,
        choices=TipoMoneda.choices,
        default=TipoMoneda.MXN,
        blank=True,
    )
    iva_opcion = models.CharField(
        max_length=4,
        choices=IvaOpcion.choices,
        default=IvaOpcion.DIECISEIS,
        blank=True,
    )
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=16)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    iva_monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    comentarios = models.TextField(blank=True, null=True)
    notas = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(
        max_length=30,
        choices=EstadoOrdenCompra.choices,
        default=EstadoOrdenCompra.BORRADOR,
    )
    archivo_pdf = models.FileField(upload_to='ordenes_compra', blank=True, null=True)
    plantilla = models.ForeignKey(
        PlantillaDocumento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_compra',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en', '-pk']
        verbose_name = 'Orden de compra'
        verbose_name_plural = 'Ordenes de compra'

    def __str__(self):
        return self.folio_orden or f'Orden {self.pk}'

    @classmethod
    def _next_folio_orden(cls):
        folios = cls.objects.filter(
            folio_orden__startswith=cls.FOLIO_PREFIX
        ).order_by('-folio_orden').values_list('folio_orden', flat=True)

        for folio in folios:
            suffix = folio[len(cls.FOLIO_PREFIX):]
            if suffix.isdigit():
                next_number = int(suffix) + 1
                return f'{cls.FOLIO_PREFIX}{next_number:0{cls.FOLIO_WIDTH}d}'

        return f'{cls.FOLIO_PREFIX}{1:0{cls.FOLIO_WIDTH}d}'

    def recalcular_totales(self, save=True):
        from decimal import Decimal

        subtotal = Decimal('0')
        for detalle in self.detalles.all():
            importe = (detalle.cantidad or Decimal('0')) * (detalle.precio_unitario or Decimal('0'))
            if detalle.importe != importe:
                detalle.importe = importe
                detalle.save(update_fields=['importe'])
            subtotal += importe

        porcentaje = self.iva_porcentaje or Decimal('0')
        iva_monto = (subtotal * porcentaje / Decimal('100')).quantize(Decimal('0.01'))
        total = subtotal + iva_monto

        self.subtotal = subtotal
        self.iva_monto = iva_monto
        self.total = total
        if save and self.pk:
            self.save(update_fields=['subtotal', 'iva_monto', 'total'])
        return self

    def clean(self):
        if self.origen == OrigenOrdenCompra.CREADO and not self.proveedor_id:
            raise ValidationError({'proveedor': 'El proveedor es obligatorio al crear una orden.'})
        if self.iva_opcion == IvaOpcion.OCHO:
            self.iva_porcentaje = 8
        elif self.iva_opcion == IvaOpcion.DIECISEIS:
            self.iva_porcentaje = 16
        elif self.iva_opcion == IvaOpcion.OTRO and self.iva_porcentaje is None:
            raise ValidationError({'iva_porcentaje': 'Indica el porcentaje de IVA.'})

    def save(self, *args, **kwargs):
        if self.folio_orden:
            self.folio_orden = self.folio_orden.upper().strip()
            super().save(*args, **kwargs)
            return

        for _ in range(3):
            self.folio_orden = self._next_folio_orden()
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.folio_orden = None

        raise IntegrityError('No se pudo generar un folio unico para la orden de compra.')


class DetalleOrdenCompra(models.Model):
    orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='detalles')
    id_producto = models.CharField(max_length=80, blank=True, null=True)
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    importe = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['pk']
        verbose_name = 'Detalle de orden de compra'
        verbose_name_plural = 'Detalles de orden de compra'

    def save(self, *args, **kwargs):
        from decimal import Decimal
        self.importe = (self.cantidad or Decimal('0')) * (self.precio_unitario or Decimal('0'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.orden.folio_orden} - {self.descripcion}'


# ------------ HISTORIAL GENERAL DE ACTIVIDAD ------------
class ModuloHistorial(models.TextChoices):
    TICKET = "ticket", "Tickets de soporte"
    SEGUIMIENTO = "seguimiento", "Seguimiento de tickets"
    EQUIPO = "equipo", "Equipos"
    ASIGNACION = "asignacion", "Asignaciones de equipo"
    MOVIMIENTO_EQUIPO = "movimiento_equipo", "Movimientos de equipo"
    PERSONAL = "personal", "Personal"
    MANTENIMIENTO = "mantenimiento", "Mantenimiento"
    ORDEN_COMPRA = "orden_compra", "Ordenes de compra"
    BITACORA = "bitacora", "Bitacora"
    SISTEMA = "sistema", "Sistema"


class AccionHistorial(models.TextChoices):
    CREACION = "creacion", "Creacion"
    ACTUALIZACION = "actualizacion", "Actualizacion"
    ELIMINACION = "eliminacion", "Eliminacion"
    CAMBIO_ESTADO = "cambio_estado", "Cambio de estado"
    ASIGNACION = "asignacion", "Asignacion"
    DEVOLUCION = "devolucion", "Devolucion"
    OTRO = "otro", "Otro"


class NivelHistorial(models.TextChoices):
    INFO = "info", "Informativo"
    ADVERTENCIA = "advertencia", "Advertencia"
    CRITICO = "critico", "Critico"


class HistorialActividad(models.Model):
    """Registro inmutable de acciones relevantes en el sistema."""

    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    modulo = models.CharField(max_length=32, choices=ModuloHistorial.choices, db_index=True)
    accion = models.CharField(max_length=24, choices=AccionHistorial.choices, db_index=True)
    nivel = models.CharField(
        max_length=16,
        choices=NivelHistorial.choices,
        default=NivelHistorial.INFO,
        db_index=True,
    )
    es_automatico = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True si lo genero el sistema (ej. movimiento al dar de alta un equipo).",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historial_actividades",
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    objeto_tipo = models.CharField(max_length=80, blank=True)
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    objeto_etiqueta = models.CharField(max_length=180, blank=True)
    # Entidad relacionada: contexto padre (ej. ticket de un seguimiento, equipo de una asignacion).
    entidad_relacionada_tipo = models.CharField(max_length=80, blank=True)
    entidad_relacionada_id = models.PositiveIntegerField(null=True, blank=True)
    entidad_relacionada_etiqueta = models.CharField(max_length=180, blank=True)
    enlace_nombre = models.CharField(max_length=80, blank=True)
    enlace_pk = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(blank=True, null=True)
    # Politica de retencion: primero se archiva (oculto de la vista activa) y luego se puede purgar.
    archivado = models.BooleanField(default=False, db_index=True)
    fecha_archivado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "Historial de actividad"
        verbose_name_plural = "Historial de actividades"

    def __str__(self):
        return f"{self.get_modulo_display()} - {self.titulo}"

