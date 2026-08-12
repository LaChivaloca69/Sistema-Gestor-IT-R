"""Forms de movimientos de equipo."""
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


class MovimientoEquipoForm(forms.ModelForm):
    ubicacion_origen = forms.ModelChoiceField(
        queryset=Ubicacion.objects.none(),
        required=False,
        label="Ubicacion origen",
    )
    ubicacion_destino = forms.ModelChoiceField(
        queryset=Ubicacion.objects.none(),
        required=False,
        label="Ubicacion destino",
    )

    class Meta:
        model = MovimientoEquipo
        fields = [
            "equipo",
            "tipo_movimiento",
            "ubicacion_origen",
            "ubicacion_destino",
            "responsable",
            "observaciones",
        ]
        labels = {
            "equipo": "Equipo",
            "tipo_movimiento": "Tipo de movimiento",
            "ubicacion_origen": "Ubicacion origen",
            "ubicacion_destino": "Ubicacion destino",
            "responsable": "Responsable",
            "observaciones": "Observaciones",
        }
        help_texts = {
            "responsable": "Responsable actual del equipo.",
            "observaciones": "Opcional. Puedes agregar comentarios sobre el movimiento.",
            "tipo_movimiento": (
                "Preferible usar las acciones del detalle del equipo "
                "(asignar, devolver, ubicacion, baja). Este registro es solo auditoria."
            ),
        }
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ubicacion_origen"].label = "Ubicacion actual"
        self.fields["ubicacion_destino"].label = "Nueva ubicacion"
        self.fields["ubicacion_origen"].disabled = True
        self.fields["responsable"].disabled = True
        self.fields["responsable"].help_text = "Se toma de la asignacion activa del equipo."

        ubicaciones = Ubicacion.objects.select_related("edificio", "zona").order_by(
            "edificio__nombre_edificio",
            "zona__nombre_zona",
            "referencia",
        )
        self.fields["ubicacion_origen"].queryset = ubicaciones
        self.fields["ubicacion_destino"].queryset = ubicaciones

        equipo = None
        if self.instance and self.instance.pk and self.instance.equipo_id:
            equipo = self.instance.equipo
        elif self.data.get("equipo"):
            try:
                equipo = Equipo.objects.select_related("ubicacion").get(
                    pk=self.data.get("equipo")
                )
            except (Equipo.DoesNotExist, ValueError, TypeError):
                equipo = None

        if equipo and equipo.ubicacion_id:
            self.fields["ubicacion_origen"].initial = equipo.ubicacion_id

        from ..views.helpers import _get_equipo_asignacion_activa

        asignacion = _get_equipo_asignacion_activa(equipo)
        if asignacion and asignacion.personal_id:
            self.fields["responsable"].initial = asignacion.personal_id

    def save(self, commit=True):
        from ..views.helpers import _get_equipo_asignacion_activa

        instance = super().save(commit=False)
        equipo = self.cleaned_data.get("equipo")
        origen = self.cleaned_data.get("ubicacion_origen")
        destino = self.cleaned_data.get("ubicacion_destino")

        asignacion = _get_equipo_asignacion_activa(equipo)
        if asignacion and asignacion.personal_id:
            instance.responsable = asignacion.personal
        else:
            instance.responsable = self.cleaned_data.get("responsable")

        if not origen and equipo and equipo.ubicacion_id:
            origen = equipo.ubicacion
        instance.origen = str(origen) if origen else None
        instance.destino = str(destino) if destino else None

        if commit:
            instance.save()
            self.save_m2m()
            if equipo and destino and equipo.ubicacion_id != destino.pk:
                equipo.ubicacion = destino
                equipo.save(update_fields=["ubicacion"])
        return instance

