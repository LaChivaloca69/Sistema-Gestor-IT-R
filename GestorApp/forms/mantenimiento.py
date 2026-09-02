"""Forms de mantenimiento y agenda."""
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


class MantenimientoForm(forms.ModelForm):
    tecnico_responsable = forms.ChoiceField(
        required=False,
        choices=(),
        label="Tecnico responsable",
    )
    proveedor_responsable = forms.ModelChoiceField(
        queryset=Proveedor.objects.none(),
        required=False,
        label="Proveedor",
    )

    class Meta:
        model = Mantenimiento
        fields = [
            "equipo",
            "tipo_mantenimiento",
            "fecha_programada",
            "tecnico_responsable",
            "costo_mantenimiento",
            "descripcion_falla",
        ]
        labels = {
            "equipo": "Equipo",
            "tipo_mantenimiento": "Tipo de mantenimiento",
            "fecha_programada": "Fecha programada",
            "tecnico_responsable": "Técnico responsable",
            "proveedor_responsable": "Proveedor responsable",
            "costo_mantenimiento": "Costo del mantenimiento",
            "descripcion_falla": "Descripción de la falla o razón",
        }
        help_texts = {
            "descripcion_falla": "Describe la falla o razón del mantenimiento.",
            "costo_mantenimiento": "Costo estimado o real del mantenimiento.",
        }
        widgets = {
            "fecha_programada": forms.DateInput(attrs={"type": "date"}),
            "descripcion_falla": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "equipo" in self.fields:
            self.fields["equipo"].label_from_instance = (
                lambda obj: f"{obj.codigo_inventario} - {obj.categoria}"
            )

        User = get_user_model()
        user_qs = operativo_users_queryset(User)

        choices = [("", "---------"), ("Proveedores", "Proveedores")]
        for user in user_qs:
            label = user.get_full_name().strip()
            if not label:
                try:
                    personal = user.personal_profile
                except Personal.DoesNotExist:
                    personal = None
                if personal:
                    label_parts = [
                        personal.nombre,
                        personal.apellido_paterno,
                        personal.apellido_materno,
                    ]
                    label = " ".join(part for part in label_parts if part)
            if not label:
                label = (
                    getattr(user, User.USERNAME_FIELD, "")
                    or getattr(user, "email", "")
                    or f"Usuario {user.pk}"
                )
            value = getattr(user, User.USERNAME_FIELD, "") or str(user.pk)
            choices.append((value, label))
        current_value = (self.instance.tecnico_responsable or "").strip()
        if current_value and current_value not in {value for value, _ in choices}:
            choices.append((current_value, current_value))
        self.fields["tecnico_responsable"].choices = choices

        proveedores = Proveedor.objects.filter(activo=True).order_by("nombre_proveedor")
        self.fields["proveedor_responsable"].queryset = proveedores
        if current_value.lower().startswith("proveedor:"):
            self.fields["tecnico_responsable"].initial = "Proveedores"
            nombre = current_value.split(":", 1)[1].strip()
            if nombre:
                proveedor = proveedores.filter(nombre_proveedor__iexact=nombre).first()
                if proveedor:
                    self.fields["proveedor_responsable"].initial = proveedor.pk

        self.order_fields([
            "equipo",
            "tipo_mantenimiento",
            "fecha_programada",
            "tecnico_responsable",
            "proveedor_responsable",
            "costo_mantenimiento",
            "descripcion_falla",
        ])

    def clean(self):
        cleaned = super().clean()
        tecnico = (cleaned.get("tecnico_responsable") or "").strip()
        proveedor = cleaned.get("proveedor_responsable")
        if tecnico == "Proveedores":
            if not proveedor:
                self.add_error("proveedor_responsable", "Selecciona un proveedor.")
            else:
                cleaned["tecnico_responsable"] = (
                    f"Proveedor: {proveedor.nombre_proveedor}"
                )
        elif proveedor:
            cleaned["proveedor_responsable"] = None
        return cleaned



# ============ AgendaMantenimiento views ==============
class AgendaMantenimientoForm(forms.ModelForm):
    fecha_inicio = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
        label="Fecha inicio",
    )
    fecha_fin = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
        label="Fecha fin",
    )
    crear_proximo_ciclo = forms.BooleanField(
        required=False,
        initial=True,
        label="Crear proximo mantenimiento automaticamente",
        help_text=(
            "Si indicas proxima fecha, programa un mantenimiento Preventivo "
            "en esa fecha (salvo que el equipo ya tenga uno abierto)."
        ),
    )

    class Meta:
        model = AgendaMantenimiento
        fields = [
            "mantenimiento",
            "fecha_inicio",
            "fecha_fin",
            "acciones_realizadas",
            "observaciones",
            "proxima_fecha_mantenimiento",
        ]
        labels = {
            "mantenimiento": "Mantenimiento",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de fin",
            "acciones_realizadas": "Acciones realizadas",
            "observaciones": "Observaciones",
            "proxima_fecha_mantenimiento": "Próxima fecha de mantenimiento",
        }
        help_texts = {
            "mantenimiento": "Seleccione el mantenimiento a cerrar.",
            "acciones_realizadas": "Describa las acciones realizadas durante el mantenimiento.",
            "observaciones": "Opcional. Puede agregar observaciones adicionales.",
            "proxima_fecha_mantenimiento": "Opcional. Genera aviso de proximo ciclo en el panel (sin email).",
        }
        widgets = {
            "fecha_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "fecha_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
            "proxima_fecha_mantenimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        fixed_mantenimiento = kwargs.pop("mantenimiento", None)
        super().__init__(*args, **kwargs)
        self.fields["acciones_realizadas"].required = True
        self.fields["fecha_fin"].required = True
        qs = Mantenimiento.objects.select_related("equipo").filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            cierre__isnull=True,
        ).order_by("fecha_programada")
        if self.instance and self.instance.pk:
            qs = Mantenimiento.objects.filter(pk=self.instance.mantenimiento_id) | qs
            self.fields["mantenimiento"].disabled = True
            self.fields["crear_proximo_ciclo"].initial = False
        elif fixed_mantenimiento is not None:
            qs = Mantenimiento.objects.filter(pk=fixed_mantenimiento.pk)
            self.fields["mantenimiento"].initial = fixed_mantenimiento
            self.fields["mantenimiento"].disabled = True
        self.fields["mantenimiento"].queryset = qs.distinct()
        self.fixed_mantenimiento = fixed_mantenimiento

    def clean(self):
        cleaned = super().clean()
        if getattr(self, "fixed_mantenimiento", None) is not None:
            cleaned["mantenimiento"] = self.fixed_mantenimiento
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if getattr(self, "fixed_mantenimiento", None) is not None:
            instance.mantenimiento = self.fixed_mantenimiento
        if commit:
            instance.save()
            self.save_m2m()
            mantenimiento = instance.mantenimiento
            mantenimiento.marcar_completado()
        return instance

