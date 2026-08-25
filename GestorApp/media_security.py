"""Hardening de subidas: tamanos, extensiones, magic bytes y nombres seguros."""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.deconstruct import deconstructible


_MAGIC = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".pdf": (b"%PDF",),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
}

_IMAGE_MIME = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".gif": {"image/gif"},
    ".webp": {"image/webp"},
}
_PDF_MIME = {"application/pdf", "application/x-pdf"}
_PLANTILLA_MIME = {
    ".pdf": _PDF_MIME,
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/octet-stream",
    },
}


def _cfg():
    raw = getattr(settings, "MEDIA_UPLOAD", {}) or {}
    return {
        "image_max_bytes": int(raw.get("image_max_bytes", 5 * 1024 * 1024)),
        "pdf_max_bytes": int(raw.get("pdf_max_bytes", 10 * 1024 * 1024)),
        "plantilla_max_bytes": int(raw.get("plantilla_max_bytes", 15 * 1024 * 1024)),
        "image_extensions": {
            e.lower() if str(e).startswith(".") else f".{str(e).lower()}"
            for e in raw.get("image_extensions", (".jpg", ".jpeg", ".png", ".gif", ".webp"))
        },
        "pdf_extensions": {".pdf"},
        "plantilla_extensions": {
            e.lower() if str(e).startswith(".") else f".{str(e).lower()}"
            for e in raw.get("plantilla_extensions", (".docx", ".xlsx", ".pdf"))
        },
    }


def normalize_extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def safe_basename(filename: str, forced_ext: str | None = None) -> str:
    """Nombre opaco: uuid + extension (sin path traversal ni nombre original)."""
    ext = (forced_ext or normalize_extension(filename) or "").lower()
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    if ext and not all(c.isalnum() or c == "." for c in ext):
        ext = ""
    return f"{uuid.uuid4().hex}{ext}"


def build_safe_media_path(subdir: str, filename: str) -> str:
    subdir = (subdir or "uploads").strip("/\\")
    return f"{subdir}/{safe_basename(filename)}"


def _read_header(uploaded, nbytes=32) -> bytes:
    pos = uploaded.tell() if hasattr(uploaded, "tell") else 0
    try:
        header = uploaded.read(nbytes) or b""
    finally:
        if hasattr(uploaded, "seek"):
            try:
                uploaded.seek(pos)
            except Exception:
                uploaded.seek(0)
    return header


def _matches_magic(ext: str, header: bytes) -> bool:
    if ext == ".webp":
        return (
            len(header) >= 12
            and header[0:4] == b"RIFF"
            and header[8:12] == b"WEBP"
        )
    signatures = _MAGIC.get(ext)
    if not signatures:
        return False
    return any(header.startswith(sig) for sig in signatures)


def _human_size(num_bytes: int) -> str:
    mb = num_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.0f} MB"
    return f"{max(1, num_bytes // 1024)} KB"


def validate_uploaded_file(archivo, *, kind: str):
    """
    Valida un UploadedFile nuevo.
    kind: 'image' | 'pdf' | 'plantilla'
    Si no es upload nuevo (FieldFile existente), lo deja pasar.
    """
    if not archivo:
        return archivo
    if not isinstance(archivo, UploadedFile):
        return archivo

    cfg = _cfg()
    if kind == "image":
        allowed_ext = cfg["image_extensions"]
        max_bytes = cfg["image_max_bytes"]
        label = "La imagen"
    elif kind == "pdf":
        allowed_ext = cfg["pdf_extensions"]
        max_bytes = cfg["pdf_max_bytes"]
        label = "El PDF"
    elif kind == "plantilla":
        allowed_ext = cfg["plantilla_extensions"]
        max_bytes = cfg["plantilla_max_bytes"]
        label = "El archivo"
    else:
        raise ValueError(f"kind no soportado: {kind}")

    size = getattr(archivo, "size", None)
    if size is not None and size > max_bytes:
        raise ValidationError(f"{label} debe pesar menos de {_human_size(max_bytes)}.")

    ext = normalize_extension(getattr(archivo, "name", "") or "")
    if ext not in allowed_ext:
        exts = ", ".join(sorted(allowed_ext))
        raise ValidationError(f"Formato no permitido. Extensiones validas: {exts}.")

    content_type = (getattr(archivo, "content_type", None) or "").split(";")[0].strip().lower()
    if content_type:
        if kind == "image":
            allowed_mime = _IMAGE_MIME.get(ext, set())
        elif kind == "pdf":
            allowed_mime = _PDF_MIME
        else:
            allowed_mime = _PLANTILLA_MIME.get(ext, set())
        if (
            allowed_mime
            and content_type not in allowed_mime
            and content_type != "application/octet-stream"
        ):
            raise ValidationError(
                f"{label} tiene un tipo MIME no permitido ({content_type})."
            )

    header = _read_header(archivo)
    if not header:
        raise ValidationError(f"{label} esta vacio o no se pudo leer.")
    if not _matches_magic(ext, header):
        raise ValidationError(
            f"{label} no coincide con su extension ({ext}). "
            "El contenido real no es un archivo valido."
        )

    archivo.name = safe_basename(archivo.name, forced_ext=ext)
    return archivo


def validate_image_upload(archivo):
    return validate_uploaded_file(archivo, kind="image")


def validate_pdf_upload(archivo):
    return validate_uploaded_file(archivo, kind="pdf")


def validate_plantilla_upload(archivo):
    return validate_uploaded_file(archivo, kind="plantilla")


@deconstructible
class SafeUploadTo:
    """upload_to estable para migraciones: subdir/uuid.ext"""

    def __init__(self, subdir: str):
        self.subdir = subdir

    def __call__(self, instance, filename):
        return build_safe_media_path(self.subdir, filename)

    def __eq__(self, other):
        return isinstance(other, SafeUploadTo) and self.subdir == other.subdir


equipo_imagen_upload_to = SafeUploadTo("equipos")
ticket_imagen_upload_to = SafeUploadTo("support")
ticket_comentario_upload_to = SafeUploadTo("support/comentarios")
plantilla_archivo_upload_to = SafeUploadTo("plantillas_orden_compra")
orden_pdf_upload_to = SafeUploadTo("ordenes_compra")


def validate_ticket_adjunto_upload(archivo):
    """Imagen o PDF para comentarios de ticket."""
    if not archivo:
        return archivo
    if not isinstance(archivo, UploadedFile):
        return archivo
    ext = normalize_extension(getattr(archivo, "name", "") or "")
    cfg = _cfg()
    if ext in cfg["image_extensions"]:
        return validate_uploaded_file(archivo, kind="image")
    if ext in cfg["pdf_extensions"]:
        return validate_uploaded_file(archivo, kind="pdf")
    raise ValidationError(
        "Formato no permitido. Adjunta una imagen (JPG, PNG, GIF, WEBP) o un PDF."
    )
