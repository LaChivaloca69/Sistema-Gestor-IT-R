"""
Extrae ModelForms/Forms de GestorApp/views/*.py y GestorApp/forms.py
hacia el paquete GestorApp/forms/.
"""
from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "GestorApp"
VIEWS = APP / "views"
FORMS_PKG = APP / "forms"
OLD_FORMS = APP / "forms.py"
OLD_GOBIERNO = APP / "gobierno_forms.py"
BACKUP_DIR = APP / "_forms_split_backup"

# view module -> list of top-level names to extract (classes + FormSet assigns)
EXTRACT_FROM_VIEWS = {
    "organizacion.py": ["AreaForm", "PuestoForm", "PersonalForm", "ProveedorForm"],
    "ubicaciones.py": ["EdificioForm", "ZonaEdificioForm", "CategoriaEquipoForm"],
    "equipo.py": ["EquipoForm", "EquipoBajaForm", "EquipoUbicacionForm", "EquipoAsignarForm"],
    "movimiento.py": ["MovimientoEquipoForm"],
    "asignacion.py": ["AsignacionEquipoForm"],
    "mantenimiento.py": ["MantenimientoForm", "AgendaMantenimientoForm"],
    "tickets.py": ["BitacoraForm", "AnswerForm"],
    "compras.py": [
        "PlantillaDocumentoForm",
        "_validar_pdf_upload",
        "_sync_iva_porcentaje",
        "OrdenCompraCrearForm",
        "OrdenCompraSubirForm",
        "DetalleOrdenCompraForm",
        "DetalleOrdenCompraFormSet",
        "DetalleOrdenCompraCapturaForm",
        "DetalleOrdenCompraCapturaFormSet",
    ],
}

# Target forms package module for each view extract
VIEW_TO_FORMS_MODULE = {
    "organizacion.py": "organizacion.py",
    "ubicaciones.py": "ubicaciones.py",
    "equipo.py": "equipo.py",
    "movimiento.py": "movimiento.py",
    "asignacion.py": "asignacion.py",
    "mantenimiento.py": "mantenimiento.py",
    "tickets.py": "tickets.py",
    "compras.py": "compras.py",
}


def get_top_level_spans(source: str) -> dict[str, tuple[int, int]]:
    """name -> (start_line_1based, end_line_1based inclusive) for top-level class/func/assign."""
    tree = ast.parse(source)
    lines = source.splitlines()
    n = len(lines)
    spans: dict[str, tuple[int, int]] = {}

    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", None) or start
            spans[node.name] = (start, end)
        elif isinstance(node, ast.Assign):
            end = getattr(node, "end_lineno", node.lineno)
            for t in node.targets:
                if isinstance(t, ast.Name):
                    spans[t.id] = (node.lineno, end)
    return spans


def slice_names(source: str, names: list[str]) -> tuple[str, str]:
    """Return (extracted_block, remaining_source) preserving order of names."""
    spans = get_top_level_spans(source)
    lines = source.splitlines(keepends=True)
    missing = [n for n in names if n not in spans]
    if missing:
        raise SystemExit(f"Missing names in source: {missing}")

    ranges = [spans[n] for n in names]
    # expand to include preceding blank/comment lines belonging to section headers
    extracted_parts = []
    remove_lines: set[int] = set()  # 0-based

    for start, end in ranges:
        # include up to 3 preceding comment/blank lines if they look like section headers
        s0 = start - 1
        preview = s0
        while preview > 0 and preview >= s0 - 4:
            prev = lines[preview - 1]
            if prev.strip() == "" or prev.lstrip().startswith("#"):
                preview -= 1
            else:
                break
        # don't steal blank that separates from previous kept code aggressively:
        # only take comment lines immediately above
        take_from = start - 1
        i = start - 2
        while i >= 0:
            raw = lines[i]
            if raw.lstrip().startswith("#"):
                take_from = i
                i -= 1
                continue
            if raw.strip() == "" and i + 1 == take_from:
                # one blank before comment block
                take_from = i
                i -= 1
                continue
            break

        chunk = "".join(lines[take_from:end])
        extracted_parts.append(chunk.rstrip() + "\n\n")
        for li in range(take_from, end):
            remove_lines.add(li)

    remaining = "".join(line for i, line in enumerate(lines) if i not in remove_lines)
    # collapse 3+ blank lines
    remaining = re.sub(r"\n{4,}", "\n\n\n", remaining)
    extracted = "".join(extracted_parts)
    return extracted, remaining


