"""Helpers para encolar tareas con django-q2 (fallback sincrono si no hay worker)."""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def background_jobs_enabled():
    return bool(getattr(settings, "BACKGROUND_JOBS_ENABLED", True))


def enqueue(func_path, *args, sync_fallback=True, **kwargs):
    """
    Encola `func_path` (dotted path) en django-q.
    Si falla o BACKGROUND_JOBS_SYNC=True, ejecuta en el request actual.
    Returns: (result_or_task_id, mode) donde mode es 'async' | 'sync'.
    """
    force_sync = bool(getattr(settings, "BACKGROUND_JOBS_SYNC", False))
    if force_sync or not background_jobs_enabled():
        return _run_sync(func_path, *args, **kwargs), "sync"

    try:
        from django_q.tasks import async_task

        task_id = async_task(func_path, *args, **kwargs)
        return task_id, "async"
    except Exception as exc:
        logger.warning("No se pudo encolar %s (%s). Fallback sync=%s", func_path, exc, sync_fallback)
        if not sync_fallback:
            raise
        return _run_sync(func_path, *args, **kwargs), "sync"


def _run_sync(func_path, *args, **kwargs):
    from django.utils.module_loading import import_string

    func = import_string(func_path)
    return func(*args, **kwargs)


def enqueue_retencion(accion="ambos", solicitado_por_id=None):
    return enqueue(
        "GestorApp.tasks.task_aplicar_retencion",
        accion,
        solicitado_por_id,
    )


def enqueue_recordatorios():
    return enqueue("GestorApp.tasks.task_recordatorios_operativos")
