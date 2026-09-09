"""Forms de gobierno: coberturas y solicitudes."""

from django import forms
from django.utils import timezone

from ..cobertura import operativo_user_choices
from ..models import (
    CategoriaEquipo,
    CoberturaTickets,
    Equipo,
    EstadoEquipo,
    EstadoSolicitudEquipo,
    Personal,
    SolicitudEquipo,
)
from ..roles import (
    is_administrador,
    is_operativo,
)
from .common import _get_user_personal



class CoberturaTicketsForm(forms.ModelForm):
    class Meta:
        model = CoberturaTickets
        fields = ["ausente", "suplente", "fecha_inicio", "fecha_fin", "activa", "motivo"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
            "motivo": forms.TextInput(attrs={"placeholder": "Vacaciones, incapacidad..."}),
        }

    def __init__(self, *args, request_user=None, **kwargs):
        self.request_user = request_user
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
        if (
            self.request_user
            and not is_administrador(self.request_user)
            and ausente
            and suplente
            and self.request_user.id
            not in {getattr(ausente, "id", None), getattr(suplente, "id", None)}
        ):
            self.add_error(
                None,
                "Debes ser el tecnico ausente o el suplente de esta cobertura.",
            )
        if cleaned.get("activa") and ausente and inicio and fin:
            solapes = CoberturaTickets.objects.filter(
                ausente=ausente,
                activa=True,
                fecha_inicio__lte=fin,
                fecha_fin__gte=inicio,
            )
            if self.instance.pk:
                solapes = solapes.exclude(pk=self.instance.pk)
            if solapes.exists():
                self.add_error(
                    "fecha_inicio",
                    "Ya hay una cobertura activa de este ausente en esas fechas.",
                )
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
        from ..models import TipoCategoriaInventario

        self.fields["categoria"].queryset = CategoriaEquipo.objects.filter(
            activo=True,
            tipo=TipoCategoriaInventario.EQUIPO,
        ).order_by("nombre_categoria")
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
            personal = _get_user_personal(user)
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


