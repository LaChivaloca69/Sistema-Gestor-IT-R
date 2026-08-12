"""Ubicaciones físicas y categorías de equipo."""
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
from ..forms.ubicaciones import (
    CategoriaEquipoForm,
    EdificioForm,
    UbicacionForm,
    ZonaEdificioForm,
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

def edificio_list(request):
    items = Edificio.objects.all()
    return render(request, "edificio/list.html", {"items": items})


def edificio_create(request):
    if request.method == "POST":
        form = EdificioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Edificio creado correctamente.")
            return redirect("edificio_list")
    else:
        form = EdificioForm()
    return render(request, "edificio/form.html", {"form": form})


def edificio_update(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    if request.method == "POST":
        form = EdificioForm(request.POST, instance=edificio)
        if form.is_valid():
            form.save()
            messages.success(request, "Edificio actualizado correctamente.")
            return redirect("edificio_list")
    else:
        form = EdificioForm(instance=edificio)
    return render(request, "edificio/form.html", {"form": form, "object": edificio})


def edificio_delete(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    if request.method == "POST":
        edificio.delete()
        messages.success(request, "Edificio eliminado correctamente.")
        return redirect("edificio_list")
    return render(request, "edificio/confirm_delete.html", {"object": edificio})

def zonaedificio_list(request):
    items = ZonaEdificio.objects.all()
    return render(request, "zonaedificio/list.html", {"items": items})


def zonaedificio_create(request):
    if request.method == "POST":
        form = ZonaEdificioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Zona creada correctamente.")
            return redirect("zonaedificio_list")
    else:
        form = ZonaEdificioForm()
    return render(request, "zonaedificio/form.html", {"form": form})


def zonaedificio_update(request, pk):
    zona = get_object_or_404(ZonaEdificio, pk=pk)
    if request.method == "POST":
        form = ZonaEdificioForm(request.POST, instance=zona)
        if form.is_valid():
            form.save()
            messages.success(request, "Zona actualizada correctamente.")
            return redirect("zonaedificio_list")
    else:
        form = ZonaEdificioForm(instance=zona)
    return render(request, "zonaedificio/form.html", {"form": form, "object": zona})


def zonaedificio_delete(request, pk):
    zona = get_object_or_404(ZonaEdificio, pk=pk)
    if request.method == "POST":
        zona.delete()
        messages.success(request, "Zona eliminada correctamente.")
        return redirect("zonaedificio_list")
    return render(request, "zonaedificio/confirm_delete.html", {"object": zona})

# ============  Ubicacion views ==============


def ubicacion_list(request):
    items = Ubicacion.objects.all()
    return render(request, "ubicacion/list.html", {"items": items})


def ubicacion_zona_choices(request):
    edificio_id = request.GET.get("edificio_id")
    zonas = []
    if edificio_id:
        zonas = list(
            ZonaEdificio.objects.filter(
                edificio_id=edificio_id,
                activo=True,
            )
            .order_by("nombre_zona")
            .values("id", "nombre_zona")
        )
    return JsonResponse({"zonas": zonas})


def ubicacion_create(request):
    if request.method == "POST":
        form = UbicacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ubicacion creada correctamente.")
            return redirect("ubicacion_list")
    else:
        form = UbicacionForm()
    return render(request, "ubicacion/form.html", {"form": form})


def ubicacion_update(request, pk):
    ubicacion = get_object_or_404(Ubicacion, pk=pk)
    if request.method == "POST":
        form = UbicacionForm(request.POST, instance=ubicacion)
        if form.is_valid():
            form.save()
            messages.success(request, "Ubicacion actualizada correctamente.")
            return redirect("ubicacion_list")
    else:
        form = UbicacionForm(instance=ubicacion)
    return render(request, "ubicacion/form.html", {"form": form, "object": ubicacion})


def ubicacion_delete(request, pk):
    ubicacion = get_object_or_404(Ubicacion, pk=pk)
    if request.method == "POST":
        ubicacion.delete()
        messages.success(request, "Ubicacion eliminada correctamente.")
        return redirect("ubicacion_list")
    return render(request, "ubicacion/confirm_delete.html", {"object": ubicacion})

def categoriaequipo_list(request):
    items = CategoriaEquipo.objects.all()
    return render(request, "categoriaequipo/list.html", {"items": items})


def categoriaequipo_create(request):
    if request.method == "POST":
        form = CategoriaEquipoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria creada correctamente.")
            return redirect("categoriaequipo_list")
    else:
        form = CategoriaEquipoForm()
    return render(request, "categoriaequipo/form.html", {"form": form})


def categoriaequipo_update(request, pk):
    categoria = get_object_or_404(CategoriaEquipo, pk=pk)
    if request.method == "POST":
        form = CategoriaEquipoForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria actualizada correctamente.")
            return redirect("categoriaequipo_list")
    else:
        form = CategoriaEquipoForm(instance=categoria)
    return render(request, "categoriaequipo/form.html", {"form": form, "object": categoria})


def categoriaequipo_delete(request, pk):
    categoria = get_object_or_404(CategoriaEquipo, pk=pk)
    if request.method == "POST":
        categoria.delete()
        messages.success(request, "Categoria eliminada correctamente.")
        return redirect("categoriaequipo_list")
    return render(request, "categoriaequipo/confirm_delete.html", {"object": categoria})

# ============  Equipo views ==============
