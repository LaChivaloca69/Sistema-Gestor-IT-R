import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import RegexValidator
from django.db import IntegrityError, models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from .media_security import (
    equipo_imagen_upload_to,
    orden_pdf_upload_to,
    plantilla_archivo_upload_to,
    ticket_comentario_upload_to,
    ticket_imagen_upload_to,
)
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
    ubicacion = models.ForeignKey(
        "Ubicacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Espacio fisico",
        help_text="Puesto fijo del empleado. Vacio si no tiene escritorio asignado.",
    )
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
class TipoProveedor(models.TextChoices):
    HARDWARE = "Hardware", "Hardware"
    SOFTWARE = "Software", "Software"
    MANTENIMIENTO = "Mantenimiento", "Mantenimiento"
    TELECOMUNICACIONES = "Telecomunicaciones", "Telecomunicaciones"
    CONSUMIBLES = "Consumibles", "Consumibles"
    OTRO = "Otro", "Otro"


class Proveedor(models.Model):
    CODIGO_PREFIX = "PROV-"
    CODIGO_WIDTH = 6

    codigo_interno = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Codigo interno",
    )
    nombre_proveedor = models.CharField(max_length=150, verbose_name="Nombre comercial")
    razon_social = models.CharField(max_length=200, blank=True, null=True)
    rfc = models.CharField(max_length=13, blank=True, null=True, verbose_name="RFC")
    tipo = models.CharField(
        max_length=30,
        choices=TipoProveedor.choices,
        blank=True,
        null=True,
        verbose_name="Tipo de proveedor",
    )
    contacto = models.CharField(max_length=150, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    sitio_web = models.URLField(blank=True, null=True, verbose_name="Sitio web")
    direccion = models.CharField(max_length=255, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=100, blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, blank=True, null=True, verbose_name="Codigo postal")
    notas = models.TextField(
        blank=True,
        null=True,
        help_text="Condiciones de pago, garantia, observaciones, etc.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre_proveedor"]
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        if self.codigo_interno:
            return f"{self.codigo_interno} — {self.nombre_proveedor}"
        return self.nombre_proveedor

    @classmethod
    def _next_codigo_interno(cls):
        codigos = (
            cls.objects.filter(codigo_interno__startswith=cls.CODIGO_PREFIX)
            .order_by("-codigo_interno")
            .values_list("codigo_interno", flat=True)
        )
        for codigo in codigos:
            suffix = codigo[len(cls.CODIGO_PREFIX):]
            if suffix.isdigit():
                next_number = int(suffix) + 1
                return f"{cls.CODIGO_PREFIX}{next_number:0{cls.CODIGO_WIDTH}d}"
        return f"{cls.CODIGO_PREFIX}{1:0{cls.CODIGO_WIDTH}d}"

    def save(self, *args, **kwargs):
        if not (self.codigo_interno or "").strip():
            self.codigo_interno = self._next_codigo_interno()
        super().save(*args, **kwargs)

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
    es_stock_default = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Almacen / stock por defecto",
        help_text="Espacio al que regresan los equipos al devolverlos a stock.",
    )

    def __str__(self):
        return f"{self.edificio} / {self.zona} / {self.referencia or 'Sin referencia'}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.es_stock_default:
            type(self).objects.filter(es_stock_default=True).exclude(pk=self.pk).update(
                es_stock_default=False
            )

# ------------ MODELOS DE EQUIPO(CATEGORIA, ESTADO, TIPO, ETC) ------------
# --- Categoria de equipo ------
class TipoCategoriaInventario(models.TextChoices):
    EQUIPO = "Equipo", "Equipo"
    PERIFERICO = "Periferico", "Periferico"
    HERRAMIENTA = "Herramienta", "Herramienta"
    CONSUMIBLE = "Consumible", "Consumible"


