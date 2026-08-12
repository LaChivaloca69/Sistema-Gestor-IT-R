"""Forms de inventario de equipos."""
from datetime import datetime
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .. import document_engine
from ..cobertura import operativo_user_choices
from ..models import (
    AccionHistorial,
    AgendaMantenimiento,
    Answer,
    Area,
    AsignacionEquipo,
    Bitacora,
    CategoriaEquipo,
    CoberturaTickets,
    DetalleOrdenCompra,
    Edificio,
    Equipo,
    EstadoAsignacion,
    EstadoEquipo,
    EstadoMantenimiento,
    EstadoOrdenCompra,
    EstadoSolicitudEquipo,
    EstadoSupport,
    IvaOpcion,
    Mantenimiento,
    MovimientoEquipo,
    OrdenCompra,
    OrigenAltaEquipo,
    Personal,
    PlantillaDocumento,
    Proveedor,
    Puesto,
    SeguimientoTicket,
    SolicitudEquipo,
    TicketIT,
    TipoPlantillaDocumento,
    TipoProveedor,
    Ubicacion,
    UrgenciaSolicitudEquipo,
    ZonaEdificio,
)
from ..roles import (
    ROLE_ADMIN,
    ROLE_CHOICES,
    ROLE_TECNICO,
    ROLE_USUARIO,
    get_user_role,
    is_admin_user,
    is_operativo,
    operativo_users_queryset,
    set_user_role,
)