COMMON_FORMS_IMPORTS = '''\
from datetime import datetime
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .. import document_engine
from ..cobertura import operativo_user_choices
from ..models import (
    AccionHistorial,
    AgendaMantenimiento,
    Answer,
    Area,
    AsignacionEquipo,
    Bitacora,
    CategoriaEquipo,
    CoberturaTickets,
    DetalleOrdenCompra,
    Edificio,
    Equipo,
    EstadoAsignacion,
    EstadoEquipo,
    EstadoMantenimiento,
    EstadoOrdenCompra,
    EstadoSolicitudEquipo,
    EstadoSupport,
    IvaOpcion,
    Mantenimiento,
    MovimientoEquipo,
    OrdenCompra,
    OrigenAltaEquipo,
    Personal,
    PlantillaDocumento,
    Proveedor,
    Puesto,
    SeguimientoTicket,
    SolicitudEquipo,
    TicketIT,
    TipoPlantillaDocumento,
    TipoProveedor,
    Ubicacion,
    UrgenciaSolicitudEquipo,
    ZonaEdificio,
)
from ..roles import (
    ROLE_ADMIN,
    ROLE_CHOICES,
    ROLE_TECNICO,
    ROLE_USUARIO,
    get_user_role,
    is_admin_user,
    is_operativo,
    operativo_users_queryset,
    set_user_role,
)
'''


HEADERS = {
    "common.py": '"""Helpers compartidos de formularios."""\n',
    "auth.py": '"""Registro de usuario."""\n',
    "tickets.py": '"""Forms de tickets, seguimientos, bitácora y answers."""\n',
    "ubicaciones.py": '"""Forms de ubicaciones físicas y categorías."""\n',
    "organizacion.py": '"""Forms de organización: áreas, puestos, personal, proveedores."""\n',
    "equipo.py": '"""Forms de inventario de equipos."""\n',
    "movimiento.py": '"""Forms de movimientos de equipo."""\n',
    "asignacion.py": '"""Forms de asignaciones."""\n',
    "mantenimiento.py": '"""Forms de mantenimiento y agenda."""\n',
    "compras.py": '"""Forms de plantillas y órdenes de compra."""\n',
    "gobierno.py": '"""Forms de gobierno: coberturas y solicitudes."""\n',
}


def write_module(name: str, body: str, extra_imports: str = "") -> None:
    header = HEADERS[name] + COMMON_FORMS_IMPORTS + extra_imports + "\n"
    (FORMS_PKG / name).write_text(header + body, encoding="utf-8")
    print(f"Wrote forms/{name} ({len(body.splitlines())} body lines)")


