"""Forms de ubicaciones físicas y categorías."""
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



class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        edificio_id = None
        if self.data.get("edificio"):
            edificio_id = self.data.get("edificio")
        elif self.instance and self.instance.pk:
            edificio_id = self.instance.edificio_id

        if edificio_id:
            self.fields["zona"].queryset = ZonaEdificio.objects.filter(
                edificio_id=edificio_id,
                activo=True,
            ).order_by("nombre_zona")
        else:
            self.fields["zona"].queryset = ZonaEdificio.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        edificio = cleaned_data.get("edificio")
        zona = cleaned_data.get("zona")
        if edificio and zona and zona.edificio_id != edificio.id:
            self.add_error("zona", "La zona debe pertenecer al edificio seleccionado.")
        return cleaned_data


class EdificioForm(forms.ModelForm):
    class Meta:
        model = Edificio
        fields = "__all__"
        labels = {
            "nombre_edificio": "Nombre del edificio",
            "descripcion": "Descripción",
        }
        help_texts = {
            "descripcion": "Breve descripción del edificio.",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }


# ============  ZonaEdificio views ==============
class ZonaEdificioForm(forms.ModelForm):
    class Meta:
        model = ZonaEdificio
        fields = "__all__"
        labels = {
            "nombre_zona": "Nombre de la zona",
            "descripcion": "Descripción",
        }
        help_texts = {
            "descripcion": "Breve descripción de la zona.",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }


# ============  CategoriaEquipo views ==============
# Formulario de categoria de equipo
class CategoriaEquipoForm(forms.ModelForm):
    class Meta:
        model = CategoriaEquipo
        fields = ["nombre_categoria", "descripcion_categoria", "tipo", "activo"]
        labels = {
            "nombre_categoria": "Nombre de la categoría",
            "descripcion_categoria": "Descripción",
            "tipo": "Tipo de inventario",
            "activo": "Activo",
        }
        help_texts = {
            "descripcion_categoria": "Breve descripción de la categoría.",
            "tipo": (
                "Equipo = maquina principal. Periferico = mouse, monitor, RAM, etc. "
                "Herramienta = taller IT. Consumible = stock por cantidad (modulo posterior)."
            ),
        }
        widgets = {
            "descripcion_categoria": forms.Textarea(attrs={"rows": 3}),
        }

