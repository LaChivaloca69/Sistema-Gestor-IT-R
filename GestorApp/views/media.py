"""Entrega de archivos en MEDIA_ROOT solo a usuarios autenticados."""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.views.static import serve


def resolve_media_file(path):
    """Devuelve el Path absoluto dentro de MEDIA_ROOT, o None si es invalido."""
    media_root = Path(settings.MEDIA_ROOT).resolve()
    requested = (media_root / path).resolve()
    try:
        requested.relative_to(media_root)
    except ValueError:
        return None
    if not requested.is_file():
        return None
    return requested


@login_required
def serve_protected_media(request, path):
    """Sirve media/ con sesion. Impide salir de MEDIA_ROOT con '..'."""
    if resolve_media_file(path) is None:
        raise Http404("Archivo no encontrado.")
    return serve(request, path, document_root=str(Path(settings.MEDIA_ROOT).resolve()))
