"""Mantenimientos y agenda."""
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
from ..forms.mantenimiento import AgendaMantenimientoForm, MantenimientoForm
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


def _estado_equipo_tras_mantenimiento(equipo):
    if not equipo or equipo.estado_equipo == EstadoEquipo.BAJA:
        return EstadoEquipo.BAJA if equipo else None
    if AsignacionEquipo.objects.filter(
        equipo=equipo,
        estado_asignacion=EstadoAsignacion.ACTIVA,
    ).exists():
        return EstadoEquipo.ASIGNADO
    return EstadoEquipo.DISPONIBLE


def _sync_equipo_inicio_mantenimiento(mantenimiento, request=None):
    equipo = mantenimiento.equipo
    if not equipo or equipo.estado_equipo == EstadoEquipo.BAJA:
        raise ValidationError("No se puede iniciar mantenimiento sobre un equipo en Baja.")
    if equipo.estado_equipo == EstadoEquipo.EN_MANTENIMIENTO:
        return equipo
    equipo.estado_equipo = EstadoEquipo.EN_MANTENIMIENTO
    equipo.save(update_fields=["estado_equipo"])
    _crear_movimiento(
        equipo,
        TipoMovimiento.MANTENIMIENTO,
        origen=equipo.ubicacion,
        destino=equipo.ubicacion,
        responsable=_get_equipo_responsable(equipo),
        observaciones=f"Inicio mantenimiento {mantenimiento.folio_mantenimiento()}",
        request=request,
    )
    return equipo


def _sync_equipo_fin_mantenimiento(mantenimiento, request=None):
    equipo = mantenimiento.equipo
    if not equipo or equipo.estado_equipo != EstadoEquipo.EN_MANTENIMIENTO:
        return equipo
    # Si otro mantenimiento sigue En Proceso sobre el mismo equipo, no restaurar.
    otros_activos = (
        Mantenimiento.objects.filter(
            equipo=equipo,
            estado_mantenimiento=EstadoMantenimiento.EN_PROCESO,
        )
        .exclude(pk=mantenimiento.pk)
        .exists()
    )
    if otros_activos:
        return equipo
    nuevo_estado = _estado_equipo_tras_mantenimiento(equipo)
    if nuevo_estado and nuevo_estado != equipo.estado_equipo:
        equipo.estado_equipo = nuevo_estado
        equipo.save(update_fields=["estado_equipo"])
        _crear_movimiento(
            equipo,
            TipoMovimiento.MANTENIMIENTO,
            origen=equipo.ubicacion,
            destino=equipo.ubicacion,
            responsable=_get_equipo_responsable(equipo),
            observaciones=(
                f"Fin mantenimiento {mantenimiento.folio_mantenimiento()} "
                f"→ {nuevo_estado}"
            ),
            request=request,
        )
    return equipo


MANTENIMIENTO_ALERTA_DIAS = 7
MANTENIMIENTO_PROXIMOS_DIAS = 30
MANTENIMIENTO_LIST_PAGE_SIZE = 20


def _mantenimiento_queryset():
    return Mantenimiento.objects.select_related("equipo", "equipo__categoria", "cierre")


def _mantenimientos_activos_qs():
    return _mantenimiento_queryset().filter(
        estado_mantenimiento__in=[
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        ]
    )


def _equipos_con_mantenimiento_activo_ids():
    return (
        Mantenimiento.objects.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ]
        )
        .values_list("equipo_id", flat=True)
        .distinct()
    )


def _proximos_ciclos_mantenimiento_qs(today=None, horizon_days=MANTENIMIENTO_ALERTA_DIAS):
    """Cierres con proxima_fecha pendiente y sin mantenimiento abierto del mismo equipo."""
    today = today or timezone.localdate()
    return (
        AgendaMantenimiento.objects.select_related(
            "mantenimiento",
            "mantenimiento__equipo",
        )
        .filter(
            proxima_fecha_mantenimiento__isnull=False,
            mantenimiento__estado_mantenimiento=EstadoMantenimiento.COMPLETADO,
            proxima_fecha_mantenimiento__lte=today + timedelta(days=horizon_days),
        )
        .exclude(mantenimiento__equipo_id__in=_equipos_con_mantenimiento_activo_ids())
        .order_by("proxima_fecha_mantenimiento", "pk")
    )