class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = [
            "codigo_inventario",
            "numero_serie",
            "categoria",
            "marca",
            "modelo",
            "Numero_Pedimiento",
            "descripcion_equipo",
            "imagen",
            "proveedor",
            "origen_alta",
            "orden_compra",
            "detalle_orden",
            "estado_equipo",
            "ubicacion",
            "fecha_alta",
            "activo",
        ]
        labels = {
            "codigo_inventario": "Código de inventario (ID)",
            "numero_serie": "Número de serie",
            "marca": "Marca",
            "modelo": "Modelo",
            "categoria": "Categoría",
            "proveedor": "Proveedor",
            "Numero_Pedimiento": "Número de pedimiento",
            "descripcion_equipo": "Descripción del equipo",
            "origen_alta": "Origen de alta",
            "orden_compra": "Orden de compra",
            "detalle_orden": "Producto de la orden",
            "estado_equipo": "Estado del equipo",
            "ubicacion": "Ubicación",
            "fecha_alta": "Fecha de alta",
            "activo": "Activo",
            "imagen": "Imagen",
        }
        help_texts = {
            "codigo_inventario": "Código único de inventario del equipo.",
            "numero_serie": "Número de serie del equipo.",
            "origen_alta": (
                "Compra: con OC. Legado: equipos viejos sin documento. "
                "Otros: donacion, transferencia, etc."
            ),
            "orden_compra": "Opcional. Solo OC en estado Terminado con cupo disponible.",
            "detalle_orden": (
                "Obligatorio si es Compra. Cada alta descuenta 1 de la cantidad de la linea."
            ),
            "proveedor": "Proveedor del equipo.",
            "Numero_Pedimiento": "Número de pedimiento del equipo(si aplica).",
            "descripcion_equipo": "Descripción detallada del equipo.",
            "estado_equipo": (
                "Disponible/Asignado se sincronizan con la asignacion activa. "
                "Usa En Mantenimiento/Baja con cuidado."
            ),
            "ubicacion": "Ubicación física del equipo.",
            "fecha_alta": "Fecha en que se dio de alta el equipo.",
        }
        widgets = {
            "descripcion_equipo": forms.Textarea(attrs={"rows": 4}),
            "fecha_alta": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exclude_id = self.instance.pk if self.instance and self.instance.pk else None

        ordenes_qs = (
            OrdenCompra.objects.filter(estado=EstadoOrdenCompra.TERMINADO)
            .prefetch_related("detalles", "detalles__equipos")
            .order_by("-creado_en")
        )
        ordenes_con_cupo = [
            orden.pk for orden in ordenes_qs if orden.puede_recibir_equipos
        ]
        if self.instance and self.instance.orden_compra_id:
            ordenes_con_cupo.append(self.instance.orden_compra_id)
        self.fields["orden_compra"].queryset = OrdenCompra.objects.filter(
            pk__in=set(ordenes_con_cupo) or [-1]
        ).order_by("-creado_en")
        self.fields["orden_compra"].required = False
        self.fields["detalle_orden"].required = False
        self.fields["detalle_orden"].label = "Producto de la orden"
        self.fields["detalle_orden"].empty_label = "---------"

        orden = None
        if self.is_bound:
            orden_id = self.data.get("orden_compra")
            if orden_id:
                orden = OrdenCompra.objects.filter(pk=orden_id).first()
        elif self.initial.get("orden_compra"):
            orden = self.initial.get("orden_compra")
            if getattr(orden, "pk", None) is None and str(orden).isdigit():
                orden = OrdenCompra.objects.filter(pk=orden).first()
        elif self.instance and self.instance.orden_compra_id:
            orden = self.instance.orden_compra

        if orden is not None and getattr(orden, "pk", None):
            lineas = list(
                DetalleOrdenCompra.objects.filter(orden=orden)
                .prefetch_related("equipos")
                .order_by("pk")
            )
            lineas_visibles = [
                linea
                for linea in lineas
                if linea.cantidad_disponible(exclude_equipo_id=exclude_id) > 0
                or (
                    self.instance
                    and self.instance.detalle_orden_id
                    and linea.pk == self.instance.detalle_orden_id
                )
            ]
            self.fields["detalle_orden"].queryset = DetalleOrdenCompra.objects.filter(
                pk__in=[linea.pk for linea in lineas_visibles] or [-1]
            ).order_by("pk")
            self.fields["detalle_orden"].label_from_instance = (
                lambda obj, _exclude=exclude_id: obj.etiqueta_inventario(
                    exclude_equipo_id=_exclude
                )
            )
        else:
            self.fields["detalle_orden"].queryset = DetalleOrdenCompra.objects.none()

    def clean(self):
        cleaned = super().clean()
        origen = cleaned.get("origen_alta")
        orden = cleaned.get("orden_compra")
        detalle = cleaned.get("detalle_orden")
        exclude_id = self.instance.pk if self.instance and self.instance.pk else None

        # Sin origen Compra no aplican datos de OC.
        if origen != OrigenAltaEquipo.COMPRA:
            cleaned["orden_compra"] = None
            cleaned["detalle_orden"] = None
            return cleaned

        if not orden:
            self.add_error(
                "orden_compra",
                "Si el origen es Compra, selecciona una orden de compra terminada.",
            )
        if orden and not detalle:
            self.add_error(
                "detalle_orden",
                "Selecciona el producto de la orden. Cada alta descuenta 1 unidad de esa linea.",
            )
        if orden and not orden.lista_para_inventario:
            self.add_error(
                "orden_compra",
                "La orden debe estar en Terminado y tener lineas capturadas.",
            )
        if detalle and orden and detalle.orden_id != orden.pk:
            self.add_error("detalle_orden", "La linea no pertenece a la orden seleccionada.")
        if detalle and not orden:
            cleaned["orden_compra"] = detalle.orden
            orden = detalle.orden
        if detalle is not None:
            disponible = detalle.cantidad_disponible(exclude_equipo_id=exclude_id)
            if disponible <= 0:
                self.add_error(
                    "detalle_orden",
                    (
                        f"Ya no hay cupo en esta linea "
                        f"({detalle.descripcion}: {detalle.cantidad_recibida(exclude_equipo_id=exclude_id)}"
                        f"/{detalle.cantidad_esperada})."
                    ),
                )
        if orden and not orden.puede_recibir_equipos:
            if not (
                self.instance
                and self.instance.pk
                and self.instance.orden_compra_id == orden.pk
            ):
                self.add_error(
                    "orden_compra",
                    "Esta orden ya no tiene productos disponibles para dar de alta.",
                )
        return cleaned

    def clean_imagen(self):
        from ..media_security import validate_image_upload

        return validate_image_upload(self.cleaned_data.get("imagen"))



class EquipoBajaForm(forms.Form):
    fecha_baja = forms.DateField(
        label="Fecha de baja",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    motivo_baja = forms.CharField(
        label="Motivo de baja",
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=255,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["fecha_baja"].initial = timezone.localdate()



class EquipoUbicacionForm(forms.Form):
    ubicacion = forms.ModelChoiceField(
        queryset=Ubicacion.objects.none(),
        required=False,
        label="Nueva ubicacion",
        empty_label="Sin ubicacion",
    )
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        max_length=255,
        widget=forms.TextInput(),
    )

    def __init__(self, *args, **kwargs):
        equipo = kwargs.pop("equipo", None)
        super().__init__(*args, **kwargs)
        self.fields["ubicacion"].queryset = Ubicacion.objects.select_related(
            "edificio", "zona"
        ).order_by(
            "edificio__nombre_edificio",
            "zona__nombre_zona",
            "referencia",
        )
        if equipo and not self.is_bound:
            self.fields["ubicacion"].initial = equipo.ubicacion_id



class EquipoAsignarForm(forms.Form):
    personal = forms.ModelChoiceField(
        queryset=Personal.objects.none(),
        label="Personal",
    )
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        max_length=255,
        widget=forms.TextInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["personal"].queryset = Personal.objects.order_by(
            "numero_empleado",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
        )

