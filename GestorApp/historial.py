"""Registro centralizado de actividad del sistema y politica de retencion."""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import AccionHistorial, HistorialActividad, ModuloHistorial, NivelHistorial


def _resolver_usuario(request=None, usuario=None):
    if usuario is not None:
        return usuario
    if request is not None and getattr(request, "user", None) and request.user.is_authenticated:
        return request.user
    return None


def _meta_objeto(objeto):
    if objeto is None:
        return "", None, ""
    return objeto._meta.label, objeto.pk, str(objeto)


def metadata_desde_formulario(form):
    if not getattr(form, "changed_data", None):
        return None
    cambios = {}
    for nombre_campo in form.changed_data:
        if nombre_campo not in form.fields:
            continue
        valor_nuevo = form.cleaned_data.get(nombre_campo)
        valor_anterior = form.initial.get(nombre_campo) if form.initial else None
        if hasattr(valor_anterior, "pk"):
            valor_anterior = valor_anterior.pk
        if hasattr(valor_nuevo, "pk"):
            valor_nuevo = valor_nuevo.pk
        cambios[nombre_campo] = {"antes": valor_anterior, "despues": valor_nuevo}
    return cambios or None


def registrar_historial(
    *,
    modulo,
    accion,
    titulo,
    request=None,
    usuario=None,
    descripcion="",
    objeto=None,
    objeto_etiqueta="",
    entidad_relacionada=None,
    entidad_relacionada_etiqueta="",
    enlace_nombre="",
    enlace_pk=None,
    metadata=None,
    fecha=None,
    nivel=NivelHistorial.INFO,
    es_automatico=False,
):
    """Crea un registro en el historial general."""
    objeto_tipo, objeto_id, etiqueta_objeto = _meta_objeto(objeto)
    if not objeto_etiqueta:
        objeto_etiqueta = etiqueta_objeto

    rel_tipo, rel_id, rel_etiqueta = _meta_objeto(entidad_relacionada)
    if not entidad_relacionada_etiqueta:
        entidad_relacionada_etiqueta = rel_etiqueta

    if enlace_pk is None and objeto_id is not None:
        enlace_pk = objeto_id

    return HistorialActividad.objects.create(
        fecha=fecha or timezone.now(),
        modulo=modulo,
        accion=accion,
        nivel=nivel,
        es_automatico=bool(es_automatico),
        usuario=_resolver_usuario(request=request, usuario=usuario),
        titulo=titulo[:200],
        descripcion=descripcion or "",
        objeto_tipo=objeto_tipo,
        objeto_id=objeto_id,
        objeto_etiqueta=objeto_etiqueta[:180],
        entidad_relacionada_tipo=rel_tipo,
        entidad_relacionada_id=rel_id,
        entidad_relacionada_etiqueta=(entidad_relacionada_etiqueta or "")[:180],
        enlace_nombre=enlace_nombre or "",
        enlace_pk=enlace_pk,
        metadata=metadata,
    )


def registrar_creacion(
    request,
    *,
    modulo,
    titulo,
    objeto,
    enlace_nombre="",
    descripcion="",
    metadata=None,
    entidad_relacionada=None,
    nivel=NivelHistorial.INFO,
    es_automatico=False,
):
    return registrar_historial(
        request=request,
        modulo=modulo,
        accion=AccionHistorial.CREACION,
        titulo=titulo,
        descripcion=descripcion,
        objeto=objeto,
        entidad_relacionada=entidad_relacionada,
        enlace_nombre=enlace_nombre,
        metadata=metadata,
        nivel=nivel,
        es_automatico=es_automatico,
    )


def registrar_actualizacion(
    request,
    *,
    modulo,
    titulo,
    objeto,
    form=None,
    enlace_nombre="",
    descripcion="",
    metadata=None,
    entidad_relacionada=None,
    nivel=NivelHistorial.INFO,
    es_automatico=False,
):
    if metadata is not None:
        meta = metadata
    elif form is not None:
        meta = metadata_desde_formulario(form)
    else:
        meta = None
    return registrar_historial(
        request=request,
        modulo=modulo,
        accion=AccionHistorial.ACTUALIZACION,
        titulo=titulo,
        descripcion=descripcion,
        objeto=objeto,
        entidad_relacionada=entidad_relacionada,
        enlace_nombre=enlace_nombre,
        metadata=meta,
        nivel=nivel,
        es_automatico=es_automatico,
    )


def registrar_eliminacion(
    request,
    *,
    modulo,
    titulo,
    objeto=None,
    descripcion="",
    metadata=None,
    entidad_relacionada=None,
    nivel=NivelHistorial.ADVERTENCIA,
    es_automatico=False,
):
    return registrar_historial(
        request=request,
        modulo=modulo,
        accion=AccionHistorial.ELIMINACION,
        titulo=titulo,
        descripcion=descripcion,
        objeto=objeto,
        entidad_relacionada=entidad_relacionada,
        metadata=metadata,
        nivel=nivel,
        es_automatico=es_automatico,
    )


