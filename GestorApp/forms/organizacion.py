"""Forms de organización: áreas, puestos, personal, proveedores."""
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


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = "__all__"
        labels = {
            "nombre_area": "Nombre del área",
            "descripcion_area": "Descripción del área",
        }
        help_texts = {
            "nombre_area": "Nombre con el que se identifica el área.",
            "descripcion_area": "Descripcion o cualquier detalle importante.",
        }
        widgets = {
            "descripcion_area": forms.Textarea(attrs={"rows": 4}),
        }



# ============  Puesto views ==============
# Formulario de puesto
class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = "__all__"
        labels = {
            "nombre_puesto": "Nombre del puesto",
            "descripcion_puesto": "Descripción del puesto",
        }
        help_texts = {
            "nombre_puesto": "Nombre con el que se identifica el puesto.",
            "descripcion_puesto": "Descripcion o cualquier detalle importante.",
        }
        widgets = {
            "descripcion_puesto": forms.Textarea(attrs={"rows": 4}),
        }



# ============  Personal views ==============
class PersonalForm(forms.ModelForm):
    account_action = forms.ChoiceField(
        choices=(
            ("none", "Sin usuario"),
            ("assign", "Asignar usuario existente"),
            ("create", "Crear usuario nuevo"),
        ),
        required=False,
        label="Tipo de Usuario",
    )
    rol = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        label="Rol del sistema",
        help_text="Solo administradores pueden cambiar el rol.",
    )
    user_existing = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        label="Usuario existente",
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        label="Nuevo usuario",
    )
    email = forms.EmailField(
        required=False,
        label="Correo del usuario",
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Contraseña",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Confirmar contrasena",
    )

    class Meta:
        model = Personal
        exclude = ["user", "admin_requested"]
        widgets = {
            "fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        User = get_user_model()
        qs = User.objects.filter(personal_profile__isnull=True)
        if self.instance and self.instance.pk and self.instance.user_id:
            qs = User.objects.filter(pk=self.instance.user_id) | qs
            self.fields["account_action"].initial = "assign"
            self.fields["user_existing"].initial = self.instance.user
        self.fields["user_existing"].queryset = qs.distinct()
        if not self.instance or not self.instance.pk:
            self.fields["account_action"].initial = "none"
        self.fields["account_action"].help_text = "Selecciona crear o asignar un usuario."
        self.account_fields = (
            "account_action",
            "user_existing",
            "username",
            "email",
            "password1",
            "password2",
        )
        if not is_admin_user(self.request_user):
            self.fields.pop("rol", None)
        elif "rol" in self.fields:
            current_user = self.instance.user if self.instance and self.instance.pk else None
            self.fields["rol"].initial = get_user_role(current_user) if current_user else ROLE_USUARIO

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("account_action") or "none"
        existing_user = cleaned.get("user_existing")
        username = (cleaned.get("username") or "").strip()
        email = (cleaned.get("email") or "").strip()
        password1 = cleaned.get("password1") or ""
        password2 = cleaned.get("password2") or ""

        if action == "none":
            if existing_user or username or email or password1 or password2:
                self.add_error(
                    "account_action",
                    "No llenes datos de usuario si eliges Sin usuario.",
                )
        elif action == "assign":
            if not existing_user:
                self.add_error("user_existing", "Selecciona un usuario.")
            if username or email or password1 or password2:
                self.add_error(
                    "username",
                    "No llenes los datos de usuario nuevo si asignas uno existente.",
                )
        elif action == "create":
            if existing_user:
                self.add_error(
                    "user_existing",
                    "No selecciones un usuario existente si vas a crear uno.",
                )
            if not username:
                self.add_error("username", "Captura un nombre de usuario.")
            elif get_user_model().objects.filter(username__iexact=username).exists():
                self.add_error("username", "Ese nombre de usuario ya existe.")
            if not email:
                self.add_error("email", "Captura un correo de usuario.")
            if not password1 or not password2:
                self.add_error("password1", "Captura la contraseña.")
            elif password1 != password2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(password1)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)

        if action == "assign" and existing_user:
            conflict_qs = Personal.objects.filter(user=existing_user)
            if self.instance and self.instance.pk:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)
            if conflict_qs.exists():
                self.add_error(
                    "user_existing",
                    "Ese usuario ya esta asignado a otro personal.",
                )

        if "rol" in cleaned and cleaned.get("rol") in {ROLE_TECNICO, ROLE_ADMIN}:
            if action == "none":
                self.add_error(
                    "rol",
                    "No puedes asignar Tecnico IT o Administrador sin usuario.",
                )

        return cleaned

    def save(self, commit=True):
        action = self.cleaned_data.get("account_action") or "none"
        rol = self.cleaned_data.get("rol") if "rol" in self.cleaned_data else None
        if action == "create":
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    username=self.cleaned_data["username"].strip(),
                    email=self.cleaned_data["email"].strip(),
                    password=self.cleaned_data["password1"],
                )
                set_user_role(user, rol or ROLE_USUARIO)
                personal = super().save(commit=False)
                personal.user = user
                personal.admin_requested = False
                if commit:
                    personal.save()
                return personal

        personal = super().save(commit=False)
        if action == "assign":
            personal.user = self.cleaned_data.get("user_existing")
        elif action == "none":
            personal.user = None
        if commit:
            personal.save()
            if rol and personal.user:
                set_user_role(personal.user, rol)
                if personal.admin_requested:
                    personal.admin_requested = False
                    personal.save(update_fields=["admin_requested"])
            elif personal.user and rol is None:
                # Sin campo rol (no admin): mantener rol actual o Usuario por defecto.
                if not get_user_role(personal.user):
                    set_user_role(personal.user, ROLE_USUARIO)
        return personal


# ============  Proveedor views ==============
# == Formulario de proveedor
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nombre_proveedor",
            "razon_social",
            "rfc",
            "tipo",
            "contacto",
            "correo",
            "telefono",
            "sitio_web",
            "direccion",
            "ciudad",
            "estado",
            "codigo_postal",
            "notas",
            "activo",
        ]
        labels = {
            "nombre_proveedor": "Nombre comercial",
            "razon_social": "Razon social",
            "rfc": "RFC",
            "tipo": "Tipo de proveedor",
            "contacto": "Contacto",
            "telefono": "Telefono",
            "correo": "Correo electronico",
            "sitio_web": "Sitio web",
            "direccion": "Direccion",
            "ciudad": "Ciudad",
            "estado": "Estado",
            "codigo_postal": "Codigo postal",
            "notas": "Notas / condiciones",
            "activo": "Activo",
        }
        help_texts = {
            "razon_social": "Nombre legal para facturacion, si difiere del comercial.",
            "rfc": "RFC para facturas y ordenes formales.",
            "contacto": "Nombre de la persona de contacto.",
            "notas": "Plazo de pago, garantia, observaciones, etc.",
        }
        widgets = {
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
            "sitio_web": forms.URLInput(attrs={"placeholder": "https://"}),
        }

    def clean_rfc(self):
        rfc = (self.cleaned_data.get("rfc") or "").strip().upper()
        return rfc or None

