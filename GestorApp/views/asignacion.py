"""Asignaciones de equipo."""
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
from ..forms.asignacion import AsignacionEquipoForm
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


def asignacionequipo_list(request):
    items = AsignacionEquipo.objects.select_related("equipo", "personal").all()
    selected_personal = request.GET.get("personal", "")
    selected_equipo = request.GET.get("equipo", "")

    if selected_personal:
        items = items.filter(personal_id=selected_personal)
    if selected_equipo:
        items = items.filter(equipo_id=selected_equipo)

    personal_choices = []
    for personal in Personal.objects.order_by(
        "numero_empleado",
        "nombre",
        "apellido_paterno",
        "apellido_materno",
    ):
        nombre_completo = " ".join(
            parte
            for parte in [
                personal.nombre,
                personal.apellido_paterno,
                personal.apellido_materno,
            ]
            if parte
        )
        if personal.numero_empleado and nombre_completo:
            label = f"{personal.numero_empleado} - {nombre_completo}"
        elif personal.numero_empleado:
            label = personal.numero_empleado
        else:
            label = nombre_completo or str(personal)
        personal_choices.append((personal.pk, label))

    equipo_choices = []
    for equipo in Equipo.objects.select_related("categoria").order_by(
        "codigo_inventario"
    ):
        descripcion = " ".join(
            parte for parte in [equipo.marca, equipo.modelo] if parte
        ).strip()
        if descripcion:
            label = f"{equipo.codigo_inventario} - {descripcion}".strip()
        else:
            label = equipo.codigo_inventario or str(equipo)
        equipo_choices.append((equipo.pk, label))

    context = {
        "items": items,
        "personal_choices": personal_choices,
        "equipo_choices": equipo_choices,
        "selected_personal": selected_personal,
        "selected_equipo": selected_equipo,
    }
    return render(request, "asignacionequipo/list.html", context)


def asignacionequipo_create(request):
    initial = {}
    equipo_id = request.GET.get("equipo")
    if equipo_id:
        initial["equipo"] = equipo_id

    if request.method == "POST":
        form = AsignacionEquipoForm(request.POST)
        if form.is_valid():
            equipo = form.cleaned_data.get("equipo")
            personal = form.cleaned_data.get("personal")
            estado = form.cleaned_data.get("estado_asignacion")
            existente_activo = False
            if equipo and estado == EstadoAsignacion.ACTIVA:
                existente_activo = AsignacionEquipo.objects.filter(
                    equipo=equipo,
                    estado_asignacion=EstadoAsignacion.ACTIVA,
                ).exists()
                if existente_activo:
                    _cerrar_asignaciones_activas(
                        equipo,
                        observaciones="Cerrada automaticamente por reasignacion.",
                    )
            asignacion = form.save()
            if equipo:
                _reconciliar_estado_equipo(equipo)
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.ASIGNACION,
                accion=historial.AccionHistorial.ASIGNACION,
                titulo=f"Asignacion de {equipo} a {personal}",
                objeto=asignacion,
                entidad_relacionada=equipo,
                enlace_nombre="equipo_detail",
                enlace_pk=equipo.pk if equipo else None,
            )
            if equipo and estado == EstadoAsignacion.ACTIVA:
                tipo_movimiento = (
                    TipoMovimiento.CAMBIO_ASIGNACION
                    if existente_activo
                    else TipoMovimiento.ASIGNACION
                )
                _crear_movimiento(
                    equipo,
                    tipo_movimiento,
                    origen=equipo.ubicacion,
                    destino=equipo.ubicacion,
                    responsable=personal or _get_equipo_responsable(equipo),
                    request=request,
                )
            messages.success(request, "Asignacion creada correctamente.")
            if equipo:
                return redirect("equipo_detail", pk=equipo.pk)
            return redirect("asignacionequipo_list")
    else:
        form = AsignacionEquipoForm(initial=initial)
    return render(request, "asignacionequipo/form.html", {"form": form})


def asignacionequipo_update(request, pk):
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    equipo_anterior_id = asignacion.equipo_id
    personal_anterior_id = asignacion.personal_id
    estado_anterior = asignacion.estado_asignacion
    if request.method == "POST":
        form = AsignacionEquipoForm(request.POST, instance=asignacion)
        if form.is_valid():
            estado = form.cleaned_data.get("estado_asignacion")
            equipo = form.cleaned_data.get("equipo")
            if (
                equipo
                and estado == EstadoAsignacion.ACTIVA
                and estado_anterior != EstadoAsignacion.ACTIVA
            ):
                _cerrar_asignaciones_activas(
                    equipo,
                    exclude_pk=asignacion.pk,
                    observaciones="Cerrada automaticamente por reasignacion.",
                )
            asignacion = form.save()
            equipos_a_sync = {asignacion.equipo_id, equipo_anterior_id}
            for eq_id in equipos_a_sync:
                if eq_id:
                    eq = Equipo.objects.filter(pk=eq_id).first()
                    if eq:
                        _reconciliar_estado_equipo(eq)
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.ASIGNACION,
                titulo=f"Asignacion actualizada: {asignacion.equipo} / {asignacion.personal}",
                objeto=asignacion,
                form=form,
                entidad_relacionada=asignacion.equipo,
                enlace_nombre="equipo_detail",
                enlace_pk=asignacion.equipo_id,
            )
            if (
                asignacion.equipo_id != equipo_anterior_id
                or asignacion.personal_id != personal_anterior_id
                or (
                    estado == EstadoAsignacion.ACTIVA
                    and estado_anterior != EstadoAsignacion.ACTIVA
                )
            ):
                _crear_movimiento(
                    asignacion.equipo,
                    TipoMovimiento.CAMBIO_ASIGNACION,
                    origen=asignacion.equipo.ubicacion,
                    destino=asignacion.equipo.ubicacion,
                    responsable=asignacion.personal,
                    request=request,
                )
            messages.success(request, "Asignacion actualizada correctamente.")
            return redirect("equipo_detail", pk=asignacion.equipo_id)
    else:
        form = AsignacionEquipoForm(instance=asignacion)
    return render(request, "asignacionequipo/form.html", {"form": form, "object": asignacion})


def asignacionequipo_delete(request, pk):
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    equipo = asignacion.equipo
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.ASIGNACION,
            titulo=f"Asignacion eliminada: {asignacion.equipo} / {asignacion.personal}",
            objeto=asignacion,
            entidad_relacionada=equipo,
        )
        asignacion.delete()
        if equipo:
            _reconciliar_estado_equipo(equipo)
        messages.success(request, "Asignacion eliminada correctamente.")
        if equipo:
            return redirect("equipo_detail", pk=equipo.pk)
        return redirect("asignacionequipo_list")
    return render(request, "asignacionequipo/confirm_delete.html", {"object": asignacion})


# ============= Mantenimiento views ==============
