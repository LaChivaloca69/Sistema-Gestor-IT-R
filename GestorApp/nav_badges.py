"""Conteos ligeros para badges del sidebar y notificaciones in-app."""

from django.db.models import Count
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .metrics_cache import get_or_set_user_metric
from .roles import is_operativo


def _safe_reverse(name, query=""):
    try:
        url = reverse(name)
    except NoReverseMatch:
        return None
    return f"{url}?{query}" if query else url


def _compute_nav_badges(user):
    # Import diferido para no circularizar con views al cargar apps.
    from .views import (
        _tickets_abiertos_qs,
        _tickets_sla_vencidos_q,
        _seguimientos_alerta_context,
        _mantenimientos_alerta_context,
        _equipos_alerta_context,
        _consumibles_alerta_context,
    )

    badges = {}
    abiertos = _tickets_abiertos_qs(user).annotate(seguimientos_count=Count("seguimientos"))
    sla = abiertos.filter(_tickets_sla_vencidos_q(timezone.now())).count()
    sin_check = abiertos.filter(seguimientos_count=0).count()
    tickets_badge = sla or sin_check
    if tickets_badge:
        badges["tickets"] = {
            "count": tickets_badge,
            "tone": "danger" if sla else "warn",
            "title": (
                f"{sla} fuera de SLA" if sla else f"{sin_check} sin seguimiento"
            ),
            "sla": sla,
            "sin_check": sin_check,
        }

    if is_operativo(user):
        today = timezone.localdate()
        seg = _seguimientos_alerta_context(today=today)
        seg_count = seg["seguimientos_vencidos_count"] + seg["seguimientos_por_vencer_count"]
        if seg_count:
            badges["seguimiento"] = {
                "count": seg_count,
                "tone": "danger" if seg["seguimientos_vencidos_count"] else "warn",
                "title": (
                    f"{seg['seguimientos_vencidos_count']} vencidos · "
                    f"{seg['seguimientos_por_vencer_count']} por vencer"
                ),
                "vencidos": seg["seguimientos_vencidos_count"],
                "por_vencer": seg["seguimientos_por_vencer_count"],
            }

        mant = _mantenimientos_alerta_context(today=today)
        mant_count = (
            mant["mantenimientos_vencidos_count"] + mant["mantenimientos_por_vencer_count"]
        )
        if mant_count:
            badges["mantenimientos"] = {
                "count": mant_count,
                "tone": "danger" if mant["mantenimientos_vencidos_count"] else "warn",
                "title": (
                    f"{mant['mantenimientos_vencidos_count']} vencidos · "
                    f"{mant['mantenimientos_por_vencer_count']} por vencer"
                ),
                "vencidos": mant["mantenimientos_vencidos_count"],
                "por_vencer": mant["mantenimientos_por_vencer_count"],
            }

        eq = _equipos_alerta_context(today=today)
        eq_count = (
            eq["equipos_sin_ubicacion_count"]
            + eq["equipos_mant_largo_count"]
            + eq["asignaciones_antiguas_count"]
        )
        if eq_count:
            badges["equipos"] = {
                "count": eq_count,
                "tone": "warn",
                "title": (
                    f"{eq['equipos_sin_ubicacion_count']} sin ubic. · "
                    f"{eq['equipos_mant_largo_count']} mant. largo · "
                    f"{eq['asignaciones_antiguas_count']} asig. antiguas"
                ),
                "sin_ubicacion": eq["equipos_sin_ubicacion_count"],
                "mant_largo": eq["equipos_mant_largo_count"],
                "asignaciones": eq["asignaciones_antiguas_count"],
            }

        from .models import EstadoSolicitudEquipo, SolicitudEquipo

        sol_count = SolicitudEquipo.objects.filter(
            estado__in=[
                EstadoSolicitudEquipo.PENDIENTE,
                EstadoSolicitudEquipo.EN_REVISION,
            ]
        ).count()
        if sol_count:
            badges["solicitudes"] = {
                "count": sol_count,
                "tone": "warn",
                "title": f"{sol_count} solicitud(es) por revisar",
            }

        cons = _consumibles_alerta_context()
        if cons["consumibles_bajo_count"]:
            badges["consumibles"] = {
                "count": cons["consumibles_bajo_count"],
                "tone": "warn",
                "title": f"{cons['consumibles_bajo_count']} con stock bajo o agotado",
            }

    return badges


def build_nav_badges(user):
    if not user or not getattr(user, "is_authenticated", False):
        return {}
    return get_or_set_user_metric("nav_badges", user, lambda: _compute_nav_badges(user))


def build_nav_notifications(user, badges=None):
    """Lista plana de avisos para la campana del topbar."""
    if badges is None:
        badges = build_nav_badges(user)
    items = []

    tickets = badges.get("tickets")
    if tickets:
        if tickets.get("sla"):
            items.append(
                {
                    "id": "tickets-sla",
                    "tone": "danger",
                    "label": f"{tickets['sla']} ticket(s) fuera de SLA",
                    "url": _safe_reverse("ticketit_list", "alerta=sla"),
                    "icon": "bi-ticket-perforated",
                }
            )
        elif tickets.get("sin_check"):
            items.append(
                {
                    "id": "tickets-sin-check",
                    "tone": "warn",
                    "label": f"{tickets['sin_check']} ticket(s) sin seguimiento",
                    "url": _safe_reverse("ticketit_list", "sin_seguimiento=1"),
                    "icon": "bi-ticket-perforated",
                }
            )

    seg = badges.get("seguimiento")
    if seg:
        items.append(
            {
                "id": "seguimiento",
                "tone": seg["tone"],
                "label": f"{seg['count']} seguimiento(s) por atender",
                "url": _safe_reverse("seguimientoticket_list", "alerta=atencion"),
                "icon": "bi-check2-square",
            }
        )

    mant = badges.get("mantenimientos")
    if mant:
        items.append(
            {
                "id": "mantenimientos",
                "tone": mant["tone"],
                "label": f"{mant['count']} mantenimiento(s) por atender",
                "url": _safe_reverse("mantenimiento_list", "alerta=atencion"),
                "icon": "bi-tools",
            }
        )

    eq = badges.get("equipos")
    if eq:
        items.append(
            {
                "id": "equipos",
                "tone": eq["tone"],
                "label": f"{eq['count']} aviso(s) de inventario",
                "url": _safe_reverse("equipo_dashboard"),
                "icon": "bi-hdd-rack",
            }
        )

    sol = badges.get("solicitudes")
    if sol:
        items.append(
            {
                "id": "solicitudes",
                "tone": sol["tone"],
                "label": f"{sol['count']} solicitud(es) de equipo",
                "url": _safe_reverse("solicitud_equipo_list", "estado=Pendiente"),
                "icon": "bi-clipboard-plus",
            }
        )

    # Filtrar urls rotas
    items = [item for item in items if item.get("url")]
    total = sum(
        badges[key]["count"]
        for key in ("tickets", "seguimiento", "mantenimientos", "equipos", "solicitudes")
        if key in badges
    )
    return items, total
