"""Home, calendario y signup."""
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
from ..cobertura import (
    coberturas_activas_para_suplente,
    ticket_asignados_q_for_user,
    user_ids_covered_by,
)
from ..forms.auth import UserRegisterForm
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

from .equipo import _equipos_alerta_context
from .mantenimiento import (
    MANTENIMIENTO_ALERTA_DIAS,
    _mantenimientos_alerta_context,
)
from .tickets import SEGUIMIENTO_ALERTA_DIAS, _seguimientos_alerta_context


def _calendar_event(
    title,
    start,
    *,
    color,
    details,
    case_type,
    case_type_label,
    case_label,
    action_url,
    action_text,
    end=None,
    all_day=True,
    urgency="ok",
    urgency_label=None,
    mine=False,
):
    class_names = [f"cal-type-{case_type}"]
    if urgency and urgency != "ok":
        class_names.append(f"cal-urgency-{urgency}")
    if mine:
        class_names.append("cal-mine")

    event = {
        "title": title,
        "start": start.isoformat(),
        "allDay": all_day,
        "backgroundColor": color,
        "borderColor": color,
        "textColor": "#ffffff",
        "classNames": class_names,
        "extendedProps": {
            "details": details,
            "caseType": case_type,
            "caseTypeLabel": case_type_label,
            "caseLabel": case_label,
            "actionUrl": action_url,
            "actionText": action_text,
            "urgency": urgency or "ok",
            "urgencyLabel": urgency_label,
            "mine": bool(mine),
        },
    }
    if end is not None:
        event["end"] = end.isoformat()
    return event


def _ticket_sla_deadline(ticket):
    """Fecha/hora límite SLA según prioridad; None si no aplica."""
    if not ticket or ticket.status == EstadoSupport.CERRADO:
        return None
    horas = SLA_HORAS_POR_PRIORIDAD.get(ticket.prioridad)
    if not horas or not ticket.fecha_support:
        return None
    deadline = ticket.fecha_support + timedelta(hours=horas)
    if timezone.is_naive(deadline):
        deadline = timezone.make_aware(deadline, timezone.get_current_timezone())
    return deadline


def _calendar_user_match_labels(user):
    """Etiquetas (username / nombre) para emparejar tecnico_responsable."""
    labels = set()
    if not user or not getattr(user, "is_authenticated", False):
        return labels
    username = getattr(user, get_user_model().USERNAME_FIELD, None) or getattr(
        user, "username", None
    )
    if username:
        labels.add(str(username).strip().lower())
    try:
        personal = user.personal_profile
    except Exception:
        personal = None
    if personal:
        parts = [personal.nombre, personal.apellido_paterno, personal.apellido_materno]
        full = " ".join(part for part in parts if part).strip().lower()
        if full:
            labels.add(full)
    return labels


def _mantenimiento_is_mine(mantenimiento, user_labels):
    tech = (mantenimiento.tecnico_responsable or "").strip().lower()
    if not tech or tech.startswith("proveedor:"):
        return False
    return tech in user_labels


def _ticket_is_assigned_to_user(ticket, user, covered_ids):
    if not user or not ticket or not ticket.asignado_a_id:
        return False
    return ticket.asignado_a_id == user.id or ticket.asignado_a_id in covered_ids


def _calendar_label(value):
    return value if value else "Sin dato"


def _calendar_short(value, max_len=34):
    """Texto corto para chips del calendario (mes)."""
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _calendar_title(prefix, context, fallback="Sin dato"):
    """Titulo intuitivo: Prefijo · contexto (folio queda en el modal)."""
    body = _calendar_short(context) or _calendar_short(fallback) or "Sin dato"
    return f"{prefix} · {body}"


def _calendar_day(value):
    if not value:
        return timezone.localdate()
    if timezone.is_aware(value):
        return timezone.localtime(value).date()
    if hasattr(value, "date") and not isinstance(value, date):
        return value.date()
    return value


