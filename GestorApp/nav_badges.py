"""Conteos ligeros para badges del sidebar."""

from django.db.models import Count
from django.utils import timezone

from .roles import is_operativo


def build_nav_badges(user):
    if not user or not getattr(user, "is_authenticated", False):
        return {}

    # Import diferido para no circularizar con views al cargar apps.
    from .views import (
        _tickets_abiertos_qs,
        _tickets_sla_vencidos_q,
        _seguimientos_alerta_context,
        _mantenimientos_alerta_context,
        _equipos_alerta_context,
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
            }

    return badges
