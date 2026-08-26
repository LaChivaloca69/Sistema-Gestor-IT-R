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
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_POST

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
    ProductoConsumible,
    Proveedor,
    Puesto,
    SLA_HORAS_POR_PRIORIDAD,
    SeguimientoTicket,
    TicketIT,
    TipoCategoriaInventario,
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

def _zona_referencias(zona):
    refs = []
    n_ubi = Ubicacion.objects.filter(zona=zona).count()
    if n_ubi:
        refs.append(f"{n_ubi} ubicacion(es)")
    return refs


def _toggle_activo_and_redirect(request, obj, list_url_name, etiqueta):
    obj.activo = not obj.activo
    obj.save(update_fields=["activo"])
    if obj.activo:
        messages.success(request, f'{etiqueta} "{obj}" reactivado/a.')
    else:
        messages.success(
            request,
            f'{etiqueta} "{obj}" desactivado/a. Ya no aparecera en altas nuevas.',
        )
    return redirect(list_url_name)


def edificio_list(request):
    items = Edificio.objects.all().order_by("nombre_edificio")
    selected_activo = request.GET.get("activo", "true")
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)
    return render(
        request,
        "edificio/list.html",
        {"items": items, "selected_activo": selected_activo},
    )


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


@require_POST
def edificio_toggle_activo(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    return _toggle_activo_and_redirect(request, edificio, "edificio_list", "Edificio")


def edificio_delete(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    # Solo ubicaciones bloquean (PROTECT). Las zonas sin ubicacion si se pueden cascader.
    n_ubi = Ubicacion.objects.filter(edificio=edificio).count()
    referencias = []
    if n_ubi:
        referencias.append(f"{n_ubi} ubicacion(es)")
    n_zonas = edificio.zonas.count()
    puede_eliminar = n_ubi == 0

    if request.method == "POST":
        accion = (request.POST.get("accion") or "eliminar").strip()
        if accion == "desactivar":
            if edificio.activo:
                edificio.activo = False
                edificio.save(update_fields=["activo"])
                messages.success(
                    request,
                    f'Edificio "{edificio}" desactivado. Conserva zonas y ubicaciones.',
                )
            else:
                messages.info(request, "El edificio ya estaba inactivo.")
            return redirect("edificio_list")

        if not puede_eliminar:
            messages.error(
                request,
                "No se puede eliminar: tiene ubicaciones vinculadas ("
                + "; ".join(referencias)
                + "). Usa Desactivar.",
            )
            return redirect("edificio_delete", pk=pk)

        try:
            nombre = str(edificio)
            edificio.delete()
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar: hay ubicaciones que lo referencian. "
                "Desactivalo en su lugar.",
            )
            return redirect("edificio_delete", pk=pk)

        messages.success(request, f'Edificio "{nombre}" eliminado correctamente.')
        return redirect("edificio_list")

    avisos = list(referencias)
    if puede_eliminar and n_zonas:
        avisos.append(
            f"Al eliminar se borraran tambien {n_zonas} zona(s) asociada(s) (cascada)."
        )

    return render(
        request,
        "edificio/confirm_delete.html",
        {
            "object": edificio,
            "referencias": referencias,
            "avisos": avisos,
            "puede_eliminar": puede_eliminar,
        },
    )


def zonaedificio_list(request):
    items = ZonaEdificio.objects.select_related("edificio").order_by(
        "edificio__nombre_edificio", "nombre_zona"
    )
    selected_activo = request.GET.get("activo", "true")
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)
    return render(
        request,
        "zonaedificio/list.html",
        {"items": items, "selected_activo": selected_activo},
    )


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


@require_POST
def zonaedificio_toggle_activo(request, pk):
    zona = get_object_or_404(ZonaEdificio, pk=pk)
    return _toggle_activo_and_redirect(request, zona, "zonaedificio_list", "Zona")


