"""Asignaciones de equipo (solo maquinas principales + kit)."""
from datetime import date, datetime, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum, Max, F
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
    _sync_perifericos_con_padre,
    _ticket_dashboard_context,
    _ticket_has_seguimientos,
    _tickets_abiertos_qs,
    _tickets_for_user,
    _tickets_sla_por_vencer_q,
    _tickets_sla_vencidos_q,
    _vincular_periferico_a_equipo,
    user_can_delete_ticket,
    user_can_edit_ticket,
    user_can_manage_orden,
    user_can_manage_ticket_flow,
    user_can_view_ticket,
)


def _asignaciones_principales_qs():
    return (
        AsignacionEquipo.objects.select_related(
            "equipo",
            "equipo__categoria",
            "personal",
        )
        .annotate(
            perifericos_count=Count(
                "equipo__perifericos",
                filter=Q(
                    equipo__perifericos__activo=True,
                )
                & ~Q(equipo__perifericos__estado_equipo=EstadoEquipo.BAJA),
                distinct=True,
            )
        )
        .filter(equipo__categoria__tipo=TipoCategoriaInventario.EQUIPO)
    )


def _asignaciones_periferico_sueltas_qs():
    """Asignaciones activas de perifericos (legado a migrar al kit)."""
    return (
        AsignacionEquipo.objects.select_related(
            "equipo",
            "equipo__categoria",
            "equipo__equipo_padre",
            "personal",
        )
        .filter(
            estado_asignacion=EstadoAsignacion.ACTIVA,
            equipo__categoria__tipo=TipoCategoriaInventario.PERIFERICO,
        )
        .order_by("personal_id", "equipo__codigo_inventario")
    )


def _personal_label(personal):
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
        return f"{personal.numero_empleado} - {nombre_completo}"
    if personal.numero_empleado:
        return personal.numero_empleado
    return nombre_completo or str(personal)


def _equipo_label(equipo):
    descripcion = " ".join(
        parte for parte in [equipo.marca, equipo.modelo] if parte
    ).strip()
    if descripcion:
        return f"{equipo.codigo_inventario} - {descripcion}".strip()
    return equipo.codigo_inventario or str(equipo)


def _sugerencias_migracion_kit():
    """
    Para cada asignacion activa de periferico, propone un equipo padre
    si la misma persona tiene asignacion(es) activa(s) de Equipo.
    """
    sueltas = list(_asignaciones_periferico_sueltas_qs())
    if not sueltas:
        return []

    personal_ids = {a.personal_id for a in sueltas if a.personal_id}
    equipos_por_personal = {}
    for asig in (
        AsignacionEquipo.objects.select_related("equipo", "equipo__categoria")
        .filter(
            personal_id__in=personal_ids,
            estado_asignacion=EstadoAsignacion.ACTIVA,
            equipo__categoria__tipo=TipoCategoriaInventario.EQUIPO,
        )
        .order_by("equipo__codigo_inventario")
    ):
        equipos_por_personal.setdefault(asig.personal_id, []).append(asig.equipo)

    sugerencias = []
    for asig in sueltas:
        candidatos = equipos_por_personal.get(asig.personal_id, [])
        sugerido = candidatos[0] if len(candidatos) == 1 else None
        ya_vinculado = bool(asig.equipo.equipo_padre_id)
        sugerencias.append(
            {
                "asignacion": asig,
                "periferico": asig.equipo,
                "personal": asig.personal,
                "candidatos": candidatos,
                "sugerido": sugerido,
                "ya_vinculado": ya_vinculado,
                "puede_auto": (sugerido is not None) or ya_vinculado,
            }
        )
    return sugerencias


