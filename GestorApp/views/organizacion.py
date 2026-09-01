"""Organización: áreas, puestos, personal, proveedores."""
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
from ..forms.organizacion import (
    AreaForm,
    PersonalForm,
    ProveedorForm,
    PuestoForm,
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
    _propagar_custodia_personal_a_equipos,
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

def area_list(request):
    items = Area.objects.all()
    return render(request, "area/list.html", {"items": items})

def area_create(request):
    if request.method == "POST":
        form = AreaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Area creada correctamente.")
            return redirect("area_list")
    else:
        form = AreaForm()
    return render(request, "area/form.html", {"form": form})

def area_update(request, pk):
    area = get_object_or_404(Area, pk=pk)
    if request.method == "POST":
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, "Area actualizada correctamente.")
            return redirect("area_list")
    else:
        form = AreaForm(instance=area)
    return render(request, "area/form.html", {"form": form, "object": area})

def area_delete(request, pk):
    area = get_object_or_404(Area, pk=pk)
    if request.method == "POST":
        area.delete()
        messages.success(request, "Area eliminada correctamente.")
        return redirect("area_list")
    return render(request, "area/confirm_delete.html", {"object": area})

def puesto_list(request):
    items = Puesto.objects.all()
    return render(request, "puesto/list.html", {"items": items})


def puesto_create(request):
    if request.method == "POST":
        form = PuestoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Puesto creado correctamente.")
            return redirect("puesto_list")
    else:
        form = PuestoForm()
    return render(request, "puesto/form.html", {"form": form})


def puesto_update(request, pk):
    puesto = get_object_or_404(Puesto, pk=pk)
    if request.method == "POST":
        form = PuestoForm(request.POST, instance=puesto)
        if form.is_valid():
            form.save()
            messages.success(request, "Puesto actualizado correctamente.")
            return redirect("puesto_list")
    else:
        form = PuestoForm(instance=puesto)
    return render(request, "puesto/form.html", {"form": form, "object": puesto})


def puesto_delete(request, pk):
    puesto = get_object_or_404(Puesto, pk=pk)
    if request.method == "POST":
        puesto.delete()
        messages.success(request, "Puesto eliminado correctamente.")
        return redirect("puesto_list")
    return render(request, "puesto/confirm_delete.html", {"object": puesto})


def personal_list(request):
    items = Personal.objects.select_related(
        "user", "area", "puesto", "ubicacion", "ubicacion__edificio", "ubicacion__zona"
    ).all()
    search_query = (request.GET.get("q") or "").strip()
    selected_area = request.GET.get("area", "")
    selected_puesto = request.GET.get("puesto", "")
    selected_activo = request.GET.get("activo", "")
    fecha_desde_raw = request.GET.get("fecha_ingreso_desde", "")
    fecha_hasta_raw = request.GET.get("fecha_ingreso_hasta", "")
    fecha_mes = request.GET.get("fecha_ingreso_mes", "")
    fecha_rango = request.GET.get("fecha_ingreso_rango", "")

    if search_query:
        items = items.filter(
            Q(numero_empleado__icontains=search_query)
            | Q(nombre__icontains=search_query)
            | Q(apellido_paterno__icontains=search_query)
            | Q(apellido_materno__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(correo__icontains=search_query)
        )
    if selected_area:
        items = items.filter(area_id=selected_area)
    if selected_puesto:
        items = items.filter(puesto_id=selected_puesto)
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)

    fecha_desde = _parse_date(fecha_desde_raw)
    fecha_hasta = _parse_date(fecha_hasta_raw)
    if not fecha_desde and not fecha_hasta:
        month_start, month_end = _month_bounds(fecha_mes)
        if month_start:
            fecha_desde, fecha_hasta = month_start, month_end
        else:
            range_start, range_end = _quick_range_bounds(fecha_rango)
            if range_start:
                fecha_desde, fecha_hasta = range_start, range_end
    items = _apply_date_filters(items, "fecha_ingreso", fecha_desde, fecha_hasta)

    items = list(items)
    for item in items:
        item.rol_label = get_user_role(item.user) if item.user_id else "—"

    context = {
        "items": items,
        "area_choices": Area.objects.order_by("nombre_area").values_list(
            "id", "nombre_area"
        ),
        "puesto_choices": Puesto.objects.order_by("nombre_puesto").values_list(
            "id", "nombre_puesto"
        ),
        "search_query": search_query,
        "selected_area": selected_area,
        "selected_puesto": selected_puesto,
        "selected_activo": selected_activo,
        "fecha_ingreso_desde": fecha_desde_raw,
        "fecha_ingreso_hasta": fecha_hasta_raw,
        "fecha_ingreso_mes": fecha_mes,
        "fecha_ingreso_rango": fecha_rango,
        "can_manage_personal": is_admin_user(request.user),
    }
    return render(request, "personal/list.html", context)


