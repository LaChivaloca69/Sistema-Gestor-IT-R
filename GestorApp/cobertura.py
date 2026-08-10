"""Helpers de gobierno: coberturas vigentes y consultas asociadas."""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import CoberturaTickets
from .roles import operativo_users_queryset


def coberturas_vigentes_qs(on_date=None):
    on_date = on_date or timezone.localdate()
    return CoberturaTickets.objects.filter(
        activa=True,
        fecha_inicio__lte=on_date,
        fecha_fin__gte=on_date,
    ).select_related("ausente", "suplente", "creado_por")


def user_ids_covered_by(suplente, on_date=None):
    """IDs de usuarios ausentes que este suplente cubre hoy."""
    if not suplente or not getattr(suplente, "is_authenticated", False):
        return []
    return list(
        coberturas_vigentes_qs(on_date)
        .filter(suplente=suplente)
        .values_list("ausente_id", flat=True)
    )


def coberturas_activas_para_suplente(suplente, on_date=None):
    if not suplente or not getattr(suplente, "is_authenticated", False):
        return CoberturaTickets.objects.none()
    return coberturas_vigentes_qs(on_date).filter(suplente=suplente)


def ticket_asignados_q_for_user(user, on_date=None):
    """
    Q para tickets 'asignados a mi', incluyendo ausentes que cubro.
    """
    covered = user_ids_covered_by(user, on_date=on_date)
    q = Q(asignado_a=user)
    if covered:
        q |= Q(asignado_a_id__in=covered)
    return q


def operativo_user_choices():
    return operativo_users_queryset(get_user_model())
