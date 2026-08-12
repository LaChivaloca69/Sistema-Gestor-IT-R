"""Shared helpers: tickets/OC permissions, dates, equipo movements."""
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.utils import timezone

from .. import historial
from ..cobertura import ticket_asignados_q_for_user
from ..roles import is_admin_user, is_operativo
from ..models import (
    AsignacionEquipo,
    EstadoAsignacion,
    EstadoEquipo,
    EstadoSupport,
    MovimientoEquipo,
    ModuloHistorial,
    NivelHistorial,
    OrdenCompra,
    PrioridadSupport,
    SLA_HORAS_POR_PRIORIDAD,
    TicketIT,
    TipoTicketSupport,
)

def _ticket_has_seguimientos(ticket):
    if ticket is None:
        return False
    if hasattr(ticket, "seguimientos_count"):
        return bool(ticket.seguimientos_count)
    return ticket.seguimientos.exists()


def user_can_view_ticket(user, ticket):
    if not user or not user.is_authenticated or ticket is None:
        return False
    if is_operativo(user):
        return True
    return ticket.solicitado_por_id == user.id


def user_can_edit_ticket(user, ticket):
    if not user or not user.is_authenticated or ticket is None:
        return False
    if is_operativo(user):
        return True
    if ticket.solicitado_por_id != user.id:
        return False
    # Solicitante solo edita mientras el ticket sigue Abierto y sin checks.
    return ticket.status == EstadoSupport.ABIERTO and not _ticket_has_seguimientos(ticket)


def user_can_delete_ticket(user, ticket):
    if not is_admin_user(user) or ticket is None:
        return False
    return not _ticket_has_seguimientos(ticket)


def user_can_manage_ticket_flow(user):
    return is_operativo(user)


def _deny_ticket_access(request, message="No tienes permisos para este ticket."):
    messages.error(request, message)
    return redirect("ticketit_list")


def _tickets_for_user(user, qs=None):
    qs = qs if qs is not None else TicketIT.objects.all()
    if is_operativo(user):
        return qs
    return qs.filter(solicitado_por=user)


def _ordenes_for_user(user, qs=None):
    qs = qs if qs is not None else OrdenCompra.objects.all()
    if is_operativo(user):
        return qs
    return qs.filter(elaborado_por=user)


def user_can_manage_orden(user, orden):
    if not user or not user.is_authenticated or orden is None:
        return False
    if is_operativo(user):
        return True
    return orden.elaborado_por_id == user.id


def _tickets_sla_vencidos_q(now=None):
    now = now or timezone.now()
    query = Q(pk__in=[])  # empty base
    for prioridad, horas in SLA_HORAS_POR_PRIORIDAD.items():
        query |= Q(
            prioridad=prioridad,
            fecha_support__lt=now - timedelta(hours=horas),
        )
    return query


def _tickets_sla_por_vencer_q(now=None):
    """Tickets activos cuyo SLA(service level agreement) aun no vence pero estan cerca del limite."""
    now = now or timezone.now()
    query = Q(pk__in=[])
    for prioridad, horas in SLA_HORAS_POR_PRIORIDAD.items():
        limite_vencido = now - timedelta(hours=horas)
        umbral = min(timedelta(hours=4), timedelta(hours=horas) * 0.25)
        # Por vencer: fecha_support > limite_vencido (aun no vencido)
        # y fecha_support <= now - (horas*timedelta - umbral)  i.e. within umbral of deadline
        inicio_aviso = now - timedelta(hours=horas) + umbral
        query |= Q(
            prioridad=prioridad,
            fecha_support__gt=limite_vencido,
            fecha_support__lte=inicio_aviso,
        )
    return query


def _tickets_abiertos_qs(user=None):
    qs = TicketIT.objects.exclude(status=EstadoSupport.CERRADO)
    if user is not None:
        qs = _tickets_for_user(user, qs)
    return qs


def _ticket_dashboard_context(user):
    abiertos = _tickets_abiertos_qs(user).annotate(seguimientos_count=Count("seguimientos"))
    now = timezone.now()
    sla_vencidos_qs = abiertos.filter(_tickets_sla_vencidos_q(now)).order_by("fecha_support")
    sla_por_vencer_qs = abiertos.filter(_tickets_sla_por_vencer_q(now)).order_by("fecha_support")
    sin_seguimiento_qs = abiertos.filter(seguimientos_count=0).order_by("-fecha_support")

    por_prioridad = []
    for value, label in PrioridadSupport.choices:
        count = abiertos.filter(prioridad=value).count()
        por_prioridad.append(
            {
                "value": value,
                "label": label,
                "count": count,
                "horas_sla": SLA_HORAS_POR_PRIORIDAD.get(value),
            }
        )

    por_tipo = []
    for value, label in TipoTicketSupport.choices:
        por_tipo.append(
            {
                "value": value,
                "label": label,
                "count": abiertos.filter(tipo_ticket=value).count(),
            }
        )

    por_estado = []
    for value, label in EstadoSupport.choices:
        if value == EstadoSupport.CERRADO:
            continue
        por_estado.append(
            {
                "value": value,
                "label": label,
                "count": abiertos.filter(status=value).count(),
            }
        )

    return {
        "ticket_dashboard": {
            "abiertos": abiertos.count(),
            "sla_vencidos": sla_vencidos_qs.count(),
            "sla_por_vencer": sla_por_vencer_qs.count(),
            "sin_seguimiento": sin_seguimiento_qs.count(),
            "por_prioridad": por_prioridad,
            "por_tipo": por_tipo,
            "por_estado": por_estado,
            "sla_tabla": [
                {"prioridad": label, "horas": SLA_HORAS_POR_PRIORIDAD[value]}
                for value, label in PrioridadSupport.choices
            ],
            "tickets_sla_vencidos": list(
                sla_vencidos_qs.select_related("solicitado_por", "asignado_a")[:8]
            ),
            "tickets_sin_seguimiento": list(
                sin_seguimiento_qs.select_related("solicitado_por", "asignado_a")[:8]
            ),
        }
    }


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _end_of_month(start_date):
    if start_date.month == 12:
        next_month = date(start_date.year + 1, 1, 1)
    else:
        next_month = date(start_date.year, start_date.month + 1, 1)
    return next_month - timedelta(days=1)