def _mantenimientos_alerta_context(
    today=None,
    horizon_days=MANTENIMIENTO_ALERTA_DIAS,
    proximos_days=MANTENIMIENTO_PROXIMOS_DIAS,
):
    today = today or timezone.localdate()
    activos = _mantenimientos_activos_qs()
    vencidos_qs = activos.filter(fecha_programada__lt=today).order_by(
        "fecha_programada", "pk"
    )
    por_vencer_qs = activos.filter(
        fecha_programada__gte=today,
        fecha_programada__lte=today + timedelta(days=horizon_days),
    ).order_by("fecha_programada", "pk")
    proximos_30_qs = activos.filter(
        fecha_programada__gte=today,
        fecha_programada__lte=today + timedelta(days=proximos_days),
    ).order_by("fecha_programada", "pk")
    ciclos_qs = _proximos_ciclos_mantenimiento_qs(today=today, horizon_days=horizon_days)
    ciclos_vencidos_qs = ciclos_qs.filter(proxima_fecha_mantenimiento__lt=today)
    ciclos_por_vencer_qs = ciclos_qs.filter(proxima_fecha_mantenimiento__gte=today)
    return {
        "mantenimientos_vencidos": list(vencidos_qs[:8]),
        "mantenimientos_por_vencer": list(por_vencer_qs[:8]),
        "mantenimientos_proximos_lista": list(proximos_30_qs[:6]),
        "mantenimientos_ciclos": list(ciclos_qs[:8]),
        "mantenimientos_vencidos_count": vencidos_qs.count(),
        "mantenimientos_por_vencer_count": por_vencer_qs.count(),
        "mantenimientos_proximos_count": proximos_30_qs.count(),
        "mantenimientos_ciclos_count": ciclos_qs.count(),
        "mantenimientos_ciclos_vencidos_count": ciclos_vencidos_qs.count(),
        "mantenimientos_ciclos_por_vencer_count": ciclos_por_vencer_qs.count(),
        "mantenimientos_alerta_dias": horizon_days,
        "mantenimientos_proximos_dias": proximos_days,
    }


