from django import forms
from django.db.models import Q

from .models import Answer, EstadoSupport, SeguimientoTicket, TicketIT


class TicketITForm(forms.ModelForm):
    class Meta:
        model = TicketIT
        exclude = ["folio_ticket"]


class SeguimientoTicketForm(forms.ModelForm):
    class Meta:
        model = SeguimientoTicket
        fields = [
            "ticket",
            "fecha_check",
            "usuario",
            "solucion",
            "observacion",
            "ya_terminado",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TicketIT.objects.filter(
            status=EstadoSupport.ABIERTO,
            ticket_check__isnull=True,
        )
        if self.instance and self.instance.ticket_id:
            qs = TicketIT.objects.filter(
                Q(status=EstadoSupport.ABIERTO, ticket_check__isnull=True)
                | Q(pk=self.instance.ticket_id)
            )
        self.fields["ticket"].queryset = qs.order_by("folio_ticket")


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = [
            "bitacora",
            "fecha_answer",
            "solucion",
            "descripcion_solucion",
        ]