class CategoriaEquipo(models.Model):
    nombre_categoria = models.CharField(max_length=100)
    descripcion_categoria = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(
        max_length=20,
        choices=TipoCategoriaInventario.choices,
        default=TipoCategoriaInventario.EQUIPO,
        db_index=True,
        verbose_name="Tipo de inventario",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo", "nombre_categoria"]
        verbose_name = "Categoria de inventario"
        verbose_name_plural = "Categorias de inventario"

    def __str__(self):
        return self.nombre_categoria


class EstadoEquipo(models.TextChoices):
    DISPONIBLE = "En Stock", "En Stock"
    ASIGNADO = "Asignado", "Asignado"
    EN_MANTENIMIENTO = "En Mantenimiento", "En Mantenimiento"
    BAJA = "Baja", "Baja"


class OrigenAltaEquipo(models.TextChoices):
    COMPRA = "Compra", "Compra (con OC)"
    LEGADO = "Legado", "Legado / historico"
    DONACION = "Donacion", "Donacion"
    TRANSFERENCIA = "Transferencia", "Transferencia"
    OTRO = "Otro", "Otro"


# --- Equipo ------
class Equipo(models.Model):
    codigo_inventario = models.CharField(max_length=50, unique=True)
    numero_serie = models.CharField(max_length=100, unique=True, blank=True, null=True)
    tag_1 = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        verbose_name="Tag 1",
        help_text="Opcional. Exactamente 6 digitos.",
        validators=[
            RegexValidator(
                regex=r"^\d{6}$",
                message="Tag 1 debe tener exactamente 6 digitos.",
            )
        ],
    )
    tag_2 = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        verbose_name="Tag 2",
        help_text="Opcional. Exactamente 4 digitos.",
        validators=[
            RegexValidator(
                regex=r"^\d{4}$",
                message="Tag 2 debe tener exactamente 4 digitos.",
            )
        ],
    )
    categoria = models.ForeignKey(CategoriaEquipo, on_delete=models.PROTECT)
    marca = models.CharField(max_length=80, blank=True, null=True)
    modelo = models.CharField(max_length=80, blank=True, null=True)
    # numero de pedimiento es un campo opcional que puede ser nulo o vacío
    Numero_Pedimiento = models.CharField(max_length=15, blank=True, null=True)
    descripcion_equipo = models.CharField(max_length=255, blank=True, null=True)
    imagen = models.ImageField(upload_to=equipo_imagen_upload_to, blank=True, null=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    origen_alta = models.CharField(
        max_length=20,
        choices=OrigenAltaEquipo.choices,
        default=OrigenAltaEquipo.LEGADO,
        verbose_name="Origen de alta",
    )
    orden_compra = models.ForeignKey(
        "OrdenCompra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipos",
        verbose_name="Orden de compra",
    )
    detalle_orden = models.ForeignKey(
        "DetalleOrdenCompra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipos",
        verbose_name="Linea de orden",
    )
    estado_equipo = models.CharField(max_length=30, choices=EstadoEquipo.choices, default=EstadoEquipo.DISPONIBLE)
    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Departamento",
    )
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True)
    equipo_padre = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perifericos",
        verbose_name="Equipo padre",
        help_text="Solo perifericos: maquina a la que estan vinculados.",
    )
    fecha_alta = models.DateField(default=timezone.now)
    fecha_baja = models.DateField(blank=True, null=True)
    motivo_baja = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.codigo_inventario

    def save(self, *args, **kwargs):
        if self.numero_serie is not None and not str(self.numero_serie).strip():
            self.numero_serie = None
        elif self.numero_serie is not None:
            self.numero_serie = str(self.numero_serie).strip()
        if self.tag_1 is not None and not str(self.tag_1).strip():
            self.tag_1 = None
        elif self.tag_1 is not None:
            self.tag_1 = str(self.tag_1).strip()
        if self.tag_2 is not None and not str(self.tag_2).strip():
            self.tag_2 = None
        elif self.tag_2 is not None:
            self.tag_2 = str(self.tag_2).strip()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # Varios NULL son validos con unique; "" no lo es.
        if self.numero_serie is not None and not str(self.numero_serie).strip():
            self.numero_serie = None
        elif self.numero_serie is not None:
            self.numero_serie = str(self.numero_serie).strip()
        if self.tag_1 is not None and not str(self.tag_1).strip():
            self.tag_1 = None
        elif self.tag_1 is not None:
            self.tag_1 = str(self.tag_1).strip()
        if self.tag_2 is not None and not str(self.tag_2).strip():
            self.tag_2 = None
        elif self.tag_2 is not None:
            self.tag_2 = str(self.tag_2).strip()
        tipo = None
        if self.categoria_id:
            tipo = self.categoria.tipo
        if self.equipo_padre_id:
            if tipo != TipoCategoriaInventario.PERIFERICO:
                raise ValidationError(
                    {"equipo_padre": "Solo un periferico puede vincularse a un equipo."}
                )
            padre = self.equipo_padre
            if padre and padre.tipo_inventario != TipoCategoriaInventario.EQUIPO:
                raise ValidationError(
                    {"equipo_padre": "El equipo padre debe ser de tipo Equipo."}
                )
            if padre and padre.pk == self.pk:
                raise ValidationError(
                    {"equipo_padre": "Un registro no puede ser padre de si mismo."}
                )
        elif tipo == TipoCategoriaInventario.HERRAMIENTA and self.equipo_padre_id:
            raise ValidationError(
                {"equipo_padre": "Las herramientas no se vinculan a un equipo."}
            )

    @property
    def tipo_inventario(self):
        cat = getattr(self, "categoria", None)
        if cat is not None:
            return cat.tipo
        return TipoCategoriaInventario.EQUIPO

    @property
    def es_equipo_principal(self):
        return self.tipo_inventario == TipoCategoriaInventario.EQUIPO

    @property
    def es_periferico(self):
        return self.tipo_inventario == TipoCategoriaInventario.PERIFERICO

    @property
    def perifericos_activos(self):
        return (
            self.perifericos.select_related("categoria", "ubicacion")
            .filter(activo=True)
            .exclude(estado_equipo=EstadoEquipo.BAJA)
            .order_by("categoria__nombre_categoria", "codigo_inventario")
        )

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
        # Solo maquinas principales se asignan a personal.
        if self.tipo_inventario != TipoCategoriaInventario.EQUIPO:
            return False
        return self.estado_equipo not in {
            EstadoEquipo.BAJA,
            EstadoEquipo.EN_MANTENIMIENTO,
        }

    @property
    def puede_vincular_perifericos(self):
        """Un equipo principal puede recibir perifericos en su kit."""
        if not self.es_equipo_principal or not self.activo:
            return False
        return self.estado_equipo != EstadoEquipo.BAJA

    @property
    def puede_vincularse_a_equipo(self):
        """Un periferico libre puede vincularse a un equipo."""
        if not self.es_periferico or not self.activo:
            return False
        if self.equipo_padre_id:
            return False
        return self.estado_equipo not in {
            EstadoEquipo.BAJA,
            EstadoEquipo.EN_MANTENIMIENTO,
        }

    @property
    def puede_desvincularse(self):
        if not self.es_periferico or not self.equipo_padre_id:
            return False
        return self.estado_equipo != EstadoEquipo.BAJA

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
        if self.perifericos.exists():
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
    VINCULAR_PERIFERICO = "Vincular periferico", "Vincular periferico"
    DESVINCULAR_PERIFERICO = "Desvincular periferico", "Desvincular periferico"
    REEMPLAZAR_PERIFERICO = "Reemplazar periferico", "Reemplazar periferico"


