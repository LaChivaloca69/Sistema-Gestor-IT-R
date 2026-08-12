"""Forms de tickets, seguimientos, bitácora y answers."""
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
from .common import (  # noqa: F401 — reexportado para vistas
    _get_personal_active_assignment,
    _get_user_personal,
    get_subtipo_ticket_choices,
    get_tipo_equipo_queryset,
)



class TicketITForm(forms.ModelForm):
    sub_tipo_ticket = forms.ChoiceField(required=False, choices=[])
    fecha_support_client = forms.CharField(required=False, widget=forms.HiddenInput())


    class Meta:
        model = TicketIT
        exclude = ["folio_ticket", "fecha_support", "status"]
        labels = {
            "requerimiento": "Problema que presenta",
            "solicitado_por": "Solicitado por",
            "asignado_a": "Asignado a",
            "area": "Área",
            "puesto": "Puesto",
            "tipo_ticket": "Tipo de ticket",
            "sub_tipo_ticket": "Subtipo de ticket",
            "prioridad": "Prioridad",
            "equipo": "Equipo",
            "tipo_equipo": "Tipo de equipo",
            "otro_tipo_equipo": "Otro tipo de equipo",
            "detalle": "Detalle",
            "descripcion": "Descripción",
            "imagen": "Imagen",
        }
        help_texts = {
            "requerimiento": "Descripcion breve del problema.",
            "area": "Indicar su localizacion.",
            "tipo_ticket": "Seleccione el tipo de ticket.",
            "sub_tipo_ticket": "Seleccione el subtipo de ticket.",
            "prioridad": "Seleccione la prioridad del ticket.",
            "asignado_a": "Tecnico o staff responsable del ticket.",
            "detalle": "Proporcione detalles adicionales sobre el problema.",
            "descripcion": "Describa detalladamente el problema o solicitud.",
            "imagen": "Adjunte una imagen del problema, si aplica.",
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        self.request_personal = _get_user_personal(self.request_user)
        self.request_assignment = _get_personal_active_assignment(self.request_personal)

        tipo_ticket = None
        if self.data.get("tipo_ticket"):
            tipo_ticket = self.data.get("tipo_ticket")
        elif self.instance and self.instance.pk:
            tipo_ticket = self.instance.tipo_ticket

        self.fields["sub_tipo_ticket"].choices = get_subtipo_ticket_choices(tipo_ticket)
        current_tipo_equipo = None
        if self.instance and self.instance.pk:
            current_tipo_equipo = self.instance.tipo_equipo
        elif self.request_assignment and self.request_assignment.equipo_id:
            current_tipo_equipo = self.request_assignment.equipo.categoria
        self.fields["tipo_equipo"].queryset = get_tipo_equipo_queryset(current_tipo_equipo)
        if current_tipo_equipo:
            self.fields["tipo_equipo"].initial = current_tipo_equipo

        if "equipo" in self.fields:
            self.fields["equipo"].label_from_instance = (
                lambda obj: f"{obj.codigo_inventario} - {obj.categoria}"
            )
            if not (self.instance and self.instance.pk) and self.request_assignment and self.request_assignment.equipo_id:
                self.fields["equipo"].initial = self.request_assignment.equipo

        if "area" in self.fields and not (self.instance and self.instance.pk) and self.request_personal:
            self.fields["area"].initial = self.request_personal.area
        if "puesto" in self.fields and not (self.instance and self.instance.pk) and self.request_personal:
            self.fields["puesto"].initial = self.request_personal.puesto

        if "solicitado_por" in self.fields:
            if (
                self.request_user
                and getattr(self.request_user, "is_authenticated", False)
                and not is_operativo(self.request_user)
            ):
                self.fields["solicitado_por"].initial = self.request_user
                self.fields["solicitado_por"].disabled = True

        if "asignado_a" in self.fields:
            user_model = get_user_model()
            user_qs = operativo_users_queryset(user_model)
            if self.instance and self.instance.asignado_a_id:
                # No OR de querysets distinct/non-distinct (TypeError en Django).
                user_qs = user_model.objects.filter(
                    Q(pk=self.instance.asignado_a_id) | Q(pk__in=user_qs.values("pk"))
                )
            self.fields["asignado_a"].queryset = user_qs.distinct().order_by(
                user_model.USERNAME_FIELD
            )
            self.fields["asignado_a"].required = False
            if not is_operativo(self.request_user):
                self.fields["asignado_a"].disabled = True
                if not (self.instance and self.instance.pk):
                    self.fields.pop("asignado_a")

        if not (self.instance and self.instance.pk) and self.request_personal:
            if "area" in self.fields:
                self.fields["area"].help_text = "Favor de comprobar que el área sea correcta."
            if "puesto" in self.fields:
                self.fields["puesto"].help_text = "Favor de comprobar que el puesto sea correcto."
            if "equipo" in self.fields:
                self.fields["equipo"].help_text = "Favor de comprobar que el equipo sea correcto."
            if "tipo_equipo" in self.fields:
                self.fields["tipo_equipo"].help_text = "Favor de comprobar que el tipo de equipo sea correcto."

    def clean_imagen(self):
        from ..media_security import validate_image_upload

        return validate_image_upload(self.cleaned_data.get("imagen"))

    def _parse_client_datetime(self, value):
        if not value:
            return None

        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def save(self, commit=True):
        instance = super().save(commit=False)
        client_value = self.cleaned_data.get("fecha_support_client")
        client_datetime = self._parse_client_datetime(client_value)
        if client_datetime and not instance.pk:
            instance.fecha_support = client_datetime

        if (
            self.request_user
            and getattr(self.request_user, "is_authenticated", False)
            and not is_operativo(self.request_user)
            and not instance.solicitado_por_id
        ):
            instance.solicitado_por = self.request_user

        # Asignar a alguien un ticket Abierto lo pasa a En Revision.
        if instance.asignado_a_id and instance.status == EstadoSupport.ABIERTO:
            instance.status = EstadoSupport.EN_REVISION

        if commit:
            instance.save()
            self.save_m2m()
        return instance



class SeguimientoTicketForm(forms.ModelForm):
    class Meta:
        model = SeguimientoTicket
        fields = [
            "ticket",
            "fecha_check",
            "avance_realizado",
            "pendiente",
            "proximo_paso",
            "fecha_proximo_seguimiento",
            "usuario",
            "solucion",
            "observacion",
            "ya_terminado",
        ]
        labels = {
            "ticket": "Ticket",
            "fecha_check": "Fecha de check",
            "avance_realizado": "Avance realizado",
            "pendiente": "Pendiente",
            "proximo_paso": "Próximo paso",
            "fecha_proximo_seguimiento": "Fecha de próximo seguimiento",
            "usuario": "Usuario",
            "solucion": "Solución",
            "observacion": "Observaciones",
            "ya_terminado": "Concluido",
        }
        widgets = {
            "avance_realizado": forms.Textarea(attrs={"rows": 3}),
            "pendiente": forms.Textarea(attrs={"rows": 3}),
            "proximo_paso": forms.Textarea(attrs={"rows": 3}),
            "fecha_check": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "fecha_proximo_seguimiento": forms.DateInput(attrs={"type": "date"}),
            "solucion": forms.Textarea(attrs={"rows": 4}),
            "observacion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.fixed_ticket = kwargs.pop("ticket", None)
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        if self.fixed_ticket is not None:
            self.fields["ticket"].initial = self.fixed_ticket
            self.fields["ticket"].queryset = TicketIT.objects.filter(pk=self.fixed_ticket.pk)
            self.fields["ticket"].disabled = True
            self.fields["ticket"].widget = forms.HiddenInput()
        else:
            qs = TicketIT.objects.exclude(status=EstadoSupport.CERRADO)
            if self.instance and self.instance.ticket_id:
                qs = TicketIT.objects.filter(
                    Q(status__in=[EstadoSupport.ABIERTO, EstadoSupport.EN_REVISION, EstadoSupport.EN_PROCESO])
                    | Q(pk=self.instance.ticket_id)
                )
            self.fields["ticket"].queryset = qs.order_by("folio_ticket")

        if "usuario" in self.fields:
            user_model = get_user_model()
            user_qs = operativo_users_queryset(user_model)
            if self.instance and self.instance.usuario_id:
                # No OR de querysets distinct/non-distinct (TypeError en Django).
                user_qs = user_model.objects.filter(
                    Q(pk=self.instance.usuario_id) | Q(pk__in=user_qs.values("pk"))
                )
            self.fields["usuario"].queryset = user_qs.distinct().order_by(
                user_model.USERNAME_FIELD
            )
            if (
                not (self.instance and self.instance.pk)
                and self.request_user
                and getattr(self.request_user, "is_authenticated", False)
                and is_operativo(self.request_user)
            ):
                self.fields["usuario"].initial = self.request_user

        if "solucion" in self.fields:
            self.fields["solucion"].required = False
            self.fields["solucion"].help_text = "Obligatoria al marcar Concluido."

    def clean(self):
        cleaned_data = super().clean()
        if self.fixed_ticket is not None:
            cleaned_data["ticket"] = self.fixed_ticket
        if cleaned_data.get("ya_terminado") and not (cleaned_data.get("solucion") or "").strip():
            self.add_error("solucion", "Indica la solucion al concluir el seguimiento.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.fixed_ticket is not None:
            instance.ticket = self.fixed_ticket
        if commit:
            instance.save()
            self.save_m2m()
        return instance




# =========== Bitacora views =============
class BitacoraForm(forms.ModelForm):
    class Meta:
        model = Bitacora
        fields = "__all__"
        labels = {
            "folio_bitacora": "Folio de bitacora",
            "fecha_bitacora": "Fecha de bitacora",
            "Situacion": "Situacion",
            "descripcion_situacion": "Descripcion de la situacion",
        }
        help_texts = {
            "descripcion_bitacora": "Descripcion",
            "Situacion": "Problema o situacion que se presenta.",
        }
        widgets = {
            "fecha_bitacora": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "descripcion_situacion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fecha_bitacora = self.fields.get("fecha_bitacora")
        if fecha_bitacora:
            fecha_bitacora.widget = forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            )
            fecha_bitacora.input_formats = ["%Y-%m-%dT%H:%M"]



# =========== Answer views =============
class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = "__all__"
        labels = {
            "folio_answer": "Folio",
            "fecha_answer": "Fecha",
            "solucion": "Solucion",
            "descripcion_solucion": "Descripcion de la solucion",
        }
        help_texts = {
            "descripcion_answer": "Descripcion",
            "descripcion_solucion": "Descripcion de la solucion",
        }
        widgets = {
            "fecha_answer": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "descripcion_solucion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fecha_answer = self.fields.get("fecha_answer")
        if fecha_answer:
            fecha_answer.widget = forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            )
            fecha_answer.input_formats = ["%Y-%m-%dT%H:%M"]

