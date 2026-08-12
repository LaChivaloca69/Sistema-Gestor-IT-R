"""Movimientos de equipo e historial de actividad."""
import csv
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
from ..forms.movimiento import MovimientoEquipoForm
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

MOVIMIENTO_LIST_PAGE_SIZE = 25
HISTORIAL_LIST_PAGE_SIZE = 40


def _movimiento_queryset():
    return MovimientoEquipo.objects.select_related(
        "equipo",
        "equipo__categoria",
        "responsable",
    )


def _filtrar_movimientos(request):
    items = _movimiento_queryset().order_by("-fecha_movimiento", "-pk")
    search_query = (request.GET.get("q") or "").strip()
    selected_tipo = request.GET.get("tipo_movimiento", "")
    selected_equipo = request.GET.get("equipo", "")
    fecha_desde_raw = request.GET.get("fecha_desde", "")
    fecha_hasta_raw = request.GET.get("fecha_hasta", "")

    if search_query:
        items = items.filter(
            Q(equipo__codigo_inventario__icontains=search_query)
            | Q(origen__icontains=search_query)
            | Q(destino__icontains=search_query)
            | Q(observaciones__icontains=search_query)
            | Q(responsable__nombre__icontains=search_query)
            | Q(responsable__apellido_paterno__icontains=search_query)
        )
    if selected_tipo:
        items = items.filter(tipo_movimiento=selected_tipo)
    if selected_equipo:
        items = items.filter(equipo_id=selected_equipo)

    fecha_desde = _parse_date(fecha_desde_raw)
    fecha_hasta = _parse_date(fecha_hasta_raw)
    items = _apply_date_filters(items, "fecha_movimiento", fecha_desde, fecha_hasta)

    filters = {
        "search_query": search_query,
        "selected_tipo": selected_tipo,
        "selected_equipo": selected_equipo,
        "fecha_desde": fecha_desde_raw,
        "fecha_hasta": fecha_hasta_raw,
    }
    return items, filters


def _export_movimientos_csv(queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="movimientos_equipo.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Fecha",
            "Equipo",
            "Tipo",
            "Origen",
            "Destino",
            "Responsable",
            "Observaciones",
        ]
    )
    for item in queryset:
        writer.writerow(
            [
                timezone.localtime(item.fecha_movimiento).strftime("%Y-%m-%d %H:%M")
                if item.fecha_movimiento
                else "",
                str(item.equipo) if item.equipo_id else "",
                item.tipo_movimiento,
                item.origen or "",
                item.destino or "",
                str(item.responsable) if item.responsable_id else "",
                item.observaciones or "",
            ]
        )
    return response


