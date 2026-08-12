"""
One-shot: split GestorApp/views.py into GestorApp/views/ package.
Keeps `from GestorApp import views` working via package __init__.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "GestorApp"
SRC = APP / "views.py"
PKG = APP / "views"
BACKUP = APP / "views.py.pre_split.bak"

DOMAIN_IMPORTS = '''\
from datetime import date, datetime, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum, Max, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import NoReverseMatch, reverse

from .. import document_engine
from .. import historial
from ..cobertura import coberturas_activas_para_suplente, ticket_asignados_q_for_user
from ..forms import (
    SeguimientoTicketForm,
    TicketITForm,
    UserRegisterForm,
    UbicacionForm,
    get_subtipo_ticket_choices,
)
from ..roles import (
    ROLE_ADMIN,
    ROLE_CHOICES,
    ROLE_TECNICO,
    ROLE_USUARIO,
    admin_required,
    get_user_role,
    is_admin_user,
    is_operativo,
    operativo_required,
    set_user_role,
)
from ..models import (
    AccionHistorial,
    AgendaMantenimiento,
    Answer,
    Area,
    AsignacionEquipo,
    Bitacora,
    CategoriaEquipo,
    DetalleOrdenCompra,
    Edificio,
    Equipo,
    EstadoAsignacion,
    EstadoEquipo,
    EstadoMantenimiento,
    EstadoOrdenCompra,
    EstadoSupport,
    HistorialActividad,
    IvaOpcion,
    Mantenimiento,
    ModuloHistorial,
    MovimientoEquipo,
    NivelHistorial,
    OrdenCompra,
    OrigenAltaEquipo,
    OrigenOrdenCompra,
    Personal,
    PlantillaDocumento,
    PrioridadSupport,
    Proveedor,
    Puesto,
    SLA_HORAS_POR_PRIORIDAD,
    SeguimientoTicket,
    TicketIT,
    TipoMoneda,
    TipoMovimiento,
    TipoMantenimiento,
    TipoProveedor,
    TipoTicketSupport,
    TipoPlantillaDocumento,
    Ubicacion,
    ZonaEdificio,
)
from .helpers import (
    _apply_date_filters,
    _cerrar_asignaciones_activas,
    _crear_movimiento,
    _deny_ticket_access,
    _end_of_month,
    _get_equipo_asignacion_activa,
    _get_equipo_responsable,
    _month_bounds,
    _ordenes_for_user,
    _parse_date,
    _quick_range_bounds,
    _reconciliar_estado_equipo,
    _ticket_dashboard_context,
    _ticket_has_seguimientos,
    _tickets_abiertos_qs,
    _tickets_for_user,
    _tickets_sla_por_vencer_q,
    _tickets_sla_vencidos_q,
    user_can_delete_ticket,
    user_can_edit_ticket,
    user_can_manage_orden,
    user_can_manage_ticket_flow,
    user_can_view_ticket,
)
'''

HELPERS_IMPORTS = '''\
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
    SLA_HORAS_POR_PRIORIDAD,
    TicketIT,
)
'''


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1 : end]) + "\n"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing {SRC}")
    if PKG.exists():
        raise SystemExit(f"Package already exists: {PKG}")

    lines = SRC.read_text(encoding="utf-8").splitlines()
    print(f"Read {len(lines)} lines from {SRC}")

    shutil.copy2(SRC, BACKUP)
    print(f"Backup -> {BACKUP}")
    PKG.mkdir()

    (PKG / "helpers.py").write_text(
        HELPERS_IMPORTS + "\n" + slice_lines(lines, 86, 416),
        encoding="utf-8",
    )
    print("Wrote helpers.py")

    modules = [
        ("organizacion.py", 417, 1079, '"""Organización: áreas, puestos, personal, proveedores."""\nimport csv\n'),
        ("ubicaciones.py", 1080, 1298, '"""Ubicaciones físicas y categorías de equipo."""\n'),
        ("equipo.py", 1299, 2365, '"""Inventario de equipos."""\nimport csv\n'),
        ("movimiento.py", 2366, 2748, '"""Movimientos de equipo e historial de actividad."""\nimport csv\n'),
        ("asignacion.py", 2749, 3015, '"""Asignaciones de equipo."""\n'),
        ("mantenimiento.py", 3016, 4003, '"""Mantenimientos y agenda."""\n'),
        ("tickets.py", 4004, 4695, '"""Tickets, seguimientos, bitácora y answers."""\n'),
        ("compras.py", 4696, 5435, '"""Plantillas y órdenes de compra."""\n'),
        ("home.py", 5436, len(lines), '"""Home, calendario y signup."""\n'),
    ]

    for name, start, end, doc in modules:
        extra = ""
        if name == "home.py":
            extra = (
                "\nfrom .equipo import _equipos_alerta_context\n"
                "from .mantenimiento import (\n"
                "    MANTENIMIENTO_ALERTA_DIAS,\n"
                "    _mantenimientos_alerta_context,\n"
                ")\n"
                "from .tickets import _seguimientos_alerta_context\n"
            )
        content = doc + DOMAIN_IMPORTS + extra + "\n" + slice_lines(lines, start, end)
        (PKG / name).write_text(content, encoding="utf-8")
        print(f"Wrote {name} ({start}-{end})")

    (PKG / "__init__.py").write_text(
        '''\
"""
Vistas de GestorApp (paquete).

Compatibilidad: `from GestorApp import views` y `views.area_list` siguen igual.
Los decoradores de rol se reexportan porque urls.py usa `views.admin_required`.
"""

from ..roles import admin_required, operativo_required

from .helpers import *  # noqa: F401,F403
from .organizacion import *  # noqa: F401,F403
from .ubicaciones import *  # noqa: F401,F403
from .equipo import *  # noqa: F401,F403
from .movimiento import *  # noqa: F401,F403
from .asignacion import *  # noqa: F401,F403
from .mantenimiento import *  # noqa: F401,F403
from .tickets import *  # noqa: F401,F403
from .compras import *  # noqa: F401,F403
from .home import *  # noqa: F401,F403
''',
        encoding="utf-8",
    )
    print("Wrote __init__.py")

    SRC.unlink()
    print(f"Removed monolith {SRC.name}")
    print("Done.")


if __name__ == "__main__":
    main()