def _parse_date_param(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _crear_proximo_mantenimiento_desde_cierre(agenda, crear=True):
    """
    Si el cierre trae proxima_fecha y crear=True, programa el siguiente ciclo
    (Programado) salvo que el equipo ya tenga uno abierto.
    """
    if not crear:
        return None, "omitido"
    proxima = agenda.proxima_fecha_mantenimiento
    if not proxima:
        return None, "sin_fecha"

    origen = agenda.mantenimiento
    equipo = origen.equipo
    abiertos = Mantenimiento.objects.filter(
        equipo=equipo,
        estado_mantenimiento__in=[
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        ],
    )
    if abiertos.exists():
        return abiertos.order_by("fecha_programada").first(), "ya_abierto"

    existente = Mantenimiento.objects.filter(
        equipo=equipo,
        fecha_programada=proxima,
        estado_mantenimiento=EstadoMantenimiento.PROGRAMADO,
    ).first()
    if existente:
        return existente, "ya_programado"

    tipo = origen.tipo_mantenimiento or TipoMantenimiento.PREVENTIVO
    if tipo == TipoMantenimiento.CORRECTIVO:
        tipo = TipoMantenimiento.PREVENTIVO

    nuevo = Mantenimiento.objects.create(
        equipo=equipo,
        tipo_mantenimiento=tipo,
        estado_mantenimiento=EstadoMantenimiento.PROGRAMADO,
        fecha_programada=proxima,
        tecnico_responsable=origen.tecnico_responsable,
        costo_mantenimiento=0,
        descripcion_falla=(
            f"Ciclo automatico tras {origen.folio_mantenimiento()}."
        ),
    )
    return nuevo, "creado"


def _mantenimiento_dashboard_context(today=None):
    today = today or timezone.localdate()
    alerta = _mantenimientos_alerta_context(today=today)
    qs = _mantenimiento_queryset()
    activos = _mantenimientos_activos_qs()

    por_estado = []
    for value, label in EstadoMantenimiento.choices:
        por_estado.append(
            {
                "value": value,
                "label": label,
                "count": qs.filter(estado_mantenimiento=value).count(),
            }
        )

    por_tipo = []
    for value, label in TipoMantenimiento.choices:
        por_tipo.append(
            {
                "value": value,
                "label": label,
                "count": activos.filter(tipo_mantenimiento=value).count(),
                "total": qs.filter(tipo_mantenimiento=value).count(),
            }
        )

    costo_completados = (
        qs.filter(estado_mantenimiento=EstadoMantenimiento.COMPLETADO).aggregate(
            total=Sum("costo_mantenimiento")
        )["total"]
        or 0
    )
    costo_activos = activos.aggregate(total=Sum("costo_mantenimiento"))["total"] or 0

    por_equipo = list(
        qs.values(
            "equipo_id",
            "equipo__codigo_inventario",
        )
        .annotate(total=Count("id"))
        .order_by("-total", "equipo__codigo_inventario")[:8]
    )

    return {
        "mantenimiento_dashboard": {
            "total": qs.count(),
            "activos": activos.count(),
            "completados": qs.filter(
                estado_mantenimiento=EstadoMantenimiento.COMPLETADO
            ).count(),
            "cancelados": qs.filter(
                estado_mantenimiento=EstadoMantenimiento.CANCELADO
            ).count(),
            "vencidos": alerta["mantenimientos_vencidos_count"],
            "por_vencer": alerta["mantenimientos_por_vencer_count"],
            "proximos_30": alerta["mantenimientos_proximos_count"],
            "ciclos": alerta["mantenimientos_ciclos_count"],
            "costo_completados": costo_completados,
            "costo_activos": costo_activos,
            "por_estado": por_estado,
            "por_tipo": por_tipo,
            "por_equipo": por_equipo,
            "lista_vencidos": alerta["mantenimientos_vencidos"],
            "lista_por_vencer": alerta["mantenimientos_por_vencer"],
            "lista_ciclos": alerta["mantenimientos_ciclos"],
            "alerta_dias": alerta["mantenimientos_alerta_dias"],
            "proximos_dias": alerta["mantenimientos_proximos_dias"],
        }
    }


def mantenimiento_dashboard(request):
    return render(
        request,
        "mantenimiento/dashboard.html",
        {
            "today": timezone.localdate(),
            **_mantenimiento_dashboard_context(),
        },
    )


def mantenimiento_list(request):
    items = _mantenimiento_queryset()
    search_query = (request.GET.get("q") or "").strip()
    selected_alerta = (request.GET.get("alerta") or "").strip()
    selected_estado = (request.GET.get("estado") or "").strip()
    selected_tipo = (request.GET.get("tipo") or "").strip()
    selected_equipo = (request.GET.get("equipo") or "").strip()
    selected_tecnico = (request.GET.get("tecnico") or "").strip()
    selected_orden = (request.GET.get("orden") or "programada").strip()
    fecha_desde = _parse_date_param(request.GET.get("fecha_desde"))
    fecha_hasta = _parse_date_param(request.GET.get("fecha_hasta"))
    today = timezone.localdate()
    horizon = today + timedelta(days=MANTENIMIENTO_ALERTA_DIAS)

    if search_query:
        folio_q = Q(
            equipo__codigo_inventario__icontains=search_query
        ) | Q(
            equipo__numero_serie__icontains=search_query
        ) | Q(
            equipo__marca__icontains=search_query
        ) | Q(
            equipo__modelo__icontains=search_query
        ) | Q(
            tecnico_responsable__icontains=search_query
        ) | Q(
            descripcion_falla__icontains=search_query
        ) | Q(
            tipo_mantenimiento__icontains=search_query
        )
        digits = "".join(ch for ch in search_query if ch.isdigit())
        if digits.isdigit():
            folio_q |= Q(pk=int(digits))
        items = items.filter(folio_q)

    if selected_estado:
        items = items.filter(estado_mantenimiento=selected_estado)
    if selected_tipo:
        items = items.filter(tipo_mantenimiento=selected_tipo)
    if selected_equipo.isdigit():
        items = items.filter(equipo_id=int(selected_equipo))
    if selected_tecnico:
        items = items.filter(tecnico_responsable=selected_tecnico)
    if fecha_desde:
        items = items.filter(fecha_programada__gte=fecha_desde)
    if fecha_hasta:
        items = items.filter(fecha_programada__lte=fecha_hasta)

    if selected_alerta == "vencidos":
        items = items.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            fecha_programada__lt=today,
        )
    elif selected_alerta == "proximos":
        items = items.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            fecha_programada__gte=today,
            fecha_programada__lte=horizon,
        )
    elif selected_alerta == "atencion":
        items = items.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            fecha_programada__lte=horizon,
        )
    elif selected_alerta == "ciclo":
        ciclos = _proximos_ciclos_mantenimiento_qs(today=today)
        items = items.filter(pk__in=ciclos.values_list("mantenimiento_id", flat=True))

    order_map = {
        "programada": ("fecha_programada", "pk"),
        "programada_desc": ("-fecha_programada", "-pk"),
        "reciente": ("-pk",),
        "estado": ("estado_mantenimiento", "fecha_programada", "pk"),
        "equipo": ("equipo__codigo_inventario", "fecha_programada", "pk"),
    }
    if selected_alerta in {"vencidos", "proximos", "atencion"}:
        items = items.order_by("fecha_programada", "pk")
    elif selected_alerta == "ciclo":
        items = items.order_by("cierre__proxima_fecha_mantenimiento", "pk")
    else:
        items = items.order_by(*order_map.get(selected_orden, order_map["programada"]))

    paginator = Paginator(items, MANTENIMIENTO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    tecnicos = (
        Mantenimiento.objects.exclude(tecnico_responsable__isnull=True)
        .exclude(tecnico_responsable="")
        .values_list("tecnico_responsable", flat=True)
        .distinct()
        .order_by("tecnico_responsable")
    )
    equipos = (
        Equipo.objects.filter(mantenimientos__isnull=False)
        .distinct()
        .order_by("codigo_inventario")
    )

    return render(
        request,
        "mantenimiento/list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "selected_alerta": selected_alerta,
            "selected_estado": selected_estado,
            "selected_tipo": selected_tipo,
            "selected_equipo": selected_equipo,
            "selected_tecnico": selected_tecnico,
            "selected_orden": selected_orden,
            "fecha_desde": fecha_desde.isoformat() if fecha_desde else "",
            "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else "",
            "estado_choices": EstadoMantenimiento.choices,
            "tipo_choices": TipoMantenimiento.choices,
            "equipo_choices": equipos,
            "tecnico_choices": tecnicos,
            "mantenimientos_alerta_dias": MANTENIMIENTO_ALERTA_DIAS,
            "today": today,
            "alerta_hasta": horizon,
        },
    )


