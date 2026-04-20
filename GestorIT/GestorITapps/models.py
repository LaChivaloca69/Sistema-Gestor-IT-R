from django.db import models
from django.utils import timezone

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


class Proveedor(models.Model):
    nombre_proveedor = models.CharField(max_length=150)
    contacto = models.CharField(max_length=150, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_proveedor


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
    rack = models.CharField(max_length=50, blank=True, null=True)
    anaquel = models.CharField(max_length=50, blank=True, null=True)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.edificio} / {self.zona} / {self.referencia or 'Sin referencia'}"


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
    fecha_compra = models.DateField(blank=True, null=True)
    costo_compra = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    garantia_meses = models.IntegerField(default=0)
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
    ENTRADA = "Entrada", "Entrada"
    SALIDA = "Salida", "Salida"
    TRANSFERENCIA = "Transferencia", "Transferencia"
    BAJA = "Baja", "Baja"


class MovimientoEquipo(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    cantidad = models.IntegerField(default=1)
    origen = models.CharField(max_length=150, blank=True, null=True)
    destino = models.CharField(max_length=150, blank=True, null=True)
    responsable = models.CharField(max_length=150, blank=True, null=True)
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
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    tecnico_responsable = models.CharField(max_length=150, blank=True, null=True)
    costo_mantenimiento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion_falla = models.CharField(max_length=255, blank=True, null=True)
    acciones_realizadas = models.TextField(blank=True, null=True)
    proxima_fecha_mantenimiento = models.DateField(blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class AgendaMantenimiento(models.Model):
    mantenimiento = models.ForeignKey(Mantenimiento, on_delete=models.CASCADE, related_name='recordatorios')
    fecha_recordatorio = models.DateTimeField()
    canal_recordatorio = models.CharField(max_length=50, blank=True, null=True)
    enviado = models.BooleanField(default=False)


class PrioridadTicket(models.TextChoices):
    BAJA = "Baja", "Baja"
    MEDIA = "Media", "Media"
    ALTA = "Alta", "Alta"
    CRITICA = "Crítica", "Crítica"


class EstadoTicket(models.TextChoices):
    ABIERTO = "Abierto", "Abierto"
    EN_PROCESO = "En Proceso", "En Proceso"
    RESUELTO = "Resuelto", "Resuelto"
    CERRADO = "Cerrado", "Cerrado"


class TicketIT(models.Model):
    folio_ticket = models.CharField(max_length=30, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    personal_solicitante = models.ForeignKey(Personal, on_delete=models.PROTECT)
    equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=PrioridadTicket.choices, default=PrioridadTicket.MEDIA)
    estado_ticket = models.CharField(max_length=20, choices=EstadoTicket.choices, default=EstadoTicket.ABIERTO)
    tecnico_asignado = models.CharField(max_length=150, blank=True, null=True)
    fecha_cierre = models.DateTimeField(blank=True, null=True)
    solucion = models.TextField(blank=True, null=True)


class SeguimientoTicket(models.Model):
    ticket = models.ForeignKey(TicketIT, on_delete=models.CASCADE, related_name='seguimientos')
    fecha_evento = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField()
    usuario_evento = models.CharField(max_length=150)
    cambio_estado = models.CharField(max_length=100, blank=True, null=True)


class Presupuesto(models.Model):
    folio_presupuesto = models.CharField(max_length=30, unique=True)
    fecha_presupuesto = models.DateField()
    cliente_o_area = models.CharField(max_length=150)
    elaborado_por = models.CharField(max_length=150)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_presupuesto = models.CharField(max_length=30, default='Borrador')
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
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    solicitado_por = models.CharField(max_length=150, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_compra = models.CharField(max_length=30, default='Solicitada')
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class DetalleCompraMaterial(models.Model):
    compra = models.ForeignKey(CompraMaterial, on_delete=models.CASCADE, related_name='detalles')
    concepto = models.CharField(max_length=150)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    importe = models.DecimalField(max_digits=12, decimal_places=2, default=0)