def personal_detail(request, pk):
    personal = get_object_or_404(
        Personal.objects.select_related(
            "user", "area", "puesto", "ubicacion", "ubicacion__edificio", "ubicacion__zona"
        ),
        pk=pk,
    )
    return render(
        request,
        "personal/detail.html",
        {
            "object": personal,
            "rol_label": get_user_role(personal.user) if personal.user_id else "—",
            "can_manage_personal": is_admin_user(request.user),
        },
    )


def personal_admin_requests(request):
    """Compat: redirige a gestion de personal/roles."""
    messages.info(request, "Los roles se asignan al editar el personal.")
    return redirect("personal_list")


def personal_admin_remove(request):
    """Panel rapido para bajar a Usuario a Tecnico/Admin (excepto superusers)."""
    if request.method == "POST":
        personal_id = request.POST.get("personal_id")
        personal = get_object_or_404(Personal, pk=personal_id)
        if not personal.user_id:
            messages.error(request, "El personal no tiene usuario asignado.")
            return redirect("personal_admin_remove")
        if personal.user.is_superuser:
            messages.error(request, "No se puede cambiar el rol de un superusuario.")
            return redirect("personal_admin_remove")
        if request.user.pk == personal.user_id:
            messages.error(request, "No puedes quitarte el rol de administrador a ti mismo.")
            return redirect("personal_admin_remove")
        set_user_role(personal.user, ROLE_USUARIO)
        if personal.admin_requested:
            personal.admin_requested = False
            personal.save(update_fields=["admin_requested"])
        messages.success(request, "Rol cambiado a Usuario.")
        historial.registrar_historial(
            request=request,
            modulo=ModuloHistorial.PERSONAL,
            accion=historial.AccionHistorial.CAMBIO_ESTADO,
            titulo=f"Rol reducido a Usuario: {personal}",
            objeto=personal,
            enlace_nombre="personal_update",
        )
        return redirect("personal_admin_remove")
    items = []
    for personal in Personal.objects.select_related("user").filter(user__isnull=False):
        role = get_user_role(personal.user)
        if role in {ROLE_TECNICO, ROLE_ADMIN} and not personal.user.is_superuser:
            personal.rol_label = role
            items.append(personal)
    return render(request, "personal/admin_remove.html", {"items": items})


def historial_retencion_admin(request):
    """Panel admin para previsualizar y encolar archivar/purgar del historial."""
    from django.conf import settings as django_settings

    from ..job_queue import enqueue_retencion

    cfg = getattr(django_settings, "HISTORIAL_RETENCION", {}) or {}
    candidatos_archivo = historial.queryset_candidatos_archivo().count()
    candidatos_purga = historial.queryset_candidatos_purga().count()
    totales = {
        "activos": HistorialActividad.objects.filter(archivado=False).count(),
        "archivados": HistorialActividad.objects.filter(archivado=True).count(),
        "criticos": HistorialActividad.objects.filter(nivel=NivelHistorial.CRITICO).count(),
        "total": HistorialActividad.objects.count(),
    }

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip().lower()
        confirmar = (request.POST.get("confirmar") or "").strip().upper() == "CONFIRMAR"

        if accion not in {"archivar", "purgar", "ambos"}:
            messages.error(request, "Accion no valida.")
            return redirect("historial_retencion_admin")

        if accion in {"purgar", "ambos"} and not confirmar:
            messages.error(
                request,
                "Para purgar debes escribir CONFIRMAR en el campo de confirmacion "
                "(la purga borra registros de forma permanente).",
            )
            return redirect("historial_retencion_admin")

        resultado, mode = enqueue_retencion(
            accion=accion,
            solicitado_por_id=request.user.pk,
        )
        if mode == "async":
            messages.success(
                request,
                f"Retencion ({accion}) encolada en background (tarea {resultado}). "
                "El worker django-q la ejecutara en breve.",
            )
        else:
            archivados = (resultado or {}).get("archivados", 0)
            purgados = (resultado or {}).get("purgados", 0)
            messages.success(
                request,
                f"Retencion aplicada en este request (sin worker). "
                f"Archivados: {archivados}. Purgados: {purgados}.",
            )
        return redirect("historial_retencion_admin")

    return render(
        request,
        "historial/retencion.html",
        {
            "config": {
                "modo": cfg.get("modo", "archivar_luego_purgar"),
                "dias_activo": cfg.get("dias_activo", 180),
                "dias_archivo": cfg.get("dias_archivo", 365),
                "proteger_criticos": cfg.get("proteger_criticos", True),
            },
            "candidatos_archivo": candidatos_archivo,
            "candidatos_purga": candidatos_purga,
            "totales": totales,
            "background_jobs_sync": bool(
                getattr(django_settings, "BACKGROUND_JOBS_SYNC", False)
            ),
        },
    )