def main() -> None:
    if FORMS_PKG.exists():
        raise SystemExit(f"Already exists: {FORMS_PKG}")
    if not OLD_FORMS.exists():
        raise SystemExit(f"Missing {OLD_FORMS}")

    BACKUP_DIR.mkdir(exist_ok=True)
    shutil.copy2(OLD_FORMS, BACKUP_DIR / "forms.py")
    shutil.copy2(OLD_GOBIERNO, BACKUP_DIR / "gobierno_forms.py")
    for vf in EXTRACT_FROM_VIEWS:
        shutil.copy2(VIEWS / vf, BACKUP_DIR / f"views_{vf}")

    FORMS_PKG.mkdir()

    # --- Split old forms.py ---
    old = OLD_FORMS.read_text(encoding="utf-8")
    # Keep helpers + ticket forms etc by AST extraction from old file
    # Extract by name groups
    common_names = [
        "get_subtipo_ticket_choices",
        "get_tipo_equipo_queryset",
        "_get_user_personal",
        "_get_personal_active_assignment",
    ]
    tickets_old = ["TicketITForm", "SeguimientoTicketForm"]
    # Drop unused AnswerForm from old forms.py (views used local AnswerForm)
    ubic_old = ["UbicacionForm"]
    auth_old = ["UserRegisterForm"]

    common_body, rest = slice_names(old, common_names)
    # re-parse rest is hard because slice_names worked on full; do separate extracts from original
    tickets_body, _ = slice_names(old, tickets_old)
    ubic_body, _ = slice_names(old, ubic_old)
    auth_body, _ = slice_names(old, auth_old)

    write_module("common.py", common_body)
    write_module(
        "auth.py",
        auth_body,
        "from .common import _get_user_personal  # noqa: F401\n",
    )
    write_module(
        "tickets.py",
        tickets_body,
        "from .common import (\n"
        "    _get_personal_active_assignment,\n"
        "    _get_user_personal,\n"
        "    get_subtipo_ticket_choices,\n"
        "    get_tipo_equipo_queryset,\n"
        ")\n",
    )
    # AnswerForm + BitacoraForm come from views below — append later
    write_module("ubicaciones.py", ubic_body)

    # --- Extract from view modules ---
    extracted_by_target: dict[str, list[str]] = {v: [] for v in set(VIEW_TO_FORMS_MODULE.values())}

    for view_file, names in EXTRACT_FROM_VIEWS.items():
        path = VIEWS / view_file
        src = path.read_text(encoding="utf-8")
        extracted, remaining = slice_names(src, names)
        target = VIEW_TO_FORMS_MODULE[view_file]
        extracted_by_target[target].append(extracted)

        # Fix remaining view: strip unused forms imports later manually; write remaining
        path.write_text(remaining, encoding="utf-8")
        print(f"Stripped forms from views/{view_file}")

    # Append view-extracted content
    extras = {
        "movimiento.py": "from ..views.helpers import _get_equipo_asignacion_activa\n",
        "tickets.py": "from .common import (\n"
        "    _get_personal_active_assignment,\n"
        "    _get_user_personal,\n"
        "    get_subtipo_ticket_choices,\n"
        "    get_tipo_equipo_queryset,\n"
        ")\n",
        "compras.py": "",
        "organizacion.py": "",
        "equipo.py": "",
        "asignacion.py": "",
        "mantenimiento.py": "",
        "ubicaciones.py": "",
    }

    for target, parts in extracted_by_target.items():
        body = "".join(parts)
        if target == "tickets.py":
            # already wrote TicketIT/Seguimiento; append Bitacora/Answer
            existing = (FORMS_PKG / "tickets.py").read_text(encoding="utf-8")
            # remove trailing and append
            (FORMS_PKG / "tickets.py").write_text(existing.rstrip() + "\n\n" + body, encoding="utf-8")
            print(f"Appended view forms to forms/tickets.py")
        elif target == "ubicaciones.py":
            existing = (FORMS_PKG / "ubicaciones.py").read_text(encoding="utf-8")
            (FORMS_PKG / "ubicaciones.py").write_text(existing.rstrip() + "\n\n" + body, encoding="utf-8")
            print(f"Appended view forms to forms/ubicaciones.py")
        else:
            write_module(target, body, extras.get(target, ""))

    # gobierno
    gob = OLD_GOBIERNO.read_text(encoding="utf-8")
    # strip module docstring and old imports — keep classes only
    gob_spans = get_top_level_spans(gob)
    gob_names = ["CoberturaTicketsForm", "SolicitudEquipoForm", "SolicitudEquipoRevisionForm"]
    gob_body, _ = slice_names(gob, gob_names)
    write_module("gobierno.py", gob_body)

    # __init__.py facade
    (FORMS_PKG / "__init__.py").write_text(
        '''\
"""
Formularios de GestorApp (paquete).

Compatibilidad: `from GestorApp.forms import TicketITForm` sigue funcionando.
"""

from .auth import UserRegisterForm
from .common import (
    get_subtipo_ticket_choices,
    get_tipo_equipo_queryset,
)
from .organizacion import AreaForm, PersonalForm, ProveedorForm, PuestoForm
from .ubicaciones import (
    CategoriaEquipoForm,
    EdificioForm,
    UbicacionForm,
    ZonaEdificioForm,
)
from .equipo import EquipoAsignarForm, EquipoBajaForm, EquipoForm, EquipoUbicacionForm
from .movimiento import MovimientoEquipoForm
from .asignacion import AsignacionEquipoForm
from .mantenimiento import AgendaMantenimientoForm, MantenimientoForm
from .tickets import AnswerForm, BitacoraForm, SeguimientoTicketForm, TicketITForm
from .compras import (
    DetalleOrdenCompraCapturaForm,
    DetalleOrdenCompraCapturaFormSet,
    DetalleOrdenCompraForm,
    DetalleOrdenCompraFormSet,
    OrdenCompraCrearForm,
    OrdenCompraSubirForm,
    PlantillaDocumentoForm,
)
from .gobierno import (
    CoberturaTicketsForm,
    SolicitudEquipoForm,
    SolicitudEquipoRevisionForm,
)

__all__ = [
    "AgendaMantenimientoForm",
    "AnswerForm",
    "AreaForm",
    "AsignacionEquipoForm",
    "BitacoraForm",
    "CategoriaEquipoForm",
    "CoberturaTicketsForm",
    "DetalleOrdenCompraCapturaForm",
    "DetalleOrdenCompraCapturaFormSet",
    "DetalleOrdenCompraForm",
    "DetalleOrdenCompraFormSet",
    "EdificioForm",
    "EquipoAsignarForm",
    "EquipoBajaForm",
    "EquipoForm",
    "EquipoUbicacionForm",
    "MantenimientoForm",
    "MovimientoEquipoForm",
    "OrdenCompraCrearForm",
    "OrdenCompraSubirForm",
    "PersonalForm",
    "PlantillaDocumentoForm",
    "ProveedorForm",
    "PuestoForm",
    "SeguimientoTicketForm",
    "SolicitudEquipoForm",
    "SolicitudEquipoRevisionForm",
    "TicketITForm",
    "UbicacionForm",
    "UserRegisterForm",
    "ZonaEdificioForm",
    "get_subtipo_ticket_choices",
    "get_tipo_equipo_queryset",
]
''',
        encoding="utf-8",
    )

    # Replace old forms.py with note — must DELETE so package takes over
    OLD_FORMS.unlink()
    # Thin compatibility shim for gobierno_forms
    OLD_GOBIERNO.write_text(
        '''\
"""Compatibilidad: reexporta forms de gobierno desde el paquete forms."""

from .forms.gobierno import (  # noqa: F401
    CoberturaTicketsForm,
    SolicitudEquipoForm,
    SolicitudEquipoRevisionForm,
)
''',
        encoding="utf-8",
    )
    print("Removed forms.py; gobierno_forms.py is now a shim")
    print("Done. Next: fix view imports.")


if __name__ == "__main__":
    main()