class MovimientoEquipo(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=40, choices=TipoMovimiento.choices)
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
    MANTENIMIENTO = "MANTENIMIENTO", "MANTENIMIENTO"


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
    imagen = models.ImageField(upload_to=ticket_imagen_upload_to, blank=True, null=True)
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

        Al concluir, SeguimientoTicket.save() limpia fecha_proximo_seguimiento
        de checks abiertos previos (historial intacto, sin alertas pendientes).
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
        # Un check concluido no agenda proximo seguimiento.
        if self.ya_terminado and self.fecha_proximo_seguimiento is not None:
            self.fecha_proximo_seguimiento = None
        super().save(*args, **kwargs)

        # Al cerrar el ticket, limpia fechas pendientes de checks abiertos previos
        # (siguen como historial intermedio, sin alertas huérfanas).
        if self.ya_terminado and self.ticket_id:
            type(self).objects.filter(
                ticket_id=self.ticket_id,
                ya_terminado=False,
                fecha_proximo_seguimiento__isnull=False,
            ).exclude(pk=self.pk).update(fecha_proximo_seguimiento=None)

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


class ComentarioTicket(models.Model):
    """Hilo de conversacion en el ticket. No cambia el estado ni el SLA."""

    ticket = models.ForeignKey(
        TicketIT,
        on_delete=models.CASCADE,
        related_name="comentarios",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comentarios_ticket",
    )
    mensaje = models.TextField(blank=True)
    es_interno = models.BooleanField(
        default=False,
        help_text="True si lo publico un tecnico o administrador.",
    )
    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Comentario de ticket"
        verbose_name_plural = "Comentarios de ticket"
        ordering = ["fecha", "pk"]

    def __str__(self):
        folio = self.ticket.folio_ticket if self.ticket_id else "SPR0"
        return f"{folio} · comentario {self.pk}"

    @property
    def tiene_adjuntos(self):
        return self.adjuntos.exists()


