"""Registro de usuario."""
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
from .common import _get_user_personal  # noqa: F401



class UserRegisterForm(UserCreationForm):
    numero_empleado = forms.CharField(max_length=30, label="Numero de empleado")
    nombre = forms.CharField(max_length=100, label="Nombre")
    apellido_paterno = forms.CharField(max_length=100, label="Apellido paterno")
    apellido_materno = forms.CharField(max_length=100, label="Apellido materno", required=False)

    class Meta:
        model = User
        fields = ["username", "password1", "password2"]

    def clean_numero_empleado(self):
        numero_empleado = self.cleaned_data.get("numero_empleado", "").strip()
        if Personal.objects.filter(numero_empleado__iexact=numero_empleado).exists():
            raise forms.ValidationError("El numero de empleado ya esta registrado.")
        return numero_empleado

    def save(self, commit=True):
        from ..roles import ROLE_USUARIO, set_user_role

        if not commit:
            return super().save(commit=False)

        with transaction.atomic():
            user = super().save(commit=True)
            set_user_role(user, ROLE_USUARIO)
            Personal.objects.create(
                user=user,
                numero_empleado=self.cleaned_data["numero_empleado"],
                nombre=self.cleaned_data["nombre"],
                apellido_paterno=self.cleaned_data["apellido_paterno"],
                apellido_materno=self.cleaned_data.get("apellido_materno") or None,
                admin_requested=False,
            )
        return user