def mantenimiento_detail(request, pk):
    mantenimiento = get_object_or_404(_mantenimiento_queryset(), pk=pk)
    cierre = getattr(mantenimiento, "cierre", None)
    return render(
        request,
        "mantenimiento/detail.html",
        {
            "object": mantenimiento,
            "cierre": cierre,
        },
    )


def mantenimiento_create(request):
    if request.method == "POST":
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            mantenimiento = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Mantenimiento programado: {mantenimiento.folio_mantenimiento()}",
                objeto=mantenimiento,
                entidad_relacionada=mantenimiento.equipo,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=mantenimiento.pk,
            )
            messages.success(request, "Mantenimiento creado correctamente.")
            return redirect("mantenimiento_detail", pk=mantenimiento.pk)
    else:
        initial = {}
        equipo_id = request.GET.get("equipo")
        fecha = request.GET.get("fecha")
        if equipo_id:
            initial["equipo"] = equipo_id
        if fecha:
            initial["fecha_programada"] = fecha
        form = MantenimientoForm(initial=initial)
    return render(request, "mantenimiento/form.html", {"form": form})


def mantenimiento_update(request, pk):
    mantenimiento = get_object_or_404(_mantenimiento_queryset(), pk=pk)
    if request.method == "POST":
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        if form.is_valid():
            mantenimiento = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Mantenimiento actualizado: {mantenimiento.folio_mantenimiento()}",
                objeto=mantenimiento,
                form=form,
                entidad_relacionada=mantenimiento.equipo,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=mantenimiento.pk,
            )
            messages.success(request, "Mantenimiento actualizado correctamente.")
            return redirect("mantenimiento_detail", pk=mantenimiento.pk)
    else:
        form = MantenimientoForm(instance=mantenimiento)
    return render(
        request,
        "mantenimiento/form.html",
        {"form": form, "object": mantenimiento},
    )


def mantenimiento_delete(request, pk):
    mantenimiento = get_object_or_404(_mantenimiento_queryset(), pk=pk)
    if request.method == "POST":
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.EN_PROCESO:
            try:
                _sync_equipo_fin_mantenimiento(mantenimiento, request=request)
            except ValidationError:
                pass
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.MANTENIMIENTO,
            titulo=f"Mantenimiento eliminado: {mantenimiento.folio_mantenimiento()}",
            objeto=mantenimiento,
        )
        mantenimiento.delete()
        messages.success(request, "Mantenimiento eliminado correctamente.")
        return redirect("mantenimiento_list")
    return render(request, "mantenimiento/confirm_delete.html", {"object": mantenimiento})