class ComentarioTicketAdjunto(models.Model):
    comentario = models.ForeignKey(
        ComentarioTicket,
        on_delete=models.CASCADE,
        related_name="adjuntos",
    )
    archivo = models.FileField(upload_to=ticket_comentario_upload_to)
    nombre_original = models.CharField(max_length=180, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adjunto de comentario"
        verbose_name_plural = "Adjuntos de comentario"
        ordering = ["pk"]

    def __str__(self):
        return self.nombre_original or (self.archivo.name if self.archivo else "adjunto")

    @property
    def es_imagen(self):
        ext = (self.archivo.name or "").rsplit(".", 1)
        suffix = f".{ext[-1].lower()}" if len(ext) == 2 else ""
        return suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    @property
    def etiqueta(self):
        return self.nombre_original or (self.archivo.name.rsplit("/", 1)[-1] if self.archivo else "archivo")


@receiver(post_delete, sender=ComentarioTicketAdjunto)
def delete_comentario_adjunto_file(sender, instance, **kwargs):
    if instance.archivo:
        instance.archivo.delete(save=False)


class Bitacora(models.Model):
    FOLIO_PREFIX = 'BIT-'
    FOLIO_WIDTH = 6

    folio_bitacora = models.CharField(max_length=30, unique=True, blank=True)
    fecha_bitacora = models.DateTimeField(default=timezone.now)
    situacion = models.CharField(max_length=180)
    descripcion_situacion = models.TextField()

    class Meta:
        verbose_name = 'Bitacora'
        verbose_name_plural = 'Bitacora'
        ordering = ['-fecha_bitacora', '-pk']

    @classmethod
    def _next_folio_bitacora(cls):
        folios = cls.objects.filter(
            folio_bitacora__startswith=cls.FOLIO_PREFIX
        ).order_by('-folio_bitacora').values_list('folio_bitacora', flat=True)

        for folio in folios:
            suffix = folio[len(cls.FOLIO_PREFIX):]
            if suffix.isdigit():
                next_number = int(suffix) + 1
                return f'{cls.FOLIO_PREFIX}{next_number:0{cls.FOLIO_WIDTH}d}'

        return f'{cls.FOLIO_PREFIX}{1:0{cls.FOLIO_WIDTH}d}'

    @property
    def tiene_respuestas(self):
        return self.answers.exists()

    @property
    def puede_eliminar(self):
        return not self.tiene_respuestas

    def clean(self):
        if self.folio_bitacora:
            folio = self.folio_bitacora.upper()
            if not folio.startswith('BIT-'):
                raise ValidationError({'folio_bitacora': 'El folio de Bitacora debe iniciar con BIT-.'})

    def save(self, *args, **kwargs):
        if self.folio_bitacora:
            self.folio_bitacora = self.folio_bitacora.upper()
            super().save(*args, **kwargs)
            return

        for _ in range(3):
            self.folio_bitacora = self._next_folio_bitacora()
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.folio_bitacora = None

        raise IntegrityError('No se pudo generar un folio unico para Bitacora.')

    def __str__(self):
        return self.folio_bitacora or 'BIT-'


class Answer(models.Model):
    bitacora = models.ForeignKey(Bitacora, on_delete=models.CASCADE, related_name='answers')
    folio_answer = models.CharField(max_length=30, blank=True)
    fecha_answer = models.DateTimeField(default=timezone.now)
    solucion = models.CharField(max_length=180)
    descripcion_solucion = models.TextField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='answers_bitacora',
    )

    class Meta:
        verbose_name = 'Answer'
        verbose_name_plural = 'Answer'
        ordering = ['-fecha_answer', '-pk']

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
        return f'{self.folio_answer or "BIT-"} - {self.solucion}'


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
    archivo = models.FileField(upload_to=plantilla_archivo_upload_to)
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
    archivo_pdf = models.FileField(upload_to=orden_pdf_upload_to, blank=True, null=True)
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

    @property
    def lista_para_inventario(self):
        """Terminado y con al menos una linea para poder dar de alta equipos."""
        if self.estado != EstadoOrdenCompra.TERMINADO:
            return False
        return self.detalles.exists()

    @property
    def puede_recibir_equipos(self):
        """Hay cupo libre en alguna linea (cantidad - equipos ya dados de alta)."""
        if not self.lista_para_inventario:
            return False
        return any(detalle.cantidad_disponible() > 0 for detalle in self.detalles.all())

    @property
    def cantidad_lineas_esperada(self):
        from decimal import Decimal

        total = Decimal("0")
        for detalle in self.detalles.all():
            total += detalle.cantidad or Decimal("0")
        return total

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

    @property
    def cantidad_esperada(self):
        """Unidades esperadas a inventariar (parte entera de la cantidad de la linea)."""
        from decimal import Decimal, ROUND_DOWN

        cantidad = self.cantidad or Decimal("0")
        return int(cantidad.to_integral_value(rounding=ROUND_DOWN))

    def cantidad_recibida(self, exclude_equipo_id=None):
        qs = self.equipos.all()
        if exclude_equipo_id:
            qs = qs.exclude(pk=exclude_equipo_id)
        return qs.count()

    def cantidad_disponible(self, exclude_equipo_id=None):
        return max(0, self.cantidad_esperada - self.cantidad_recibida(exclude_equipo_id=exclude_equipo_id))

    def etiqueta_inventario(self, exclude_equipo_id=None):
        disponible = self.cantidad_disponible(exclude_equipo_id=exclude_equipo_id)
        esperada = self.cantidad_esperada
        recibida = self.cantidad_recibida(exclude_equipo_id=exclude_equipo_id)
        return (
            f"{self.descripcion} — disponibles: {disponible} "
            f"(alta: {recibida}/{esperada})"
        )