CALENDAR_PAST_DAYS = 30
CALENDAR_FUTURE_DAYS = 90
# Paleta por tipo (chips / eventos). Urgencia no reemplaza el color: solo borde CSS.
CAL_COLOR_TICKET = "#ea580c"
CAL_COLOR_TICKET_PROCESO = "#c2410c"
CAL_COLOR_TICKET_REVISION = "#9a3412"
CAL_COLOR_TICKET_CERRADO = "#78716c"
CAL_COLOR_MANT = "#2563eb"
CAL_COLOR_MANT_DONE = "#1e40af"
CAL_COLOR_MANT_CANCEL = "#b91c1c"
CAL_COLOR_CHECK = "#7c3aed"
CAL_COLOR_CHECK_DONE = "#5b21b6"
CAL_COLOR_CICLO = "#db2777"
CAL_COLOR_MOV_ALTA = "#16a34a"
CAL_COLOR_MOV_BAJA = "#b91c1c"
CAL_COLOR_MOV_ASIGN = "#0d9488"
CAL_COLOR_MOV_CAMBIO_ASIGN = "#0891b2"
CAL_COLOR_MOV_MANT = "#ca8a04"
CAL_COLOR_MOV_UBIC = "#64748b"
# Compat: ya no se usan para rellenar el evento; la urgencia va por classNames + CSS.
CALENDAR_COLOR_VENCIDO = "#dc2626"
CALENDAR_COLOR_POR_VENCER = "#f59e0b"


def _calendar_window(today=None):
    today = today or timezone.localdate()
    return (
        today - timedelta(days=CALENDAR_PAST_DAYS),
        today + timedelta(days=CALENDAR_FUTURE_DAYS),
        today,
    )


def _calendar_urgency_from_date(event_date, today=None, alerta_dias=7, active=True):
    if not active or not event_date:
        return "ok", None
    today = today or timezone.localdate()
    if isinstance(event_date, datetime):
        event_date = _calendar_day(event_date)
    if event_date < today:
        return "vencido", "Vencido"
    if event_date <= today + timedelta(days=alerta_dias):
        return "por_vencer", "Por vencer"
    return "ok", None


def _ticket_calendar_urgency(ticket, now=None):
    if ticket.status == EstadoSupport.CERRADO:
        return "ok", None
    now = now or timezone.now()
    deadline = _ticket_sla_deadline(ticket)
    if not deadline:
        return "ok", None
    if timezone.is_naive(now):
        now = timezone.make_aware(now, timezone.get_current_timezone())
    horas = SLA_HORAS_POR_PRIORIDAD.get(ticket.prioridad) or 0
    if now >= deadline:
        return "vencido", "SLA vencido"
    umbral = min(timedelta(hours=4), timedelta(hours=horas) * 0.25) if horas else timedelta(hours=4)
    if now >= deadline - umbral:
        return "por_vencer", "SLA por vencer"
    return "ok", None


def _calendar_apply_urgency_color(base_color, urgency):
    """Conserva el color de tipo; la urgencia se marca con cal-urgency-* en CSS."""
    return base_color


