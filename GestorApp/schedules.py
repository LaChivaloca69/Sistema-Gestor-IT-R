"""Schedules por defecto de django-q2 (idempotente)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


def ensure_default_schedules():
    """Crea/actualiza schedules de retencion diaria y recordatorios cada 15 min."""
    try:
        from django_q.models import Schedule
    except Exception as exc:
        logger.debug("django_q no disponible para schedules: %s", exc)
        return False

    now = timezone.now()
    # Proxima corrida nocturna ~02:00 local
    next_night = now.replace(hour=2, minute=0, second=0, microsecond=0)
    if next_night <= now:
        next_night += timedelta(days=1)

    Schedule.objects.update_or_create(
        name="historial-retencion-diaria",
        defaults={
            "func": "GestorApp.tasks.task_aplicar_retencion",
            "kwargs": "accion='ambos'",
            "schedule_type": Schedule.DAILY,
            "repeats": -1,
            "next_run": next_night,
        },
    )

    Schedule.objects.update_or_create(
        name="recordatorios-operativos-15m",
        defaults={
            "func": "GestorApp.tasks.task_recordatorios_operativos",
            "schedule_type": Schedule.MINUTES,
            "minutes": 15,
            "repeats": -1,
            "next_run": now + timedelta(minutes=1),
        },
    )
    logger.info("Schedules de background jobs asegurados.")
    return True


def on_post_migrate_ensure_schedules(sender, **kwargs):
    """Tras migrate de GestorApp, asegura schedules si django_q ya existe."""
    try:
        ensure_default_schedules()
    except Exception as exc:
        logger.debug("No se crearon schedules en post_migrate: %s", exc)