# ------------ CONSUMIBLES (stock por cantidad) ------------
class UnidadConsumible(models.TextChoices):
    PIEZA = "pza", "Pieza"
    CAJA = "caja", "Caja"
    ML = "ml", "Mililitro"
    LITRO = "L", "Litro"
    METRO = "m", "Metro"
    ROLLO = "rollo", "Rollo"
    OTRO = "otro", "Otro"


class TipoMovimientoStock(models.TextChoices):
    ENTRADA = "Entrada", "Entrada"
    SALIDA = "Salida", "Salida"
    AJUSTE = "Ajuste", "Ajuste"


class ProductoConsumible(models.Model):
    sku = models.CharField(max_length=40, unique=True, verbose_name="SKU / codigo")
    nombre = models.CharField(max_length=160)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    categoria = models.ForeignKey(
        CategoriaEquipo,
        on_delete=models.PROTECT,
        related_name="productos_consumibles",
        limit_choices_to={"tipo": TipoCategoriaInventario.CONSUMIBLE},
    )
    unidad = models.CharField(
        max_length=10,
        choices=UnidadConsumible.choices,
        default=UnidadConsumible.PIEZA,
    )
    stock_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_aproximado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Costo unitario approx.",
    )
    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos_consumibles",
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos_consumibles",
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre", "sku"]
        verbose_name = "Producto consumible"
        verbose_name_plural = "Productos consumibles"

    def __str__(self):
        return f"{self.sku} — {self.nombre}"

    @property
    def esta_bajo_minimo(self):
        from decimal import Decimal

        minimo = self.stock_minimo or Decimal("0")
        if minimo <= 0:
            return False
        return (self.stock_actual or Decimal("0")) <= minimo

    @property
    def semaforo(self):
        from decimal import Decimal

        stock = self.stock_actual or Decimal("0")
        minimo = self.stock_minimo or Decimal("0")
        if stock <= 0:
            return "critico"
        if minimo > 0 and stock <= minimo:
            return "bajo"
        return "ok"

    def clean(self):
        super().clean()
        if self.categoria_id and self.categoria.tipo != TipoCategoriaInventario.CONSUMIBLE:
            raise ValidationError(
                {"categoria": "La categoria debe ser de tipo Consumible."}
            )
        if self.stock_actual is not None and self.stock_actual < 0:
            raise ValidationError({"stock_actual": "El stock no puede ser negativo."})
        if self.stock_minimo is not None and self.stock_minimo < 0:
            raise ValidationError({"stock_minimo": "El minimo no puede ser negativo."})