def personal_create(request):
    if request.method == "POST":
        form = PersonalForm(request.POST, request_user=request.user)
        if form.is_valid():
            personal = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.PERSONAL,
                titulo=f"Personal agregado: {personal}",
                objeto=personal,
                enlace_nombre="personal_update",
            )
            messages.success(request, "Personal creado correctamente.")
            return redirect("personal_list")
    else:
        form = PersonalForm(request_user=request.user)
    return render(request, "personal/form.html", {"form": form})


def personal_update(request, pk):
    personal = get_object_or_404(Personal, pk=pk)
    ubicacion_anterior_id = personal.ubicacion_id
    area_anterior_id = personal.area_id
    if request.method == "POST":
        form = PersonalForm(request.POST, instance=personal, request_user=request.user)
        if form.is_valid():
            with transaction.atomic():
                personal = form.save()
                equipos_actualizados = 0
                if (
                    personal.ubicacion_id != ubicacion_anterior_id
                    or personal.area_id != area_anterior_id
                ):
                    equipos_actualizados = _propagar_custodia_personal_a_equipos(
                        personal, request=request
                    )
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.PERSONAL,
                titulo=f"Personal actualizado: {personal}",
                objeto=personal,
                form=form,
                enlace_nombre="personal_update",
            )
            messages.success(request, "Personal actualizado correctamente.")
            if equipos_actualizados:
                messages.info(
                    request,
                    f"Se actualizo la ubicacion de {equipos_actualizados} equipo(s) asignado(s).",
                )
            return redirect("personal_list")
    else:
        form = PersonalForm(instance=personal, request_user=request.user)
    return render(request, "personal/form.html", {"form": form, "object": personal})


def personal_delete(request, pk):
    personal = get_object_or_404(Personal, pk=pk)
    if request.method == "POST":
        etiqueta = str(personal)
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.PERSONAL,
            titulo=f"Personal eliminado: {etiqueta}",
            objeto=personal,
            metadata={"personal_id": personal.pk},
            nivel=NivelHistorial.CRITICO,
        )
        personal.delete()
        messages.success(request, "Personal eliminado correctamente.")
        return redirect("personal_list")
    return render(request, "personal/confirm_delete.html", {"object": personal})

def proveedor_list(request):
    items = Proveedor.objects.all()
    selected_tipo = request.GET.get("tipo", "")
    selected_activo = request.GET.get("activo", "")
    search_query = (request.GET.get("q") or "").strip()

    if search_query:
        items = items.filter(
            Q(nombre_proveedor__icontains=search_query)
            | Q(razon_social__icontains=search_query)
            | Q(codigo_interno__icontains=search_query)
            | Q(rfc__icontains=search_query)
            | Q(contacto__icontains=search_query)
            | Q(correo__icontains=search_query)
        )
    if selected_tipo:
        items = items.filter(tipo=selected_tipo)
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)

    return render(
        request,
        "proveedor/list.html",
        {
            "items": items,
            "tipo_choices": TipoProveedor.choices,
            "selected_tipo": selected_tipo,
            "selected_activo": selected_activo,
            "search_query": search_query,
        },
    )


def proveedor_create(request):
    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor creado correctamente.")
            return redirect("proveedor_list")
    else:
        form = ProveedorForm()
    return render(request, "proveedor/form.html", {"form": form})


def proveedor_update(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor actualizado correctamente.")
            return redirect("proveedor_list")
    else:
        form = ProveedorForm(instance=proveedor)
    return render(request, "proveedor/form.html", {"form": form, "object": proveedor})


def proveedor_delete(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        proveedor.delete()
        messages.success(request, "Proveedor eliminado correctamente.")
        return redirect("proveedor_list")
    return render(request, "proveedor/confirm_delete.html", {"object": proveedor})

# ============  Edificio views ==============
# Formulario de edificio
