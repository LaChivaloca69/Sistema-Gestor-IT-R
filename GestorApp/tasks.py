"""Tareas de background (django-q2): retencion e historial de recordatorios."""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

logger = logging.getLogger(__name__)

SLA_REMINDER_CACHE_KEY = "gestor:jobs:sla_reminder_fingerprint"
SLA_REMINDER_TTL = 60 * 60  # no repetir el mismo aviso mas de 1h


def task_aplicar_retencion(accion="ambos", solicitado_por_id=None):
    """
    Archiva / purga historial segun accion: archivar | purgar | ambos.
    Pensada para cola async (django-q) o manage.py.
    """
    from . import historial
    from .metrics_cache import invalidate_metrics_cache
    from .models import AccionHistorial, HistorialActividad, ModuloHistorial, NivelHistorial

    accion = (accion or "ambos").strip().lower()
    if accion == "archivar":
        resultado = {"archivo": historial.archivar_historial(), "purga": {"omitido": True}}
    elif accion == "purgar":
        resultado = {"archivo": {"omitido": True}, "purga": historial.purgar_historial()}
    else:
        accion = "ambos"
        resultado = historial.aplicar_retencion()

    archivados = (resultado.get("archivo") or {}).get("archivados", 0)
    purgados = (resultado.get("purga") or {}).get("purgados", 0)

    usuario = None
    if solicitado_por_id:
        from django.contrib.auth import get_user_model

        usuario = get_user_model().objects.filter(pk=solicitado_por_id).first()

    HistorialActividad.objects.create(
        modulo=ModuloHistorial.SISTEMA,
        accion=AccionHistorial.OTRO,
        nivel=NivelHistorial.ADVERTENCIA if accion in {"purgar", "ambos"} else NivelHistorial.INFO,
        es_automatico=solicitado_por_id is None,
        usuario=usuario,
        titulo=f"Retencion de historial ({accion})",
        descripcion=f"Archivados={archivados}. Purgados={purgados}.",
        metadata={"accion": accion, "resultado": resultado, "origen": "background_job"},
    )
    invalidate_metrics_cache()
    logger.info(
        "Retencion historial OK accion=%s archivados=%s purgados=%s",
        accion,
        archivados,
        purgados,
    )
    return {"accion": accion, "archivados": archivados, "purgados": purgados}


def task_recordatorios_operativos():
    """
    Escanea SLA / mantenimientos vencidos y deja rastro en historial si cambio el estado.
    (Email/Teams se puede enganchar despues reutilizando este conteo.)
    """
    from . import historial
    from .models import AccionHistorial, ModuloHistorial, NivelHistorial
    from .views import (
        _mantenimientos_alerta_context,
        _tickets_abiertos_qs,
        _tickets_sla_por_vencer_q,
        _tickets_sla_vencidos_q,
    )

    now = timezone.now()
    today = timezone.localdate()

    abiertos = _tickets_abiertos_qs(None).annotate(seguimientos_count=Count("seguimientos"))
    sla_vencidos = abiertos.filter(_tickets_sla_vencidos_q(now)).count()
    sla_por_vencer = abiertos.filter(_tickets_sla_por_vencer_q(now)).count()
    mant = _mantenimientos_alerta_context(today=today)
    mant_vencidos = mant.get("mantenimientos_vencidos_count", 0)
    mant_por_vencer = mant.get("mantenimientos_por_vencer_count", 0)

    fingerprint = (
        f"sla:{sla_vencidos}/{sla_por_vencer}|mant:{mant_vencidos}/{mant_por_vencer}"
    )
    previous = cache.get(SLA_REMINDER_CACHE_KEY)
    if previous == fingerprint:
        logger.debug("Recordatorios operativos: sin cambios (%s)", fingerprint)
        return {"skipped": True, "fingerprint": fingerprint}

    cache.set(SLA_REMINDER_CACHE_KEY, fingerprint, SLA_REMINDER_TTL)

    partes = []
    if sla_vencidos:
        partes.append(f"{sla_vencidos} ticket(s) fuera de SLA")
    if sla_por_vencer:
        partes.append(f"{sla_por_vencer} ticket(s) SLA por vencer")
    if mant_vencidos:
        partes.append(f"{mant_vencidos} mantenimiento(s) vencido(s)")
    if mant_por_vencer:
        partes.append(f"{mant_por_vencer} mantenimiento(s) por vencer")

    if not partes:
        # Estado limpio: solo registrar si veniamos de un aviso previo
        if previous:
            historial.registrar_historial(
                request=None,
                modulo=ModuloHistorial.SISTEMA,
                accion=AccionHistorial.OTRO,
                titulo="Recordatorio operativo: sin alertas activas",
                descripcion="SLA y mantenimientos sin pendientes criticos.",
                nivel=NivelHistorial.INFO,
                es_automatico=True,
                metadata={"fingerprint": fingerprint},
            )
        return {"skipped": False, "alertas": 0, "fingerprint": fingerprint}

    titulo = "Recordatorio operativo: " + "; ".join(partes[:2])
    if len(partes) > 2:
        titulo += f" (+{len(partes) - 2} mas)"

    historial.registrar_historial(
        request=None,
        modulo=ModuloHistorial.SISTEMA,
        accion=AccionHistorial.OTRO,
        titulo=titulo[:200],
        descripcion="; ".join(partes),
        nivel=NivelHistorial.ADVERTENCIA if (sla_vencidos or mant_vencidos) else NivelHistorial.INFO,
        es_automatico=True,
        metadata={
            "fingerprint": fingerprint,
            "sla_vencidos": sla_vencidos,
            "sla_por_vencer": sla_por_vencer,
            "mant_vencidos": mant_vencidos,
            "mant_por_vencer": mant_por_vencer,
            "canal": "historial",  # futuro: email / Teams
        },
    )
    logger.info("Recordatorios operativos: %s", fingerprint)
    return {
        "skipped": False,
        "alertas": len(partes),
        "fingerprint": fingerprint,
        "detalle": partes,
    }