class MovimientoStock(models.Model):
    producto = models.ForeignKey(
        ProductoConsumible,
        on_delete=models.CASCADE,
        related_name="movimientos",
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TipoMovimientoStock.choices,
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    stock_antes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_despues = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    responsable = models.ForeignKey(
        Personal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_stock",
    )
    orden_compra = models.ForeignKey(
        "OrdenCompra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_stock",
    )
    fecha_movimiento = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-fecha_movimiento", "-pk"]
        verbose_name = "Movimiento de stock"
        verbose_name_plural = "Movimientos de stock"

    def __str__(self):
        return f"{self.tipo_movimiento} {self.cantidad} · {self.producto.sku}"


# ------------ HISTORIAL GENERAL DE ACTIVIDAD ------------
class ModuloHistorial(models.TextChoices):
    TICKET = "ticket", "Tickets de soporte"
    SEGUIMIENTO = "seguimiento", "Seguimiento de tickets"
    EQUIPO = "equipo", "Equipos"
    ASIGNACION = "asignacion", "Asignaciones de equipo"
    MOVIMIENTO_EQUIPO = "movimiento_equipo", "Movimientos de equipo"
    CONSUMIBLE = "consumible", "Consumibles"
    PERSONAL = "personal", "Personal"
    MANTENIMIENTO = "mantenimiento", "Mantenimiento"
    ORDEN_COMPRA = "orden_compra", "Ordenes de compra"
    BITACORA = "bitacora", "Bitacora"
    SISTEMA = "sistema", "Sistema"
    GOBIERNO = "gobierno", "Gobierno y roles"
    SOLICITUD_EQUIPO = "solicitud_equipo", "Solicitudes de equipo"


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


# ------------ GOBIERNO: cobertura y solicitudes de equipo ------------

class CoberturaTickets(models.Model):
    """Delegacion temporal: el suplente atiende tickets del ausente."""

    ausente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coberturas_como_ausente",
        verbose_name="Tecnico ausente",
    )
    suplente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coberturas_como_suplente",
        verbose_name="Suplente",
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activa = models.BooleanField(default=True)
    motivo = models.CharField(max_length=255, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coberturas_creadas",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_inicio", "-pk"]
        verbose_name = "Cobertura de tickets"
        verbose_name_plural = "Coberturas de tickets"

    def __str__(self):
        return f"{self.suplente} cubre a {self.ausente} ({self.fecha_inicio} → {self.fecha_fin})"

    def clean(self):
        if self.ausente_id and self.suplente_id and self.ausente_id == self.suplente_id:
            raise ValidationError("El ausente y el suplente deben ser personas distintas.")
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError("La fecha fin no puede ser anterior al inicio.")

    @property
    def vigente_hoy(self):
        today = timezone.localdate()
        return bool(self.activa and self.fecha_inicio <= today <= self.fecha_fin)