def movimientoequipo_list(request):
    """Auditoria / historial general de actividad (filtrable)."""
    items = HistorialActividad.objects.select_related("usuario").order_by("-fecha", "-pk")
    selected_modulo = request.GET.get("modulo", "")
    selected_accion = request.GET.get("accion", "")
    selected_nivel = request.GET.get("nivel", "")
    selected_origen = request.GET.get("origen", "")  # automatico | manual | ""
    selected_estado = request.GET.get("estado", "activo")  # activo | archivado | todos
    selected_usuario = (request.GET.get("usuario") or "").strip()
    busqueda = (request.GET.get("q") or "").strip()
    fecha_desde = _parse_date(request.GET.get("fecha_desde"))
    fecha_hasta = _parse_date(request.GET.get("fecha_hasta"))

    if selected_estado == "activo" or selected_estado == "":
        items = items.filter(archivado=False)
    elif selected_estado == "archivado":
        items = items.filter(archivado=True)
    # "todos" no filtra por archivado

    if selected_modulo:
        items = items.filter(modulo=selected_modulo)
    if selected_accion:
        items = items.filter(accion=selected_accion)
    if selected_nivel:
        items = items.filter(nivel=selected_nivel)
    if selected_origen == "automatico":
        items = items.filter(es_automatico=True)
    elif selected_origen == "manual":
        items = items.filter(es_automatico=False)
    if selected_usuario == "sistema":
        items = items.filter(usuario__isnull=True)
    elif selected_usuario.isdigit():
        items = items.filter(usuario_id=int(selected_usuario))
    if busqueda:
        items = items.filter(
            Q(titulo__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(objeto_etiqueta__icontains=busqueda)
            | Q(entidad_relacionada_etiqueta__icontains=busqueda)
            | Q(usuario__username__icontains=busqueda)
            | Q(usuario__first_name__icontains=busqueda)
            | Q(usuario__last_name__icontains=busqueda)
        )
    items = _apply_date_filters(items, "fecha", fecha_desde, fecha_hasta)

    paginator = Paginator(items, HISTORIAL_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    User = get_user_model()
    usuario_choices = (
        User.objects.filter(historial_actividades__isnull=False)
        .distinct()
        .order_by("username")
        .values_list("id", "username", "first_name", "last_name")
    )

    context = {
        "items": page_obj,
        "page_obj": page_obj,
        "result_count": paginator.count,
        "modulo_choices": ModuloHistorial.choices,
        "accion_choices": historial.AccionHistorial.choices,
        "nivel_choices": NivelHistorial.choices,
        "usuario_choices": usuario_choices,
        "selected_modulo": selected_modulo,
        "selected_accion": selected_accion,
        "selected_nivel": selected_nivel,
        "selected_origen": selected_origen,
        "selected_estado": selected_estado or "activo",
        "selected_usuario": selected_usuario,
        "busqueda": busqueda,
        "fecha_desde": request.GET.get("fecha_desde", ""),
        "fecha_hasta": request.GET.get("fecha_hasta", ""),
    }
    return render(request, "movimientoequipo/list.html", context)


def historial_actividad_detail(request, pk):
    """Detalle de un evento de auditoria / historial."""
    obj = get_object_or_404(
        HistorialActividad.objects.select_related("usuario"),
        pk=pk,
    )
    enlace_url = None
    if obj.enlace_nombre and obj.enlace_pk:
        try:
            enlace_url = reverse(obj.enlace_nombre, args=[obj.enlace_pk])
        except NoReverseMatch:
            enlace_url = None
    return render(
        request,
        "historial/auditoria_detail.html",
        {
            "object": obj,
            "enlace_url": enlace_url,
        },
    )


def movimientoequipo_registros(request):
    items, filters = _filtrar_movimientos(request)
    if (request.GET.get("export") or "").lower() == "csv":
        return _export_movimientos_csv(items)

    paginator = Paginator(items, MOVIMIENTO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "items": page_obj,
        "page_obj": page_obj,
        "tipo_choices": TipoMovimiento.choices,
        "equipo_choices": Equipo.objects.order_by("codigo_inventario").values_list(
            "id", "codigo_inventario"
        ),
        **filters,
    }
    return render(request, "movimientoequipo/registros.html", context)


def movimientoequipo_detail(request, pk):
    movimiento = get_object_or_404(_movimiento_queryset(), pk=pk)
    return render(
        request,
        "movimientoequipo/detail.html",
        {
            "object": movimiento,
            "equipo": movimiento.equipo,
        },
    )


def movimientoequipo_equipo_info(request):
    equipo_id = request.GET.get("equipo_id")
    data = {
        "ubicacion_id": "",
        "ubicacion_label": "",
        "responsable_id": "",
        "responsable_label": "",
    }
    if equipo_id:
        try:
            equipo = Equipo.objects.select_related("ubicacion").get(pk=equipo_id)
        except (Equipo.DoesNotExist, ValueError, TypeError):
            equipo = None

        if equipo and equipo.ubicacion_id:
            data["ubicacion_id"] = str(equipo.ubicacion_id)
            data["ubicacion_label"] = str(equipo.ubicacion)

        asignacion = _get_equipo_asignacion_activa(equipo)
        if asignacion and asignacion.personal_id:
            data["responsable_id"] = str(asignacion.personal_id)
            data["responsable_label"] = str(asignacion.personal)

    return JsonResponse(data)


def movimientoequipo_create(request):
    if request.method == "POST":
        form = MovimientoEquipoForm(request.POST)
        if form.is_valid():
            movimiento = form.save()
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.MOVIMIENTO_EQUIPO,
                accion=historial.AccionHistorial.CREACION,
                titulo=f"Movimiento manual: {movimiento.equipo}",
                descripcion=movimiento.observaciones or "",
                objeto=movimiento,
                enlace_nombre="movimientoequipo_detail",
                metadata={"tipo_movimiento": movimiento.tipo_movimiento},
            )
            messages.success(
                request,
                "Movimiento registrado. Queda como auditoria (no editable).",
            )
            return redirect("movimientoequipo_detail", pk=movimiento.pk)
    else:
        initial = {}
        equipo_id = request.GET.get("equipo")
        if equipo_id and str(equipo_id).isdigit():
            initial["equipo"] = int(equipo_id)
        form = MovimientoEquipoForm(initial=initial)
    return render(request, "movimientoequipo/form.html", {"form": form})


def movimientoequipo_update(request, pk):
    messages.warning(
        request,
        "Los movimientos son solo auditoria y no se pueden editar.",
    )
    return redirect("movimientoequipo_detail", pk=pk)


def movimientoequipo_delete(request, pk):
    messages.warning(
        request,
        "Los movimientos son solo auditoria y no se pueden eliminar.",
    )
    return redirect("movimientoequipo_detail", pk=pk)