# ------------ Politica de retencion ------------
#
# Flujo recomendado (archivar_luego_purgar):
#   1) Activo: visible en la lista principal (archivado=False).
#   2) Archivar: despues de HISTORIAL_RETENCION["dias_activo"] dias, se marca
#      archivado=True. Sigue en BD y se puede consultar con filtro "Archivados".
#   3) Purgar: despues de HISTORIAL_RETENCION["dias_archivo"] dias desde
#      fecha_archivado (o desde fecha si modo solo_purgar), se BORRA de la BD.
#
# Modos:
#   - archivar_luego_purgar (default): primero oculta, luego elimina.
#   - solo_archivar: nunca borra; solo marca archivado.
#   - solo_purgar: borra directo al cumplir dias_activo (sin paso intermedio).


def _config_retencion():
    cfg = getattr(settings, "HISTORIAL_RETENCION", {}) or {}
    return {
        "modo": cfg.get("modo", "archivar_luego_purgar"),
        "dias_activo": int(cfg.get("dias_activo", 180)),
        "dias_archivo": int(cfg.get("dias_archivo", 365)),
        "proteger_criticos": bool(cfg.get("proteger_criticos", True)),
    }


def queryset_candidatos_archivo(ahora=None):
    cfg = _config_retencion()
    ahora = ahora or timezone.now()
    limite = ahora - timedelta(days=cfg["dias_activo"])
    qs = HistorialActividad.objects.filter(archivado=False, fecha__lt=limite)
    if cfg["proteger_criticos"]:
        qs = qs.exclude(nivel=NivelHistorial.CRITICO)
    return qs


def queryset_candidatos_purga(ahora=None):
    cfg = _config_retencion()
    ahora = ahora or timezone.now()
    modo = cfg["modo"]

    if modo == "solo_archivar":
        return HistorialActividad.objects.none()

    if modo == "solo_purgar":
        limite = ahora - timedelta(days=cfg["dias_activo"])
        qs = HistorialActividad.objects.filter(fecha__lt=limite)
    else:
        # archivar_luego_purgar: purga solo lo ya archivado hace dias_archivo
        limite = ahora - timedelta(days=cfg["dias_archivo"])
        qs = HistorialActividad.objects.filter(
            Q(archivado=True) & (Q(fecha_archivado__lt=limite) | Q(fecha_archivado__isnull=True, fecha__lt=limite))
        )

    if cfg["proteger_criticos"]:
        qs = qs.exclude(nivel=NivelHistorial.CRITICO)
    return qs


def archivar_historial(*, dry_run=False, ahora=None):
    """Marca como archivados los registros que ya cumplieron dias_activo."""
    cfg = _config_retencion()
    if cfg["modo"] == "solo_purgar":
        return {"archivados": 0, "omitido": "modo solo_purgar"}

    ahora = ahora or timezone.now()
    qs = queryset_candidatos_archivo(ahora=ahora)
    total = qs.count()
    if dry_run or total == 0:
        return {"archivados": total, "dry_run": dry_run}

    actualizados = qs.update(archivado=True, fecha_archivado=ahora)
    return {"archivados": actualizados, "dry_run": False}


def purgar_historial(*, dry_run=False, ahora=None):
    """Elimina permanentemente registros segun la politica de retencion."""
    ahora = ahora or timezone.now()
    qs = queryset_candidatos_purga(ahora=ahora)
    total = qs.count()
    if dry_run or total == 0:
        return {"purgados": total, "dry_run": dry_run}

    borrados, _ = qs.delete()
    return {"purgados": borrados, "dry_run": False}


def aplicar_retencion(*, dry_run=False, ahora=None):
    """Ejecuta archivo y/o purga segun HISTORIAL_RETENCION['modo']."""
    ahora = ahora or timezone.now()
    cfg = _config_retencion()
    resultado = {"modo": cfg["modo"], "config": cfg}
    resultado["archivo"] = archivar_historial(dry_run=dry_run, ahora=ahora)
    resultado["purga"] = purgar_historial(dry_run=dry_run, ahora=ahora)
    return resultado


__all__ = [
    "AccionHistorial",
    "ModuloHistorial",
    "NivelHistorial",
    "aplicar_retencion",
    "archivar_historial",
    "metadata_desde_formulario",
    "purgar_historial",
    "queryset_candidatos_archivo",
    "queryset_candidatos_purga",
    "registrar_actualizacion",
    "registrar_creacion",
    "registrar_eliminacion",
    "registrar_historial",
]
