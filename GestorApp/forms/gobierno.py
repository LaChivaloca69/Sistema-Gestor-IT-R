"""Forms de gobierno: coberturas y solicitudes."""
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
    SeguimientoSolicitudEquipo,
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



class CoberturaTicketsForm(forms.ModelForm):
    class Meta:
        model = CoberturaTickets
        fields = ["ausente", "suplente", "fecha_inicio", "fecha_fin", "activa", "motivo"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
            "motivo": forms.TextInput(attrs={"placeholder": "Vacaciones, incapacidad..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = operativo_user_choices()
        self.fields["ausente"].queryset = qs
        self.fields["suplente"].queryset = qs
        self.fields["ausente"].label = "Tecnico ausente"
        self.fields["suplente"].label = "Suplente"
        if not self.instance.pk:
            today = timezone.localdate()
            self.fields["fecha_inicio"].initial = today
            self.fields["fecha_fin"].initial = today

    def clean(self):
        cleaned = super().clean()
        ausente = cleaned.get("ausente")
        suplente = cleaned.get("suplente")
        inicio = cleaned.get("fecha_inicio")
        fin = cleaned.get("fecha_fin")
        if ausente and suplente and ausente == suplente:
            self.add_error("suplente", "Debe ser distinto al ausente.")
        if inicio and fin and fin < inicio:
            self.add_error("fecha_fin", "No puede ser anterior al inicio.")
        return cleaned



class SolicitudEquipoForm(forms.ModelForm):
    class Meta:
        model = SolicitudEquipo
        fields = [
            "titulo",
            "categoria",
            "urgencia",
            "justificacion",
            "notas_solicitante",
            "personal",
        ]
        widgets = {
            "justificacion": forms.Textarea(attrs={"rows": 4}),
            "titulo": forms.TextInput(attrs={"placeholder": "Ej. Laptop para nuevo ingreso"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["categoria"].queryset = CategoriaEquipo.objects.order_by("nombre_categoria")
        self.fields["categoria"].required = False
        self.fields["personal"].queryset = Personal.objects.filter(activo=True).order_by(
            "nombre", "apellido_paterno"
        )
        self.fields["personal"].required = False
        self.fields["personal"].help_text = (
            "Opcional: a quien se asignaria. Si tienes perfil de personal, se sugiere solo."
        )
        if user and not is_operativo(user):
            # Usuario final: personal fijo a su perfil si existe
            try:
                personal = user.personal_profile
            except Personal.DoesNotExist:
                personal = None
            if personal:
                self.fields["personal"].queryset = Personal.objects.filter(pk=personal.pk)
                self.fields["personal"].initial = personal
                self.fields["personal"].disabled = True
            else:
                self.fields.pop("personal")



class SolicitudEquipoRevisionForm(forms.Form):
    estado = forms.ChoiceField(
        label="Accion",
        choices=[
            (EstadoSolicitudEquipo.EN_REVISION, "En revision"),
            (EstadoSolicitudEquipo.APROBADA, "Aprobar"),
            (EstadoSolicitudEquipo.RECHAZADA, "Rechazar"),
            (EstadoSolicitudEquipo.COMPLETADA, "Cerrar solicitud"),
        ],
        help_text="Cerrar termina la atencion. Si eliges un equipo, se asigna al personal destino.",
    )
    notas_it = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Notas IT",
    )
    equipo = forms.ModelChoiceField(
        queryset=Equipo.objects.none(),
        required=False,
        label="Equipo a asignar",
        help_text="Opcional al aprobar o cerrar. Solo equipos disponibles.",
    )

    def __init__(self, *args, solicitud=None, require_estado=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitud = solicitud
        self.fields["estado"].required = require_estado
        qs = Equipo.objects.filter(
            activo=True,
            estado_equipo=EstadoEquipo.DISPONIBLE,
        ).order_by("codigo_inventario")
        if solicitud and solicitud.categoria_id:
            qs = qs.filter(categoria_id=solicitud.categoria_id)
        self.fields["equipo"].queryset = qs
        if solicitud:
            self.fields["estado"].initial = (
                solicitud.estado
                if solicitud.estado
                in {
                    EstadoSolicitudEquipo.EN_REVISION,
                    EstadoSolicitudEquipo.APROBADA,
                    EstadoSolicitudEquipo.RECHAZADA,
                    EstadoSolicitudEquipo.COMPLETADA,
                }
                else EstadoSolicitudEquipo.EN_REVISION
            )
            self.fields["notas_it"].initial = solicitud.notas_it
            if solicitud.equipo_id:
                self.fields["equipo"].initial = solicitud.equipo_id


class SeguimientoSolicitudEquipoForm(forms.ModelForm):
    class Meta:
        model = SeguimientoSolicitudEquipo
        fields = [
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
            "fecha_check": "Fecha de check",
            "avance_realizado": "Avance realizado",
            "pendiente": "Pendiente",
            "proximo_paso": "Proximo paso",
            "fecha_proximo_seguimiento": "Fecha de proxima revision",
            "usuario": "Usuario",
            "solucion": "Solucion",
            "observacion": "Observaciones",
            "ya_terminado": "Concluido",
        }
        widgets = {
            "avance_realizado": forms.Textarea(attrs={"rows": 3}),
            "pendiente": forms.Textarea(attrs={"rows": 3}),
            "proximo_paso": forms.Textarea(attrs={"rows": 3}),
            "fecha_check": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "fecha_proximo_seguimiento": forms.DateInput(attrs={"type": "date"}),
            "solucion": forms.Textarea(attrs={"rows": 4}),
            "observacion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.fixed_solicitud = kwargs.pop("solicitud", None)
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        if "usuario" in self.fields:
            user_model = get_user_model()
            user_qs = operativo_users_queryset(user_model)
            if self.instance and self.instance.usuario_id:
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

        fecha_check = self.fields.get("fecha_check")
        if fecha_check:
            fecha_check.required = False
            fecha_check.input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"]
            if not (self.instance and self.instance.pk):
                fecha_check.initial = timezone.now()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("ya_terminado") and not (cleaned_data.get("solucion") or "").strip():
            self.add_error("solucion", "Indica la solucion al concluir la revision.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.fixed_solicitud is not None:
            instance.solicitud = self.fixed_solicitud
        if not instance.fecha_check:
            instance.fecha_check = timezone.now()
        if commit:
            instance.save()
            self.save_m2m()
        return instance