def mantenimiento_iniciar(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method != "POST":
        return redirect("mantenimiento_detail", pk=pk)
    try:
        mantenimiento.iniciar()
        _sync_equipo_inicio_mantenimiento(mantenimiento, request=request)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("mantenimiento_detail", pk=pk)

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MANTENIMIENTO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Mantenimiento iniciado: {mantenimiento.folio_mantenimiento()}",
        objeto=mantenimiento,
        entidad_relacionada=mantenimiento.equipo,
        enlace_nombre="mantenimiento_detail",
        metadata={"estado": mantenimiento.estado_mantenimiento},
    )
    messages.success(request, f"{mantenimiento.folio_mantenimiento()} en proceso.")
    return redirect("mantenimiento_detail", pk=pk)


def mantenimiento_cancelar(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method != "POST":
        return redirect("mantenimiento_detail", pk=pk)
    try:
        estaba_en_proceso = (
            mantenimiento.estado_mantenimiento == EstadoMantenimiento.EN_PROCESO
        )
        mantenimiento.cancelar()
        if estaba_en_proceso:
            _sync_equipo_fin_mantenimiento(mantenimiento, request=request)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("mantenimiento_detail", pk=pk)

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MANTENIMIENTO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Mantenimiento cancelado: {mantenimiento.folio_mantenimiento()}",
        objeto=mantenimiento,
        entidad_relacionada=mantenimiento.equipo,
        enlace_nombre="mantenimiento_detail",
        metadata={"estado": mantenimiento.estado_mantenimiento},
    )
    messages.success(request, f"{mantenimiento.folio_mantenimiento()} cancelado.")
    return redirect("mantenimiento_detail", pk=pk)


def mantenimiento_reabrir(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method != "POST":
        return redirect("mantenimiento_detail", pk=pk)
    try:
        estado_anterior = mantenimiento.estado_mantenimiento
        mantenimiento.reabrir()
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.EN_PROCESO:
            _sync_equipo_inicio_mantenimiento(mantenimiento, request=request)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("mantenimiento_detail", pk=pk)

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MANTENIMIENTO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Mantenimiento reabierto: {mantenimiento.folio_mantenimiento()}",
        objeto=mantenimiento,
        entidad_relacionada=mantenimiento.equipo,
        enlace_nombre="mantenimiento_detail",
        metadata={
            "estado_anterior": estado_anterior,
            "estado": mantenimiento.estado_mantenimiento,
        },
    )
    messages.success(
        request,
        f"{mantenimiento.folio_mantenimiento()} reabierto ({mantenimiento.estado_mantenimiento}).",
    )
    return redirect("mantenimiento_detail", pk=pk)


def _mensaje_proximo_ciclo(request, resultado, motivo):
    if motivo == "creado" and resultado is not None:
        messages.success(
            request,
            f"Proximo ciclo programado: {resultado.folio_mantenimiento()} "
            f"({resultado.fecha_programada}).",
        )
        historial.registrar_creacion(
            request,
            modulo=ModuloHistorial.MANTENIMIENTO,
            titulo=f"Proximo ciclo programado: {resultado.folio_mantenimiento()}",
            objeto=resultado,
            entidad_relacionada=resultado.equipo,
            enlace_nombre="mantenimiento_detail",
            enlace_pk=resultado.pk,
        )
    elif motivo == "ya_abierto" and resultado is not None:
        messages.info(
            request,
            f"No se creo otro ciclo: el equipo ya tiene "
            f"{resultado.folio_mantenimiento()} abierto.",
        )
    elif motivo == "ya_programado" and resultado is not None:
        messages.info(
            request,
            f"Ya existia el ciclo {resultado.folio_mantenimiento()} "
            f"para esa fecha.",
        )


def agendamantenimiento_list(request):
    items = AgendaMantenimiento.objects.select_related(
        "mantenimiento", "mantenimiento__equipo"
    )
    search_query = (request.GET.get("q") or "").strip()
    if search_query:
        q = (
            Q(mantenimiento__equipo__codigo_inventario__icontains=search_query)
            | Q(mantenimiento__equipo__marca__icontains=search_query)
            | Q(mantenimiento__equipo__modelo__icontains=search_query)
            | Q(acciones_realizadas__icontains=search_query)
            | Q(observaciones__icontains=search_query)
            | Q(mantenimiento__tecnico_responsable__icontains=search_query)
        )
        digits = "".join(ch for ch in search_query if ch.isdigit())
        if digits.isdigit():
            q |= Q(mantenimiento_id=int(digits)) | Q(pk=int(digits))
        items = items.filter(q)

    items = items.order_by("-fecha_fin", "-pk")
    paginator = Paginator(items, MANTENIMIENTO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "agendamantenimiento/list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
        },
    )