def asignacionequipo_list(request):
    items = _asignaciones_principales_qs().order_by("-fecha_asignacion", "-pk")
    selected_personal = request.GET.get("personal", "")
    selected_equipo = request.GET.get("equipo", "")
    selected_estado = request.GET.get("estado", EstadoAsignacion.ACTIVA)

    if selected_personal:
        items = items.filter(personal_id=selected_personal)
    if selected_equipo:
        items = items.filter(equipo_id=selected_equipo)
    if selected_estado:
        items = items.filter(estado_asignacion=selected_estado)

    personal_choices = [
        (personal.pk, _personal_label(personal))
        for personal in Personal.objects.order_by(
            "numero_empleado",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
        )
    ]
    equipo_choices = [
        (equipo.pk, _equipo_label(equipo))
        for equipo in Equipo.objects.select_related("categoria")
        .filter(categoria__tipo=TipoCategoriaInventario.EQUIPO)
        .order_by("codigo_inventario")
    ]

    sueltas_count = _asignaciones_periferico_sueltas_qs().count()

    context = {
        "items": items,
        "personal_choices": personal_choices,
        "equipo_choices": equipo_choices,
        "estado_choices": EstadoAsignacion.choices,
        "selected_personal": selected_personal,
        "selected_equipo": selected_equipo,
        "selected_estado": selected_estado,
        "sueltas_count": sueltas_count,
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
                _sync_perifericos_con_padre(equipo, request=request)
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
                    eq = Equipo.objects.filter(pk=eq_id).select_related("categoria").first()
                    if eq:
                        _reconciliar_estado_equipo(eq)
                        _sync_perifericos_con_padre(eq, request=request)
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
            _sync_perifericos_con_padre(equipo, request=request)
        messages.success(request, "Asignacion eliminada correctamente.")
        if equipo:
            return redirect("equipo_detail", pk=equipo.pk)
        return redirect("asignacionequipo_list")
    return render(request, "asignacionequipo/confirm_delete.html", {"object": asignacion})


def asignacion_kit_migracion(request):
    """
    Asistente: convierte asignaciones sueltas de perifericos en vinculos al kit
    del equipo principal de la misma persona.
    """
    sugerencias = _sugerencias_migracion_kit()

    if request.method == "POST":
        selected_ids = request.POST.getlist("asignacion_id")
        aplicados = 0
        omitidos = 0
        errores = 0
        for raw_id in selected_ids:
            if not str(raw_id).isdigit():
                continue
            asig = (
                AsignacionEquipo.objects.select_related(
                    "equipo", "equipo__categoria", "personal"
                )
                .filter(
                    pk=int(raw_id),
                    estado_asignacion=EstadoAsignacion.ACTIVA,
                    equipo__categoria__tipo=TipoCategoriaInventario.PERIFERICO,
                )
                .first()
            )
            if not asig:
                omitidos += 1
                continue

            periferico = asig.equipo
            padre_id = request.POST.get(f"padre_{asig.pk}", "").strip()
            padre = None
            if padre_id.isdigit():
                padre = (
                    Equipo.objects.select_related("categoria")
                    .filter(
                        pk=int(padre_id),
                        categoria__tipo=TipoCategoriaInventario.EQUIPO,
                    )
                    .first()
                )
            elif periferico.equipo_padre_id:
                # Ya vinculado: solo cerrar asignacion suelta.
                _cerrar_asignaciones_activas(
                    periferico,
                    observaciones="Cerrada al migrar a kit (ya estaba vinculado).",
                )
                _reconciliar_estado_equipo(periferico)
                aplicados += 1
                continue

            if padre is None:
                # Intentar unico equipo activo de la persona.
                unicos = list(
                    AsignacionEquipo.objects.filter(
                        personal=asig.personal,
                        estado_asignacion=EstadoAsignacion.ACTIVA,
                        equipo__categoria__tipo=TipoCategoriaInventario.EQUIPO,
                    ).select_related("equipo")
                )
                if len(unicos) == 1:
                    padre = unicos[0].equipo

            if padre is None:
                omitidos += 1
                continue

            try:
                with transaction.atomic():
                    if periferico.equipo_padre_id and periferico.equipo_padre_id != padre.pk:
                        omitidos += 1
                        continue
                    if not periferico.equipo_padre_id:
                        _vincular_periferico_a_equipo(
                            periferico,
                            padre,
                            request=request,
                            observaciones=(
                                f"Migracion kit: de asignacion suelta de "
                                f"{asig.personal} al equipo {padre.codigo_inventario}"
                            ),
                        )
                    else:
                        _cerrar_asignaciones_activas(
                            periferico,
                            observaciones="Cerrada al migrar a kit.",
                        )
                        _reconciliar_estado_equipo(periferico)
                    aplicados += 1
            except ValidationError:
                errores += 1

        if aplicados:
            messages.success(
                request,
                f"Migracion aplicada: {aplicados} periferico(s) pasaron al kit.",
            )
        if omitidos:
            messages.warning(
                request,
                f"{omitidos} fila(s) omitidas (sin equipo padre claro o ya resueltas).",
            )
        if errores:
            messages.error(request, f"{errores} fila(s) con error al vincular.")
        return redirect("asignacion_kit_migracion")

    return render(
        request,
        "asignacionequipo/kit_migracion.html",
        {
            "sugerencias": sugerencias,
            "total": len(sugerencias),
            "auto_count": sum(1 for s in sugerencias if s["puede_auto"]),
        },
    )