def _build_home_calendar_events(user=None):
    window_start, window_end, today = _calendar_window()
    now = timezone.now()
    events = []
    staff_user = is_operativo(user)
    covered_ids = set(user_ids_covered_by(user, on_date=today)) if staff_user else set()
    user_labels = _calendar_user_match_labels(user) if staff_user else set()

    # Ampliar lookup de tickets abiertos: el evento operativo cae en la fecha límite SLA.
    max_sla_days = 1
    if SLA_HORAS_POR_PRIORIDAD:
        max_sla_days = max(1, (max(SLA_HORAS_POR_PRIORIDAD.values()) // 24) + 1)
    ticket_lookup_start = window_start - timedelta(days=max_sla_days)

    tickets_qs = (
        TicketIT.objects.select_related("area", "puesto", "solicitado_por", "asignado_a")
        .filter(
            fecha_support__date__gte=ticket_lookup_start,
            fecha_support__date__lte=window_end,
        )
        .order_by("-fecha_support")
    )
    if user is not None and not staff_user:
        tickets_qs = tickets_qs.filter(solicitado_por=user)

    for ticket in tickets_qs:
        sla_deadline = _ticket_sla_deadline(ticket)
        req = ticket.requerimiento
        if ticket.status != EstadoSupport.CERRADO and sla_deadline:
            event_date = _calendar_day(sla_deadline)
            title = _calendar_title("SLA", req, fallback=ticket.folio_ticket)
            case_type_label = "Límite SLA"
        else:
            event_date = _calendar_day(ticket.fecha_support)
            title = _calendar_title("Ticket", req, fallback=ticket.folio_ticket)
            case_type_label = "Ticket de soporte"

        if event_date < window_start or event_date > window_end:
            continue

        urgency, urgency_label = _ticket_calendar_urgency(ticket, now=now)
        base_color = {
            EstadoSupport.CERRADO: CAL_COLOR_TICKET_CERRADO,
            EstadoSupport.EN_PROCESO: CAL_COLOR_TICKET_PROCESO,
            EstadoSupport.EN_REVISION: CAL_COLOR_TICKET_REVISION,
            EstadoSupport.ABIERTO: CAL_COLOR_TICKET,
        }.get(ticket.status, CAL_COLOR_TICKET)
        color = _calendar_apply_urgency_color(base_color, urgency)

        if staff_user:
            mine = _ticket_is_assigned_to_user(ticket, user, covered_ids)
        else:
            mine = True

        details = [
            {"label": "Folio", "value": _calendar_label(ticket.folio_ticket)},
            {"label": "Estado", "value": _calendar_label(ticket.status)},
            {"label": "Prioridad", "value": _calendar_label(ticket.prioridad)},
            {
                "label": "Asignado a",
                "value": _calendar_label(
                    getattr(ticket.asignado_a, "username", None)
                ),
            },
            {"label": "Area", "value": _calendar_label(getattr(ticket.area, "nombre_area", None))},
            {"label": "Puesto", "value": _calendar_label(getattr(ticket.puesto, "nombre_puesto", None))},
            {
                "label": "Solicitado por",
                "value": _calendar_label(getattr(ticket.solicitado_por, "username", None)),
            },
            {"label": "Requerimiento", "value": _calendar_label(ticket.requerimiento)},
            {
                "label": "Fecha de alta",
                "value": _calendar_day(ticket.fecha_support).isoformat()
                if ticket.fecha_support
                else "Sin dato",
            },
        ]
        if sla_deadline:
            details.insert(
                0,
                {
                    "label": "Fecha limite SLA",
                    "value": timezone.localtime(sla_deadline).strftime("%Y-%m-%d %H:%M"),
                },
            )
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        if mine and staff_user and ticket.asignado_a_id in covered_ids:
            details.insert(0, {"label": "Cobertura", "value": "Ticket del tecnico que cubres"})

        events.append(
            _calendar_event(
                title,
                event_date,
                color=color,
                details=details,
                case_type="ticket",
                case_type_label=case_type_label,
                case_label=ticket.folio_ticket,
                action_url=reverse("ticketit_detail", args=[ticket.pk]),
                action_text="Abrir ticket",
                urgency=urgency,
                urgency_label=urgency_label,
                mine=mine,
            )
        )

    if not staff_user:
        events.sort(key=lambda event: event["start"])
        return events

    movimientos_qs = (
        MovimientoEquipo.objects.select_related("equipo", "responsable")
        .filter(
            fecha_movimiento__date__gte=window_start,
            fecha_movimiento__date__lte=window_end,
        )
        .order_by("-fecha_movimiento")
    )
    my_personal_id = None
    try:
        my_personal_id = user.personal_profile.pk
    except Exception:
        my_personal_id = None

    for movimiento in movimientos_qs:
        color = {
            TipoMovimiento.DADA_DE_ALTA: CAL_COLOR_MOV_ALTA,
            TipoMovimiento.DADA_DE_BAJA: CAL_COLOR_MOV_BAJA,
            TipoMovimiento.ASIGNACION: CAL_COLOR_MOV_ASIGN,
            TipoMovimiento.CAMBIO_ASIGNACION: CAL_COLOR_MOV_CAMBIO_ASIGN,
            TipoMovimiento.MANTENIMIENTO: CAL_COLOR_MOV_MANT,
            TipoMovimiento.CAMBIO_UBICACION: CAL_COLOR_MOV_UBIC,
        }.get(movimiento.tipo_movimiento, CAL_COLOR_MOV_ASIGN)
        mine = bool(my_personal_id and movimiento.responsable_id == my_personal_id)
        codigo = getattr(getattr(movimiento, "equipo", None), "codigo_inventario", None)
        events.append(
            _calendar_event(
                _calendar_title(
                    movimiento.tipo_movimiento or "Movimiento",
                    codigo,
                    fallback="equipo",
                ),
                _calendar_day(movimiento.fecha_movimiento),
                color=color,
                details=[
                    {"label": "Tipo", "value": _calendar_label(movimiento.tipo_movimiento)},
                    {
                        "label": "Equipo",
                        "value": _calendar_label(
                            getattr(movimiento.equipo, "codigo_inventario", None)
                        ),
                    },
                    {"label": "Origen", "value": _calendar_label(movimiento.origen)},
                    {"label": "Destino", "value": _calendar_label(movimiento.destino)},
                    {
                        "label": "Responsable",
                        "value": _calendar_label(
                            str(movimiento.responsable) if movimiento.responsable else None
                        ),
                    },
                    {
                        "label": "Observaciones",
                        "value": _calendar_label(movimiento.observaciones),
                    },
                ],
                case_type="movimiento",
                case_type_label="Movimiento de equipo",
                case_label=_calendar_label(movimiento.tipo_movimiento),
                action_url=reverse("movimientoequipo_detail", args=[movimiento.pk]),
                action_text="Ver movimiento",
                urgency="ok",
                mine=mine,
            )
        )

    mantenimientos_qs = (
        Mantenimiento.objects.select_related("equipo", "cierre")
        .filter(
            fecha_programada__gte=window_start,
            fecha_programada__lte=window_end,
        )
        .order_by("-fecha_programada")
    )
    for mantenimiento in mantenimientos_qs:
        base_color = CAL_COLOR_MANT
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.COMPLETADO:
            base_color = CAL_COLOR_MANT_DONE
        elif mantenimiento.estado_mantenimiento == EstadoMantenimiento.CANCELADO:
            base_color = CAL_COLOR_MANT_CANCEL

        activo = mantenimiento.estado_mantenimiento in {
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        }
        urgency, urgency_label = _calendar_urgency_from_date(
            mantenimiento.fecha_programada,
            today=today,
            alerta_dias=MANTENIMIENTO_ALERTA_DIAS,
            active=activo,
        )
        color = _calendar_apply_urgency_color(base_color, urgency)
        mine = _mantenimiento_is_mine(mantenimiento, user_labels)
        codigo = getattr(mantenimiento.equipo, "codigo_inventario", None)
        details = [
            {"label": "Folio", "value": mantenimiento.folio_mantenimiento()},
            {"label": "Estado", "value": _calendar_label(mantenimiento.estado_mantenimiento)},
            {"label": "Tipo", "value": _calendar_label(mantenimiento.tipo_mantenimiento)},
            {
                "label": "Equipo",
                "value": _calendar_label(codigo),
            },
            {"label": "Responsable", "value": _calendar_label(mantenimiento.tecnico_responsable)},
            {"label": "Costo", "value": _calendar_label(mantenimiento.costo_mantenimiento)},
        ]
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        events.append(
            _calendar_event(
                _calendar_title(
                    mantenimiento.tipo_mantenimiento or "Mantenimiento",
                    codigo,
                    fallback=mantenimiento.folio_mantenimiento(),
                ),
                mantenimiento.fecha_programada,
                color=color,
                details=details,
                case_type="mantenimiento",
                case_type_label="Mantenimiento",
                case_label=mantenimiento.folio_mantenimiento(),
                action_url=reverse("mantenimiento_detail", args=[mantenimiento.pk]),
                action_text="Abrir mantenimiento",
                urgency=urgency,
                urgency_label=urgency_label,
                mine=mine,
            )
        )

    ciclos_qs = (
        AgendaMantenimiento.objects.select_related("mantenimiento", "mantenimiento__equipo")
        .filter(
            proxima_fecha_mantenimiento__isnull=False,
            proxima_fecha_mantenimiento__gte=window_start,
            proxima_fecha_mantenimiento__lte=window_end,
        )
        .order_by("-proxima_fecha_mantenimiento")
    )
    for agenda in ciclos_qs:
        urgency, urgency_label = _calendar_urgency_from_date(
            agenda.proxima_fecha_mantenimiento,
            today=today,
            alerta_dias=MANTENIMIENTO_ALERTA_DIAS,
            active=True,
        )
        color = _calendar_apply_urgency_color(CAL_COLOR_CICLO, urgency)
        mine = _mantenimiento_is_mine(agenda.mantenimiento, user_labels)
        codigo = getattr(agenda.mantenimiento.equipo, "codigo_inventario", None)
        folio = agenda.mantenimiento.folio_mantenimiento()
        details = [
            {"label": "Folio", "value": folio},
            {
                "label": "Equipo",
                "value": _calendar_label(codigo),
            },
            {
                "label": "Inicio",
                "value": agenda.fecha_inicio.strftime("%Y-%m-%d %H:%M")
                if agenda.fecha_inicio
                else "Sin inicio",
            },
            {
                "label": "Fin",
                "value": agenda.fecha_fin.strftime("%Y-%m-%d %H:%M")
                if agenda.fecha_fin
                else "Sin fin",
            },
            {"label": "Acciones", "value": _calendar_label(agenda.acciones_realizadas)},
            {"label": "Observaciones", "value": _calendar_label(agenda.observaciones)},
            {
                "label": "Proximo mantenimiento",
                "value": agenda.proxima_fecha_mantenimiento.strftime("%Y-%m-%d"),
            },
        ]
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        events.append(
            _calendar_event(
                _calendar_title("Ciclo", codigo, fallback=folio),
                agenda.proxima_fecha_mantenimiento,
                color=color,
                details=details,
                case_type="ciclo",
                case_type_label="Proximo ciclo",
                case_label=folio,
                action_url=reverse("mantenimiento_detail", args=[agenda.mantenimiento_id]),
                action_text="Abrir mantenimiento",
                urgency=urgency,
                urgency_label=urgency_label,
                mine=mine,
            )
        )

    checks_qs = (
        SeguimientoTicket.objects.select_related("ticket", "ticket__asignado_a", "usuario")
        .filter(
            Q(
                fecha_proximo_seguimiento__gte=window_start,
                fecha_proximo_seguimiento__lte=window_end,
            )
            | Q(
                fecha_proximo_seguimiento__isnull=True,
                fecha_check__date__gte=window_start,
                fecha_check__date__lte=window_end,
            )
        )
        .order_by("-fecha_check")
    )
    for seguimiento in checks_qs:
        # Preferir la fecha operativa del próximo check.
        ticket = seguimiento.ticket
        req = getattr(ticket, "requerimiento", None)
        folio = seguimiento.folio_check or getattr(ticket, "folio_ticket", None)
        if seguimiento.fecha_proximo_seguimiento:
            event_date = seguimiento.fecha_proximo_seguimiento
            case_type_label = "Proximo check"
        else:
            event_date = _calendar_day(seguimiento.fecha_check)
            case_type_label = "Check"
        title = _calendar_title("Check", req, fallback=folio)

        activo = (
            not seguimiento.ya_terminado
            and seguimiento.fecha_proximo_seguimiento is not None
            and getattr(ticket, "status", None) != EstadoSupport.CERRADO
        )
        urgency, urgency_label = _calendar_urgency_from_date(
            seguimiento.fecha_proximo_seguimiento,
            today=today,
            alerta_dias=SEGUIMIENTO_ALERTA_DIAS,
            active=activo,
        )
        base_color = CAL_COLOR_CHECK_DONE if seguimiento.ya_terminado else CAL_COLOR_CHECK
        color = _calendar_apply_urgency_color(base_color, urgency)
        mine = bool(
            (seguimiento.usuario_id and user and seguimiento.usuario_id == user.id)
            or _ticket_is_assigned_to_user(ticket, user, covered_ids)
        )
        details = [
            {"label": "Folio", "value": _calendar_label(folio)},
            {
                "label": "Ticket",
                "value": _calendar_label(getattr(ticket, "folio_ticket", None)),
            },
            {
                "label": "Requerimiento",
                "value": _calendar_label(req),
            },
            {
                "label": "Estado",
                "value": "Terminado" if seguimiento.ya_terminado else "Pendiente",
            },
            {"label": "Avance", "value": _calendar_label(seguimiento.avance_realizado)},
            {"label": "Pendiente", "value": _calendar_label(seguimiento.pendiente)},
            {"label": "Proximo paso", "value": _calendar_label(seguimiento.proximo_paso)},
            {
                "label": "Usuario",
                "value": _calendar_label(
                    str(seguimiento.usuario) if seguimiento.usuario else None
                ),
            },
            {"label": "Observacion", "value": _calendar_label(seguimiento.observacion)},
        ]
        if seguimiento.fecha_proximo_seguimiento:
            details.insert(
                0,
                {
                    "label": "Proximo check",
                    "value": seguimiento.fecha_proximo_seguimiento.strftime("%Y-%m-%d"),
                },
            )
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        events.append(
            _calendar_event(
                title,
                event_date,
                color=color,
                details=details,
                case_type="seguimiento_ticket",
                case_type_label=case_type_label,
                case_label=folio or "Check",
                action_url=reverse("ticketit_detail", args=[seguimiento.ticket_id]),
                action_text="Abrir ticket",
                urgency=urgency,
                urgency_label=urgency_label,
                mine=mine,
            )
        )

    events.sort(key=lambda event: event["start"])
    return events


def home(request):
    from ..metrics_cache import get_or_set_user_metric

    today = timezone.localdate()
    is_staff_user = is_operativo(request.user)

    def _compute_home_kpis():
        tickets_abiertos_qs = _tickets_abiertos_qs(request.user)
        alerta_seguimientos = {}
        alerta_mantenimientos = {}
        alerta_equipos = {}
        if is_staff_user:
            alerta_seguimientos = _seguimientos_alerta_context(today=today)
            alerta_mantenimientos = _mantenimientos_alerta_context(today=today)
            alerta_equipos = _equipos_alerta_context(today=today)

        ticket_ops = _ticket_dashboard_context(request.user)["ticket_dashboard"]
        ordenes_count = _ordenes_for_user(request.user).count()
        seguimientos_atencion = (
            alerta_seguimientos.get("seguimientos_vencidos_count", 0)
            + alerta_seguimientos.get("seguimientos_por_vencer_count", 0)
        )
        mantenimientos_atencion = (
            alerta_mantenimientos.get("mantenimientos_vencidos_count", 0)
            + alerta_mantenimientos.get("mantenimientos_por_vencer_count", 0)
        )
        equipos_atencion = (
            alerta_equipos.get("equipos_sin_ubicacion_count", 0)
            + alerta_equipos.get("equipos_mant_largo_count", 0)
            + alerta_equipos.get("asignaciones_antiguas_count", 0)
        )
        return {
            "ticket_ops": {
                "sla_vencidos": ticket_ops["sla_vencidos"],
                "sin_seguimiento": ticket_ops["sin_seguimiento"],
            },
            "alerta_seguimientos": alerta_seguimientos,
            "alerta_mantenimientos": {
                k: v
                for k, v in alerta_mantenimientos.items()
                if k != "mantenimientos_proximos_lista"
            },
            "upcoming_mantenimientos": list(
                alerta_mantenimientos.get("mantenimientos_proximos_lista", [])
            )[:8],
            "alerta_equipos": alerta_equipos,
            "seguimientos_atencion": seguimientos_atencion,
            "mantenimientos_atencion": mantenimientos_atencion,
            "equipos_atencion": equipos_atencion,
            "dashboard_counts": {
                "tickets": _tickets_for_user(request.user).count(),
                "tickets_abiertos": tickets_abiertos_qs.count(),
                "tickets_sla_vencidos": ticket_ops["sla_vencidos"],
                "tickets_sin_seguimiento": ticket_ops["sin_seguimiento"],
                "equipos_activos": Equipo.objects.filter(activo=True)
                .exclude(estado_equipo=EstadoEquipo.BAJA)
                .count()
                if is_staff_user
                else None,
                "equipos_atencion": equipos_atencion,
                "equipos_sin_ubicacion": alerta_equipos.get("equipos_sin_ubicacion_count", 0),
                "equipos_mant_largo": alerta_equipos.get("equipos_mant_largo_count", 0),
                "asignaciones_antiguas": alerta_equipos.get("asignaciones_antiguas_count", 0),
                "mantenimientos_proximos": alerta_mantenimientos.get(
                    "mantenimientos_proximos_count", 0
                ),
                "mantenimientos_atencion": mantenimientos_atencion,
                "mantenimientos_vencidos": alerta_mantenimientos.get(
                    "mantenimientos_vencidos_count", 0
                ),
                "mantenimientos_por_vencer": alerta_mantenimientos.get(
                    "mantenimientos_por_vencer_count", 0
                ),
                "mantenimientos_ciclos": alerta_mantenimientos.get(
                    "mantenimientos_ciclos_count", 0
                ),
                "seguimientos_atencion": seguimientos_atencion,
                "seguimientos_vencidos": alerta_seguimientos.get(
                    "seguimientos_vencidos_count", 0
                ),
                "seguimientos_por_vencer": alerta_seguimientos.get(
                    "seguimientos_por_vencer_count", 0
                ),
                "ordenes": ordenes_count,
                "historial_hoy": HistorialActividad.objects.filter(
                    fecha__date=today,
                    archivado=False,
                ).count()
                if is_staff_user
                else None,
            },
            "has_attention_alerts": bool(
                ticket_ops["sla_vencidos"]
                or ticket_ops["sin_seguimiento"]
                or seguimientos_atencion
                or mantenimientos_atencion
                or alerta_mantenimientos.get("mantenimientos_ciclos_count", 0)
                or equipos_atencion
            ),
        }

    kpis = get_or_set_user_metric("home_kpis", request.user, _compute_home_kpis)
    tickets_abiertos_qs = _tickets_abiertos_qs(request.user)
    ticket_ops = kpis["ticket_ops"]
    alerta_seguimientos = kpis["alerta_seguimientos"]
    alerta_mantenimientos = kpis["alerta_mantenimientos"]
    alerta_equipos = kpis["alerta_equipos"]

    calendar_events = _build_home_calendar_events(user=request.user)
    calendar_counts = {
        "ticket": 0,
        "mantenimiento": 0,
        "seguimiento_ticket": 0,
        "ciclo": 0,
        "movimiento": 0,
        "vencido": 0,
        "por_vencer": 0,
        "mine": 0,
        "all": 0,
    }
    for event in calendar_events:
        props = event.get("extendedProps") or {}
        case_type = props.get("caseType")
        if case_type in calendar_counts:
            calendar_counts[case_type] += 1
        urgency = props.get("urgency")
        if urgency in {"vencido", "por_vencer"}:
            calendar_counts[urgency] += 1
        calendar_counts["all"] += 1
        if props.get("mine"):
            calendar_counts["mine"] += 1

    coberturas_hoy = 0
    if is_staff_user:
        coberturas_hoy = coberturas_activas_para_suplente(request.user).count()

    context = {
        "calendar_events": calendar_events,
        "calendar_counts": calendar_counts,
        "calendar_past_days": CALENDAR_PAST_DAYS,
        "calendar_future_days": CALENDAR_FUTURE_DAYS,
        "calendar_default_scope": "mine" if is_staff_user else "all",
        "calendar_coberturas_hoy": coberturas_hoy,
        "dashboard_counts": kpis["dashboard_counts"],
        "recent_tickets": tickets_abiertos_qs.select_related(
            "area", "solicitado_por", "tipo_equipo"
        ).order_by("-fecha_support")[:5],
        "has_attention_alerts": kpis["has_attention_alerts"],
        "upcoming_mantenimientos": kpis["upcoming_mantenimientos"],
        "recent_historial": list(
            HistorialActividad.objects.select_related("usuario")
            .filter(archivado=False)
            .order_by("-fecha")[:8]
        ) if is_staff_user else [],
        "is_admin_dashboard": is_staff_user,
        "ticket_dashboard": ticket_ops,
        "today": today,
        **alerta_seguimientos,
        **alerta_mantenimientos,
        **alerta_equipos,
    }
    return render(request, "home.html", context)


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Usuario creado correctamente.")
            return redirect("home")
    else:
        form = UserRegisterForm()

    return render(request, "signup.html", {"form": form})





















