def zonaedificio_delete(request, pk):
    zona = get_object_or_404(ZonaEdificio, pk=pk)
    referencias = _zona_referencias(zona)
    puede_eliminar = not referencias

    if request.method == "POST":
        accion = (request.POST.get("accion") or "eliminar").strip()
        if accion == "desactivar":
            if zona.activo:
                zona.activo = False
                zona.save(update_fields=["activo"])
                messages.success(
                    request,
                    f'Zona "{zona}" desactivada. Conserva las ubicaciones vinculadas.',
                )
            else:
                messages.info(request, "La zona ya estaba inactiva.")
            return redirect("zonaedificio_list")

        if not puede_eliminar:
            messages.error(
                request,
                "No se puede eliminar: esta en uso ("
                + "; ".join(referencias)
                + "). Usa Desactivar.",
            )
            return redirect("zonaedificio_delete", pk=pk)

        try:
            nombre = str(zona)
            zona.delete()
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar: hay ubicaciones que la referencian. "
                "Desactivala en su lugar.",
            )
            return redirect("zonaedificio_delete", pk=pk)

        messages.success(request, f'Zona "{nombre}" eliminada correctamente.')
        return redirect("zonaedificio_list")

    return render(
        request,
        "zonaedificio/confirm_delete.html",
        {
            "object": zona,
            "referencias": referencias,
            "puede_eliminar": puede_eliminar,
        },
    )

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

def _categoria_referencias(categoria):
    """Conteos de usos que bloquean borrado (FK PROTECT)."""
    refs = []
    n_eq = Equipo.objects.filter(categoria=categoria).count()
    if n_eq:
        refs.append(f"{n_eq} equipo(s) / periferico(s) / herramienta(s)")
    n_tk = TicketIT.objects.filter(tipo_equipo=categoria).count()
    if n_tk:
        refs.append(f"{n_tk} ticket(s)")
    n_cons = ProductoConsumible.objects.filter(categoria=categoria).count()
    if n_cons:
        refs.append(f"{n_cons} consumible(s)")
    return refs


def categoriaequipo_list(request):
    items = CategoriaEquipo.objects.all().order_by("tipo", "nombre_categoria")
    selected_tipo = (request.GET.get("tipo") or "").strip()
    selected_activo = request.GET.get("activo", "true")
    if selected_tipo:
        items = items.filter(tipo=selected_tipo)
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)
    return render(
        request,
        "categoriaequipo/list.html",
        {
            "items": items,
            "tipo_choices": TipoCategoriaInventario.choices,
            "selected_tipo": selected_tipo,
            "selected_activo": selected_activo,
        },
    )


def categoriaequipo_create(request):
    if request.method == "POST":
        form = CategoriaEquipoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria creada correctamente.")
            return redirect("categoriaequipo_list")
    else:
        initial = {}
        tipo = (request.GET.get("tipo") or "").strip()
        if tipo in {c.value for c in TipoCategoriaInventario}:
            initial["tipo"] = tipo
        form = CategoriaEquipoForm(initial=initial)
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


@require_POST
def categoriaequipo_toggle_activo(request, pk):
    categoria = get_object_or_404(CategoriaEquipo, pk=pk)
    categoria.activo = not categoria.activo
    categoria.save(update_fields=["activo"])
    if categoria.activo:
        messages.success(request, f'Categoria "{categoria}" reactivada.')
    else:
        messages.success(
            request,
            f'Categoria "{categoria}" desactivada. Ya no aparecera en formularios nuevos.',
        )
    return redirect("categoriaequipo_list")


def categoriaequipo_delete(request, pk):
    categoria = get_object_or_404(CategoriaEquipo, pk=pk)
    referencias = _categoria_referencias(categoria)
    puede_eliminar = not referencias

    if request.method == "POST":
        accion = (request.POST.get("accion") or "eliminar").strip()
        if accion == "desactivar":
            if categoria.activo:
                categoria.activo = False
                categoria.save(update_fields=["activo"])
                messages.success(
                    request,
                    f'Categoria "{categoria}" desactivada. Conserva el historial vinculado.',
                )
            else:
                messages.info(request, "La categoria ya estaba inactiva.")
            return redirect("categoriaequipo_list")

        if not puede_eliminar:
            messages.error(
                request,
                "No se puede eliminar: esta en uso ("
                + "; ".join(referencias)
                + "). Usa Desactivar para dejar de ofrecela en altas nuevas.",
            )
            return redirect("categoriaequipo_delete", pk=pk)

        try:
            nombre = str(categoria)
            categoria.delete()
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar: hay registros que la referencian. "
                "Desactivala en su lugar.",
            )
            return redirect("categoriaequipo_delete", pk=pk)

        messages.success(request, f'Categoria "{nombre}" eliminada correctamente.')
        return redirect("categoriaequipo_list")

    return render(
        request,
        "categoriaequipo/confirm_delete.html",
        {
            "object": categoria,
            "referencias": referencias,
            "puede_eliminar": puede_eliminar,
        },
    )

# ============  Equipo views ==============
