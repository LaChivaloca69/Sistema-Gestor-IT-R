"""Forms de asignaciones."""
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


def _queryset_equipos_asignables(include_equipo=None):
    qs = (
        Equipo.objects.select_related("categoria")
        .filter(
            activo=True,
            categoria__tipo=TipoCategoriaInventario.EQUIPO,
        )
        .exclude(
            estado_equipo__in=[EstadoEquipo.BAJA, EstadoEquipo.EN_MANTENIMIENTO],
        )
        .order_by("codigo_inventario")
    )
    if include_equipo and getattr(include_equipo, "pk", None):
        qs = (Equipo.objects.filter(pk=include_equipo.pk) | qs).distinct().order_by(
            "codigo_inventario"
        )
    return qs


# ============  AsignacionEquipo views ==============
# Formulario de asignacion de equipo
class AsignacionEquipoForm(forms.ModelForm):
    class Meta:
        model = AsignacionEquipo
        fields = "__all__"
        labels = {
            "equipo": "Equipo",
            "personal": "Personal",
            "fecha_asignacion": "Fecha de asignación",
            "fecha_devolucion": "Fecha de devolución",
            "estado_asignacion": "Estado de asignación",
            "observaciones": "Observaciones",
        }
        help_texts = {
            "equipo": "Solo maquinas principales (laptops, PCs, impresoras…). Los perifericos van en el kit del equipo.",
            "observaciones": "Observaciones o notas a tomar encuenta.",
            "estado_asignacion": (
                "Activa pone el equipo en Asignado. Devuelta/Extraviada lo libera "
                "(si no hay otra activa)."
            ),
        }
        widgets = {
            "fecha_asignacion": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "fecha_devolucion": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fecha_devolucion = self.fields.get("fecha_devolucion")
        if fecha_devolucion:
            fecha_devolucion.widget = forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            )
            fecha_devolucion.input_formats = ["%Y-%m-%dT%H:%M"]
        equipo_field = self.fields.get("equipo")
        if equipo_field:
            include = self.instance.equipo if self.instance and self.instance.pk else None
            equipo_field.queryset = _queryset_equipos_asignables(include_equipo=include)
            equipo_field.label_from_instance = (
                lambda obj: (
                    f"{obj.codigo_inventario} · {obj.categoria} · "
                    f"{obj.marca or '-'} {obj.modelo or ''} · {obj.estado_equipo}"
                ).strip()
            )

    def clean(self):
        cleaned = super().clean()
        equipo = cleaned.get("equipo")
        estado = cleaned.get("estado_asignacion") or EstadoAsignacion.ACTIVA
        if equipo and estado == EstadoAsignacion.ACTIVA:
            if getattr(equipo, "tipo_inventario", None) != TipoCategoriaInventario.EQUIPO:
                raise ValidationError(
                    "Solo se pueden asignar equipos (maquinas principales). "
                    "Vincula perifericos al kit del equipo."
                )
            if not equipo.puede_asignarse:
                raise ValidationError(
                    "Este equipo no esta disponible para asignar "
                    "(Baja, En Mantenimiento o inactivo)."
                )
            if equipo.estado_equipo == EstadoEquipo.BAJA:
                raise ValidationError("No se puede asignar un equipo en Baja.")
            if equipo.estado_equipo == EstadoEquipo.EN_MANTENIMIENTO:
                raise ValidationError(
                    "No se puede asignar un equipo En Mantenimiento. "
                    "Cierra o cancela el mantenimiento primero."
                )
            if not equipo.activo:
                raise ValidationError("No se puede asignar un equipo inactivo.")
        if estado in {EstadoAsignacion.DEVUELTA, EstadoAsignacion.EXTRAVIADA}:
            if not cleaned.get("fecha_devolucion"):
                cleaned["fecha_devolucion"] = timezone.now()
        return cleaned