def agendamantenimiento_create(request):
    mantenimiento_id = request.GET.get("mantenimiento")
    fixed = None
    if mantenimiento_id:
        fixed = get_object_or_404(Mantenimiento, pk=mantenimiento_id)
        if not fixed.puede_completar:
            messages.error(request, "Ese mantenimiento no se puede cerrar en su estado actual.")
            return redirect("mantenimiento_detail", pk=fixed.pk)

    if request.method == "POST":
        form = AgendaMantenimientoForm(request.POST, mantenimiento=fixed)
        if form.is_valid():
            agenda = form.save()
            _sync_equipo_fin_mantenimiento(agenda.mantenimiento, request=request)
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Cierre de {agenda.mantenimiento.folio_mantenimiento()}",
                objeto=agenda,
                entidad_relacionada=agenda.mantenimiento,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=agenda.mantenimiento_id,
            )
            proximo, motivo = _crear_proximo_mantenimiento_desde_cierre(
                agenda,
                crear=form.cleaned_data.get("crear_proximo_ciclo", False),
            )
            messages.success(request, "Mantenimiento cerrado correctamente.")
            _mensaje_proximo_ciclo(request, proximo, motivo)
            if motivo == "creado" and proximo is not None:
                return redirect("mantenimiento_detail", pk=proximo.pk)
            return redirect("mantenimiento_detail", pk=agenda.mantenimiento_id)
    else:
        form = AgendaMantenimientoForm(mantenimiento=fixed)
    return render(
        request,
        "agendamantenimiento/form.html",
        {"form": form, "mantenimiento": fixed},
    )


def agendamantenimiento_update(request, pk):
    agenda = get_object_or_404(
        AgendaMantenimiento.objects.select_related("mantenimiento", "mantenimiento__equipo"),
        pk=pk,
    )
    if request.method == "POST":
        form = AgendaMantenimientoForm(request.POST, instance=agenda)
        if form.is_valid():
            agenda = form.save()
            _sync_equipo_fin_mantenimiento(agenda.mantenimiento, request=request)
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Cierre actualizado: {agenda.mantenimiento.folio_mantenimiento()}",
                objeto=agenda,
                form=form,
                entidad_relacionada=agenda.mantenimiento,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=agenda.mantenimiento_id,
            )
            proximo, motivo = _crear_proximo_mantenimiento_desde_cierre(
                agenda,
                crear=form.cleaned_data.get("crear_proximo_ciclo", False),
            )
            messages.success(request, "Cierre actualizado correctamente.")
            _mensaje_proximo_ciclo(request, proximo, motivo)
            if motivo == "creado" and proximo is not None:
                return redirect("mantenimiento_detail", pk=proximo.pk)
            return redirect("mantenimiento_detail", pk=agenda.mantenimiento_id)
    else:
        form = AgendaMantenimientoForm(instance=agenda)
    return render(
        request,
        "agendamantenimiento/form.html",
        {"form": form, "object": agenda, "mantenimiento": agenda.mantenimiento},
    )


def agendamantenimiento_delete(request, pk):
    agenda = get_object_or_404(AgendaMantenimiento, pk=pk)
    mantenimiento = agenda.mantenimiento
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.MANTENIMIENTO,
            titulo=f"Cierre eliminado: {mantenimiento.folio_mantenimiento()}",
            objeto=agenda,
            entidad_relacionada=mantenimiento,
        )
        agenda.delete()
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.COMPLETADO:
            mantenimiento.estado_mantenimiento = EstadoMantenimiento.EN_PROCESO
            mantenimiento.save(update_fields=["estado_mantenimiento"])
            try:
                _sync_equipo_inicio_mantenimiento(mantenimiento, request=request)
            except ValidationError:
                pass
        messages.success(request, "Cierre eliminado correctamente.")
        return redirect("mantenimiento_detail", pk=mantenimiento.pk)
    return render(request, "agendamantenimiento/confirm_delete.html", {"object": agenda})


# ============ TicketIT views ==============
# Formulario de ticket

