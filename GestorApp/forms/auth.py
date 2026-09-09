"""Registro de usuario."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from ..models import (
    Personal,
)


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": (
            "Usuario o contraseña incorrectos. "
            "Revisa que esten bien escritos (mayusculas y minusculas cuentan)."
        ),
        "inactive": "Esta cuenta esta desactivada. Contacta a un administrador.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["password"].label = "Contraseña"
        self.fields["username"].widget.attrs.update(
            {
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "Tu usuario",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "autocomplete": "current-password",
                "placeholder": "Tu contraseña",
            }
        )


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

