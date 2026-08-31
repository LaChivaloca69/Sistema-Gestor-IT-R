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
    TipoCategoriaInventario,
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
            "descripcion_equipo": "Descripción",
            "origen_alta": "Origen de alta",
            "orden_compra": "Orden de compra",
            "detalle_orden": "Producto de la orden",
            "estado_equipo": "Estado",
            "ubicacion": "Espacio fisico",
            "fecha_alta": "Fecha de alta",
            "activo": "Activo",
            "imagen": "Imagen",
        }
        help_texts = {
            "codigo_inventario": "Código único de inventario.",
            "numero_serie": "Número de serie (si aplica).",
            "origen_alta": (
                "Compra: con OC. Legado: equipos viejos sin documento. "
                "Otros: donacion, transferencia, etc."
            ),
            "orden_compra": "Opcional. Solo OC en estado Terminado con cupo disponible.",
            "detalle_orden": (
                "Obligatorio si es Compra. Cada alta descuenta 1 de la cantidad de la linea."
            ),
            "proveedor": "Proveedor.",
            "Numero_Pedimiento": "Número de pedimiento (si aplica).",
            "descripcion_equipo": "Descripción detallada.",
            "estado_equipo": (
                "Disponible/Asignado se sincronizan con la asignacion activa. "
                "Usa En Mantenimiento/Baja con cuidado."
            ),
            "ubicacion": "Almacen o lugar fisico del equipo.",
            "fecha_alta": "Fecha en que se dio de alta.",
        }
        widgets = {
            "descripcion_equipo": forms.Textarea(attrs={"rows": 4}),
            "fecha_alta": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, tipo=None, **kwargs):
        self.tipo_inventario = tipo
        super().__init__(*args, **kwargs)
        exclude_id = self.instance.pk if self.instance and self.instance.pk else None

        if self.tipo_inventario is None and self.instance and self.instance.pk:
            self.tipo_inventario = self.instance.tipo_inventario
        if self.tipo_inventario is None:
            self.tipo_inventario = TipoCategoriaInventario.EQUIPO

        categorias = CategoriaEquipo.objects.filter(
            activo=True,
            tipo=self.tipo_inventario,
        ).order_by("nombre_categoria")
        if self.instance and self.instance.categoria_id:
            categorias = (
                CategoriaEquipo.objects.filter(pk=self.instance.categoria_id) | categorias
            ).distinct().order_by("nombre_categoria")
        self.fields["categoria"].queryset = categorias
        self.fields["categoria"].help_text = (
            f"Solo categorias de tipo {self.tipo_inventario}."
        )

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

        if "ubicacion" in self.fields:
            self.fields["ubicacion"].empty_label = "Sin espacio fisico"
            self.fields["ubicacion"].queryset = Ubicacion.objects.filter(
                activo=True
            ).select_related("edificio", "zona").order_by(
                "edificio__nombre_edificio",
                "zona__nombre_zona",
                "referencia",
            )

    def clean(self):
        cleaned = super().clean()
        origen = cleaned.get("origen_alta")
        orden = cleaned.get("orden_compra")
        detalle = cleaned.get("detalle_orden")
        categoria = cleaned.get("categoria")
        exclude_id = self.instance.pk if self.instance and self.instance.pk else None

        if categoria and self.tipo_inventario and categoria.tipo != self.tipo_inventario:
            self.add_error(
                "categoria",
                f"La categoria debe ser de tipo {self.tipo_inventario}.",
            )

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
        label="Espacio fisico",
        empty_label="Sin espacio fisico",
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


def _queryset_perifericos_libres(exclude_pk=None):
    qs = (
        Equipo.objects.select_related("categoria", "ubicacion")
        .filter(
            activo=True,
            categoria__tipo=TipoCategoriaInventario.PERIFERICO,
            equipo_padre__isnull=True,
        )
        .exclude(
            estado_equipo__in=[EstadoEquipo.BAJA, EstadoEquipo.EN_MANTENIMIENTO],
        )
        .order_by("categoria__nombre_categoria", "codigo_inventario")
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def _queryset_equipos_padre():
    return (
        Equipo.objects.select_related("categoria", "ubicacion")
        .filter(
            activo=True,
            categoria__tipo=TipoCategoriaInventario.EQUIPO,
        )
        .exclude(estado_equipo=EstadoEquipo.BAJA)
        .order_by("codigo_inventario")
    )


class EquipoVincularPerifericoForm(forms.Form):
    """Desde un equipo: elegir periferico libre para el kit."""

    periferico = forms.ModelChoiceField(
        queryset=Equipo.objects.none(),
        label="Periferico",
        help_text="Solo perifericos libres (sin equipo padre).",
    )
    observaciones = forms.CharField(
        required=False,
        label="Motivo / notas",
        max_length=255,
        widget=forms.TextInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["periferico"].queryset = _queryset_perifericos_libres()
        self.fields["periferico"].label_from_instance = (
            lambda obj: (
                f"{obj.codigo_inventario} · {obj.categoria} · "
                f"{obj.marca or '-'} {obj.modelo or ''} · {obj.estado_equipo}"
            ).strip()
        )


class PerifericoVincularEquipoForm(forms.Form):
    """Desde un periferico: elegir equipo padre."""

    equipo_padre = forms.ModelChoiceField(
        queryset=Equipo.objects.none(),
        label="Equipo",
        help_text="Maquina principal a la que se vincula este periferico.",
    )
    observaciones = forms.CharField(
        required=False,
        label="Motivo / notas",
        max_length=255,
        widget=forms.TextInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipo_padre"].queryset = _queryset_equipos_padre()
        self.fields["equipo_padre"].label_from_instance = (
            lambda obj: (
                f"{obj.codigo_inventario} · {obj.categoria} · "
                f"{obj.marca or '-'} {obj.modelo or ''} · {obj.estado_equipo}"
            ).strip()
        )


class PerifericoReemplazarForm(forms.Form):
    """Reemplazar un periferico del kit por otro libre."""

    periferico_nuevo = forms.ModelChoiceField(
        queryset=Equipo.objects.none(),
        label="Periferico de reemplazo",
        help_text="Debe estar libre (sin equipo padre).",
    )
    motivo = forms.CharField(
        required=False,
        label="Motivo del cambio",
        max_length=255,
        widget=forms.TextInput(
            attrs={"placeholder": "Ej. falla, upgrade, dano..."}
        ),
    )

    def __init__(self, *args, **kwargs):
        periferico_actual = kwargs.pop("periferico_actual", None)
        super().__init__(*args, **kwargs)
        exclude = periferico_actual.pk if periferico_actual else None
        self.fields["periferico_nuevo"].queryset = _queryset_perifericos_libres(
            exclude_pk=exclude
        )
        self.fields["periferico_nuevo"].label_from_instance = (
            lambda obj: (
                f"{obj.codigo_inventario} · {obj.categoria} · "
                f"{obj.marca or '-'} {obj.modelo or ''} · {obj.estado_equipo}"
            ).strip()
        )


class PerifericoDesvincularForm(forms.Form):
    observaciones = forms.CharField(
        required=False,
        label="Motivo",
        max_length=255,
        widget=forms.TextInput(),
    )