def _month_bounds(value):
    if not value:
        return None, None
    try:
        year_str, month_str = value.split("-")
        year = int(year_str)
        month = int(month_str)
    except (ValueError, AttributeError):
        return None, None
    if month < 1 or month > 12:
        return None, None
    start = date(year, month, 1)
    return start, _end_of_month(start)


def _quick_range_bounds(value):
    if not value:
        return None, None
    today = timezone.localdate()
    if value == "last_7":
        return today - timedelta(days=6), today
    if value == "last_30":
        return today - timedelta(days=29), today
    if value == "this_month":
        start = date(today.year, today.month, 1)
        return start, _end_of_month(start)
    if value == "last_month":
        first_this_month = date(today.year, today.month, 1)
        last_month_end = first_this_month - timedelta(days=1)
        start = date(last_month_end.year, last_month_end.month, 1)
        return start, last_month_end
    if value == "this_year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    return None, None


def _apply_date_filters(items, field_name, start_date, end_date):
    if start_date:
        items = items.filter(**{f"{field_name}__gte": start_date})
    if end_date:
        items = items.filter(**{f"{field_name}__lte": end_date})
    return items


def _get_equipo_asignacion_activa(equipo):
    if not equipo:
        return None
    return (
        AsignacionEquipo.objects.select_related("personal")
        .filter(equipo=equipo, estado_asignacion=EstadoAsignacion.ACTIVA)
        .order_by("-fecha_asignacion")
        .first()
    )


def _get_equipo_responsable(equipo):
    asignacion = _get_equipo_asignacion_activa(equipo)
    if asignacion and asignacion.personal_id:
        return asignacion.personal
    return None


def _cerrar_asignaciones_activas(equipo, exclude_pk=None, observaciones=None):
    """Marca como Devuelta cualquier asignacion activa del equipo."""
    if not equipo:
        return 0
    qs = AsignacionEquipo.objects.filter(
        equipo=equipo,
        estado_asignacion=EstadoAsignacion.ACTIVA,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    now = timezone.now()
    updated = 0
    for asignacion in qs:
        asignacion.estado_asignacion = EstadoAsignacion.DEVUELTA
        if not asignacion.fecha_devolucion:
            asignacion.fecha_devolucion = now
        if observaciones and not asignacion.observaciones:
            asignacion.observaciones = observaciones
        asignacion.save(
            update_fields=["estado_asignacion", "fecha_devolucion", "observaciones"]
        )
        updated += 1
    return updated


def _reconciliar_estado_equipo(equipo, save=True):
    """
    Disponible/Asignado siguen a la asignacion activa.
    No toca Baja ni En Mantenimiento.
    """
    if not equipo:
        return None
    if equipo.estado_equipo in {EstadoEquipo.BAJA, EstadoEquipo.EN_MANTENIMIENTO}:
        return equipo
    tiene_activa = AsignacionEquipo.objects.filter(
        equipo=equipo,
        estado_asignacion=EstadoAsignacion.ACTIVA,
    ).exists()
    nuevo = EstadoEquipo.ASIGNADO if tiene_activa else EstadoEquipo.DISPONIBLE
    if equipo.estado_equipo != nuevo:
        equipo.estado_equipo = nuevo
        if save:
            equipo.save(update_fields=["estado_equipo"])
    return equipo


def _crear_movimiento(
    equipo,
    tipo_movimiento,
    origen=None,
    destino=None,
    responsable=None,
    observaciones=None,
    request=None,
):
    if not equipo:
        return None
    movimiento = MovimientoEquipo.objects.create(
        equipo=equipo,
        tipo_movimiento=tipo_movimiento,
        origen=str(origen) if origen else None,
        destino=str(destino) if destino else None,
        responsable=responsable,
        observaciones=observaciones or None,
    )
    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MOVIMIENTO_EQUIPO,
        accion=historial.AccionHistorial.OTRO,
        titulo=f"{tipo_movimiento}: {equipo.codigo_inventario}",
        descripcion=observaciones or "",
        objeto=movimiento,
        objeto_etiqueta=str(equipo),
        entidad_relacionada=equipo,
        enlace_nombre="movimientoequipo_detail",
        es_automatico=True,
        nivel=NivelHistorial.INFO,
        metadata={
            "tipo_movimiento": tipo_movimiento,
            "origen": str(origen) if origen else None,
            "destino": str(destino) if destino else None,
            "responsable": str(responsable) if responsable else None,
        },
    )
    return movimiento

# =========== Area views ==============
# Formulario de area 