class EstadoSolicitudEquipo(models.TextChoices):
    PENDIENTE = "Pendiente", "Pendiente"
    EN_REVISION = "En revision", "En revision"
    APROBADA = "Aprobada", "Aprobada"
    RECHAZADA = "Rechazada", "Rechazada"
    COMPLETADA = "Completada", "Completada"
    CANCELADA = "Cancelada", "Cancelada"


class UrgenciaSolicitudEquipo(models.TextChoices):
    BAJA = "Baja", "Baja"
    MEDIA = "Media", "Media"
    ALTA = "Alta", "Alta"


class SolicitudEquipo(models.Model):
    FOLIO_PREFIX = "SOL-"
    FOLIO_WIDTH = 6

    folio = models.CharField(max_length=30, unique=True, blank=True)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitudes_equipo",
    )
    personal = models.ForeignKey(
        Personal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_equipo",
        help_text="Perfil de personal a quien se asignaria el equipo.",
    )
    categoria = models.ForeignKey(
        CategoriaEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes",
    )
    titulo = models.CharField(max_length=160)
    justificacion = models.TextField()
    urgencia = models.CharField(
        max_length=10,
        choices=UrgenciaSolicitudEquipo.choices,
        default=UrgenciaSolicitudEquipo.MEDIA,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoSolicitudEquipo.choices,
        default=EstadoSolicitudEquipo.PENDIENTE,
        db_index=True,
    )
    notas_solicitante = models.CharField(max_length=255, blank=True)
    notas_it = models.TextField(blank=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_equipo_revisadas",
    )
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_origen",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion", "-pk"]
        verbose_name = "Solicitud de equipo"
        verbose_name_plural = "Solicitudes de equipo"

    def __str__(self):
        return f"{self.folio or 'SOL'} - {self.titulo}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.folio:
            self.folio = f"{self.FOLIO_PREFIX}{self.pk:0{self.FOLIO_WIDTH}d}"
            super().save(update_fields=["folio"])

    @property
    def puede_cancelar_solicitante(self):
        return self.estado in {
            EstadoSolicitudEquipo.PENDIENTE,
            EstadoSolicitudEquipo.EN_REVISION,
        }

    @property
    def puede_gestionar_it(self):
        return self.estado in {
            EstadoSolicitudEquipo.PENDIENTE,
            EstadoSolicitudEquipo.EN_REVISION,
            EstadoSolicitudEquipo.APROBADA,
        }

    @property
    def esta_cerrada(self):
        return self.estado in {
            EstadoSolicitudEquipo.RECHAZADA,
            EstadoSolicitudEquipo.COMPLETADA,
            EstadoSolicitudEquipo.CANCELADA,
        }


class SeguimientoSolicitudEquipo(models.Model):
    solicitud = models.ForeignKey(
        SolicitudEquipo,
        on_delete=models.CASCADE,
        related_name="seguimientos",
    )
    fecha_check = models.DateTimeField(default=timezone.now)
    avance_realizado = models.TextField(blank=True, null=True)
    pendiente = models.TextField(blank=True, null=True)
    proximo_paso = models.TextField(blank=True, null=True)
    fecha_proximo_seguimiento = models.DateField(blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seguimientos_solicitud_equipo",
    )
    solucion = models.TextField(blank=True, default="")
    observacion = models.TextField(blank=True, null=True)
    ya_terminado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha_check", "-pk"]
        verbose_name = "Revision IT"
        verbose_name_plural = "Revisiones IT"

    def __str__(self):
        folio = self.solicitud.folio if self.solicitud_id else "SOL"
        return f"{folio} · {self.fecha_check}"

    def clean(self):
        if self.ya_terminado and not (self.solucion or "").strip():
            raise ValidationError(
                {"solucion": "Indica la solucion al concluir la revision."}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if (
            self.solicitud_id
            and self.solicitud.estado == EstadoSolicitudEquipo.PENDIENTE
        ):
            self.solicitud.estado = EstadoSolicitudEquipo.EN_REVISION
            self.solicitud.save(update_fields=["estado", "fecha_actualizacion"])

