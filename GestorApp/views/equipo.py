"""Inventario de equipos."""
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
from django.db.models import Count, Exists, F, Max, OuterRef, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import NoReverseMatch, reverse

from .. import document_engine
from .. import historial
from ..cobertura import coberturas_activas_para_suplente, ticket_asignados_q_for_user
from ..forms.equipo import (
    EquipoAsignarForm,
    EquipoBajaForm,
    EquipoForm,
    EquipoUbicacionForm,
    EquipoVincularPerifericoForm,
    PerifericoDesvincularForm,
    PerifericoReemplazarForm,
    PerifericoVincularEquipoForm,
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
from ..inventory_types import get_inventario_ui, inventario_ui_for_equipo, resolve_inventario_tipo
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
    _aplicar_asignacion_a_equipo,
    _cerrar_asignaciones_activas,
    _crear_movimiento,
    _deny_ticket_access,
    _desvincular_periferico,
    _end_of_month,
    _get_equipo_asignacion_activa,
    _get_equipo_responsable,
    _get_espacio_stock_default,
    _liberar_equipo_tras_devolucion,
    _month_bounds,
    _ordenes_for_user,
    _parse_date,
    _quick_range_bounds,
    _reconciliar_estado_equipo,
    _reemplazar_periferico,
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

EQUIPO_LIST_PAGE_SIZE = 20
EQUIPO_ASIGNACION_ALERTA_DIAS = 180
EQUIPO_MANTENIMIENTO_LARGO_DIAS = 14


def _mark_inventario_nav(request, inv):
    request.inventario_list_url_name = inv["list_url"]
    return inv


def _equipo_queryset():
    return Equipo.objects.select_related(
        "categoria",
        "proveedor",
        "area",
        "ubicacion",
        "ubicacion__edificio",
        "ubicacion__zona",
        "orden_compra",
        "detalle_orden",
        "equipo_padre",
        "equipo_padre__categoria",
    ).annotate(perifericos_count=Count("perifericos", distinct=True))


def _equipos_sin_ubicacion_qs(tipo=None):
    asignacion_sin_puesto_fijo = AsignacionEquipo.objects.filter(
        equipo=OuterRef("pk"),
        estado_asignacion=EstadoAsignacion.ACTIVA,
        personal__ubicacion__isnull=True,
    )
    qs = (
        _equipo_queryset()
        .filter(ubicacion__isnull=True)
        .exclude(estado_equipo=EstadoEquipo.BAJA)
        .filter(activo=True)
        .exclude(Exists(asignacion_sin_puesto_fijo))
    )
    if tipo:
        qs = qs.filter(categoria__tipo=tipo)
    return qs


def _equipos_mantenimiento_largo_qs(now=None, dias=EQUIPO_MANTENIMIENTO_LARGO_DIAS, tipo=None):
    now = now or timezone.now()
    limite = now - timedelta(days=dias)
    qs = (
        _equipo_queryset()
        .filter(estado_equipo=EstadoEquipo.EN_MANTENIMIENTO)
        .annotate(
            ultimo_inicio_mant=Max(
                "movimientos__fecha_movimiento",
                filter=Q(movimientos__tipo_movimiento=TipoMovimiento.MANTENIMIENTO),
            )
        )
        .filter(Q(ultimo_inicio_mant__lte=limite) | Q(ultimo_inicio_mant__isnull=True))
        .order_by(F("ultimo_inicio_mant").asc(nulls_first=True), "codigo_inventario")
    )
    if tipo:
        qs = qs.filter(categoria__tipo=tipo)
    return qs


def _asignaciones_antiguas_qs(today=None, dias=EQUIPO_ASIGNACION_ALERTA_DIAS, tipo=None):
    today = today or timezone.localdate()
    cutoff = today - timedelta(days=dias)
    qs = (
        AsignacionEquipo.objects.select_related("equipo", "personal", "equipo__categoria")
        .filter(
            estado_asignacion=EstadoAsignacion.ACTIVA,
            fecha_asignacion__date__lte=cutoff,
        )
        .exclude(equipo__estado_equipo=EstadoEquipo.BAJA)
        .order_by("fecha_asignacion", "pk")
    )
    if tipo:
        qs = qs.filter(equipo__categoria__tipo=tipo)
    return qs


def _equipos_alerta_context(
    today=None,
    asignacion_dias=EQUIPO_ASIGNACION_ALERTA_DIAS,
    mant_dias=EQUIPO_MANTENIMIENTO_LARGO_DIAS,
    tipo=TipoCategoriaInventario.EQUIPO,
):
    today = today or timezone.localdate()
    sin_ubicacion_qs = _equipos_sin_ubicacion_qs(tipo=tipo).order_by("codigo_inventario")
    mant_largo_qs = _equipos_mantenimiento_largo_qs(dias=mant_dias, tipo=tipo)
    asign_antiguas_qs = _asignaciones_antiguas_qs(today=today, dias=asignacion_dias, tipo=tipo)
    return {
        "equipos_sin_ubicacion": list(sin_ubicacion_qs[:8]),
        "equipos_sin_ubicacion_count": sin_ubicacion_qs.count(),
        "equipos_mant_largo": list(mant_largo_qs[:8]),
        "equipos_mant_largo_count": mant_largo_qs.count(),
        "asignaciones_antiguas": list(asign_antiguas_qs[:8]),
        "asignaciones_antiguas_count": asign_antiguas_qs.count(),
        "equipos_asignacion_alerta_dias": asignacion_dias,
        "equipos_mant_largo_dias": mant_dias,
    }


def _equipo_dashboard_context(today=None, tipo=TipoCategoriaInventario.EQUIPO):
    today = today or timezone.localdate()
    alerta = _equipos_alerta_context(today=today, tipo=tipo)
    qs = _equipo_queryset().filter(categoria__tipo=tipo)

    por_estado = []
    for value, label in EstadoEquipo.choices:
        por_estado.append(
            {
                "value": value,
                "label": label,
                "count": qs.filter(estado_equipo=value).count(),
            }
        )

    por_categoria = list(
        qs.values("categoria_id", "categoria__nombre_categoria")
        .annotate(total=Count("id"))
        .order_by("-total", "categoria__nombre_categoria")[:10]
    )

    por_ubicacion = list(
        qs.exclude(ubicacion__isnull=True)
        .values(
            "ubicacion_id",
            "ubicacion__edificio__nombre_edificio",
            "ubicacion__zona__nombre_zona",
            "ubicacion__referencia",
        )
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )

    return {
        "equipo_dashboard": {
            "total": qs.count(),
            "activos": qs.filter(activo=True).exclude(estado_equipo=EstadoEquipo.BAJA).count(),
            "disponibles": qs.filter(estado_equipo=EstadoEquipo.DISPONIBLE).count(),
            "asignados": qs.filter(estado_equipo=EstadoEquipo.ASIGNADO).count(),
            "en_mantenimiento": qs.filter(estado_equipo=EstadoEquipo.EN_MANTENIMIENTO).count(),
            "baja": qs.filter(estado_equipo=EstadoEquipo.BAJA).count(),
            "sin_ubicacion": alerta["equipos_sin_ubicacion_count"],
            "mant_largo": alerta["equipos_mant_largo_count"],
            "asignaciones_antiguas": alerta["asignaciones_antiguas_count"],
            "por_estado": por_estado,
            "por_categoria": por_categoria,
            "por_ubicacion": por_ubicacion,
            "lista_sin_ubicacion": alerta["equipos_sin_ubicacion"],
            "lista_mant_largo": alerta["equipos_mant_largo"],
            "lista_asignaciones_antiguas": alerta["asignaciones_antiguas"],
            "asignacion_alerta_dias": alerta["equipos_asignacion_alerta_dias"],
            "mant_largo_dias": alerta["equipos_mant_largo_dias"],
        }
    }


def equipo_dashboard(request):
    return render(
        request,
        "equipo/dashboard.html",
        {
            "today": timezone.localdate(),
            **_equipo_dashboard_context(),
        },
    )


def _filtrar_equipos(request, tipo=None):
    items = _equipo_queryset().order_by("-fecha_alta", "-pk")
    if tipo:
        items = items.filter(categoria__tipo=tipo)
    search_query = (request.GET.get("q") or "").strip()
    selected_categoria = request.GET.get("categoria", "")
    selected_estado = request.GET.get("estado_equipo", "")
    selected_activo = request.GET.get("activo", "")
    selected_ubicacion = request.GET.get("ubicacion", "")
    selected_sin_ubicacion = request.GET.get("sin_ubicacion", "")
    selected_alerta = (request.GET.get("alerta") or "").strip()
    selected_origen = request.GET.get("origen_alta", "")
    selected_sin_oc = request.GET.get("sin_oc", "")
    selected_vinculo = (request.GET.get("vinculo") or "").strip()
    fecha_desde_raw = request.GET.get("fecha_alta_desde", "")
    fecha_hasta_raw = request.GET.get("fecha_alta_hasta", "")
    fecha_mes = request.GET.get("fecha_alta_mes", "")
    fecha_rango = request.GET.get("fecha_alta_rango", "")
    today = timezone.localdate()

    if search_query:
        items = items.filter(
            Q(codigo_inventario__icontains=search_query)
            | Q(numero_serie__icontains=search_query)
            | Q(marca__icontains=search_query)
            | Q(modelo__icontains=search_query)
            | Q(descripcion_equipo__icontains=search_query)
            | Q(Numero_Pedimiento__icontains=search_query)
            | Q(equipo_padre__codigo_inventario__icontains=search_query)
        )
    if selected_categoria:
        items = items.filter(categoria_id=selected_categoria)
    if selected_estado:
        items = items.filter(estado_equipo=selected_estado)
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)
    if selected_sin_ubicacion == "1":
        items = _equipos_sin_ubicacion_qs(tipo=tipo)
    if selected_origen:
        items = items.filter(origen_alta=selected_origen)
    if selected_sin_oc == "1":
        items = items.filter(orden_compra__isnull=True)
    elif selected_ubicacion:
        items = items.filter(ubicacion_id=selected_ubicacion)

    if tipo == TipoCategoriaInventario.PERIFERICO:
        if selected_vinculo == "libre":
            items = items.filter(equipo_padre__isnull=True)
        elif selected_vinculo == "vinculado":
            items = items.filter(equipo_padre__isnull=False)

    if selected_alerta == "sin_ubicacion":
        items = _equipos_sin_ubicacion_qs(tipo=tipo).order_by("codigo_inventario")
    elif selected_alerta == "mant_largo":
        items = _equipos_mantenimiento_largo_qs(tipo=tipo)
    elif selected_alerta == "asignacion_antigua":
        ids = _asignaciones_antiguas_qs(today=today, tipo=tipo).values_list("equipo_id", flat=True)
        items = _equipo_queryset().filter(pk__in=ids)
        if tipo:
            items = items.filter(categoria__tipo=tipo)
        items = items.order_by("codigo_inventario")
    elif selected_alerta == "baja":
        items = items.filter(estado_equipo=EstadoEquipo.BAJA).order_by("-fecha_baja", "-pk")

    fecha_desde = _parse_date(fecha_desde_raw)
    fecha_hasta = _parse_date(fecha_hasta_raw)
    if not fecha_desde and not fecha_hasta and not selected_alerta:
        month_start, month_end = _month_bounds(fecha_mes)
        if month_start:
            fecha_desde, fecha_hasta = month_start, month_end
        else:
            range_start, range_end = _quick_range_bounds(fecha_rango)
            if range_start:
                fecha_desde, fecha_hasta = range_start, range_end
    if not selected_alerta:
        items = _apply_date_filters(items, "fecha_alta", fecha_desde, fecha_hasta)

    filters = {
        "search_query": search_query,
        "selected_categoria": selected_categoria,
        "selected_estado": selected_estado,
        "selected_activo": selected_activo,
        "selected_ubicacion": selected_ubicacion,
        "selected_sin_ubicacion": selected_sin_ubicacion,
        "selected_alerta": selected_alerta,
        "selected_origen": selected_origen,
        "selected_sin_oc": selected_sin_oc,
        "selected_vinculo": selected_vinculo,
        "origen_choices": OrigenAltaEquipo.choices,
        "fecha_alta_desde": fecha_desde_raw,
        "fecha_alta_hasta": fecha_hasta_raw,
        "fecha_alta_mes": fecha_mes,
        "fecha_alta_rango": fecha_rango,
    }
    return items, filters


def _export_equipos_csv(queryset, inv=None):
    inv = inv or get_inventario_ui(TipoCategoriaInventario.EQUIPO)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{inv["csv_filename"]}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Codigo",
            "Serie",
            "Marca",
            "Modelo",
            "Categoria",
            "Tipo",
            "Equipo padre",
            "Estado",
            "Activo",
            "Ubicacion",
            "Proveedor",
            "Pedimiento",
            "Fecha alta",
            "Fecha baja",
            "Motivo baja",
        ]
    )
    for equipo in queryset.select_related("categoria", "proveedor", "ubicacion", "equipo_padre"):
        writer.writerow(
            [
                equipo.codigo_inventario,
                equipo.numero_serie or "",
                equipo.marca or "",
                equipo.modelo or "",
                str(equipo.categoria) if equipo.categoria_id else "",
                equipo.categoria.tipo if equipo.categoria_id else "",
                equipo.equipo_padre.codigo_inventario if equipo.equipo_padre_id else "",
                equipo.estado_equipo,
                "Si" if equipo.activo else "No",
                str(equipo.ubicacion) if equipo.ubicacion_id else "",
                str(equipo.proveedor) if equipo.proveedor_id else "",
                equipo.Numero_Pedimiento or "",
                equipo.fecha_alta.isoformat() if equipo.fecha_alta else "",
                equipo.fecha_baja.isoformat() if equipo.fecha_baja else "",
                equipo.motivo_baja or "",
            ]
        )
    return response


def equipo_detalle_orden_choices(request):
    """Lineas de una OC con cupo disponible, para el combo Producto de la orden."""
    orden_id = (request.GET.get("orden_id") or "").strip()
    exclude_equipo_id = (request.GET.get("exclude_equipo_id") or "").strip()
    exclude_id = int(exclude_equipo_id) if exclude_equipo_id.isdigit() else None

    choices = []
    proveedor_id = None
    folio = ""
    if orden_id.isdigit():
        orden = (
            OrdenCompra.objects.filter(pk=orden_id)
            .prefetch_related("detalles", "detalles__equipos")
            .first()
        )
        if orden is not None:
            proveedor_id = orden.proveedor_id
            folio = orden.folio_orden or ""
            for linea in orden.detalles.all().order_by("pk"):
                disponible = linea.cantidad_disponible(exclude_equipo_id=exclude_id)
                if disponible <= 0 and not (
                    exclude_id
                    and Equipo.objects.filter(
                        pk=exclude_id, detalle_orden_id=linea.pk
                    ).exists()
                ):
                    continue
                choices.append(
                    {
                        "id": linea.pk,
                        "label": linea.etiqueta_inventario(exclude_equipo_id=exclude_id),
                        "descripcion": linea.descripcion or "",
                        "disponible": disponible,
                    }
                )

    return JsonResponse(
        {
            "choices": choices,
            "proveedor_id": proveedor_id,
            "folio": folio,
        }
    )


def equipo_list(request, tipo=None):
    tipo = resolve_inventario_tipo(tipo or TipoCategoriaInventario.EQUIPO)
    inv = _mark_inventario_nav(request, get_inventario_ui(tipo))
    items, filters = _filtrar_equipos(request, tipo=tipo)
    if (request.GET.get("export") or "").lower() == "csv":
        return _export_equipos_csv(items, inv=inv)

    paginator = Paginator(items, EQUIPO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    ubicaciones = Ubicacion.objects.select_related("edificio", "zona").order_by(
        "edificio__nombre_edificio",
        "zona__nombre_zona",
        "referencia",
    )
    context = {
        "items": page_obj,
        "page_obj": page_obj,
        "inv": inv,
        "categoria_choices": CategoriaEquipo.objects.filter(tipo=tipo)
        .order_by("nombre_categoria")
        .values_list("id", "nombre_categoria"),
        "estado_choices": EstadoEquipo.choices,
        "ubicacion_choices": [(ubicacion.pk, str(ubicacion)) for ubicacion in ubicaciones],
        "equipos_asignacion_alerta_dias": EQUIPO_ASIGNACION_ALERTA_DIAS,
        "equipos_mant_largo_dias": EQUIPO_MANTENIMIENTO_LARGO_DIAS,
        **filters,
    }
    return render(request, "equipo/list.html", context)


def equipo_detail(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    inv = _mark_inventario_nav(request, inventario_ui_for_equipo(equipo))
    asignacion_activa = _get_equipo_asignacion_activa(equipo)
    perifericos = []
    if equipo.es_equipo_principal:
        perifericos = list(equipo.perifericos_activos)
    movimientos = (
        MovimientoEquipo.objects.select_related("responsable")
        .filter(equipo=equipo)
        .order_by("-fecha_movimiento", "-pk")[:20]
    )
    asignaciones = (
        AsignacionEquipo.objects.select_related("personal")
        .filter(equipo=equipo)
        .order_by("-fecha_asignacion", "-pk")[:10]
    )
    mantenimientos = (
        Mantenimiento.objects.select_related("cierre")
        .filter(equipo=equipo)
        .order_by("-fecha_programada", "-pk")[:10]
    )
    tickets = (
        TicketIT.objects.select_related("solicitado_por", "asignado_a")
        .filter(equipo=equipo)
        .order_by("-fecha_support", "-pk")[:10]
    )
    return render(
        request,
        "equipo/detail.html",
        {
            "object": equipo,
            "inv": inv,
            "asignacion_activa": asignacion_activa,
            "perifericos": perifericos,
            "movimientos": movimientos,
            "asignaciones": asignaciones,
            "mantenimientos": mantenimientos,
            "tickets": tickets,
            "mostrar_asignacion": inv["permite_asignacion"] and not (
                equipo.es_periferico and equipo.equipo_padre_id
            ),
            "mostrar_kit": equipo.es_equipo_principal,
        },
    )


def equipo_create(request, tipo=None):
    tipo = resolve_inventario_tipo(tipo or TipoCategoriaInventario.EQUIPO)
    inv = _mark_inventario_nav(request, get_inventario_ui(tipo))
    orden = None
    detalle = None
    orden_id = (request.GET.get("orden") or request.POST.get("orden_compra") or "").strip()
    detalle_id = (request.GET.get("detalle") or "").strip()

    if orden_id.isdigit():
        orden = OrdenCompra.objects.filter(pk=orden_id).prefetch_related(
            "detalles", "detalles__equipos"
        ).first()
        if orden is None:
            messages.error(request, "Orden de compra no encontrada.")
            return redirect("ordencompra_list")
        if not orden.lista_para_inventario:
            messages.error(
                request,
                "La orden debe estar en Terminado y tener lineas para dar de alta equipos.",
            )
            return redirect("ordencompra_update", pk=orden.pk)
        if not orden.puede_recibir_equipos:
            messages.error(
                request,
                "Esta orden ya no tiene productos disponibles: todas las lineas estan cubiertas.",
            )
            return redirect("ordencompra_update", pk=orden.pk)

    if detalle_id.isdigit():
        detalle = DetalleOrdenCompra.objects.filter(pk=detalle_id).select_related("orden").prefetch_related("equipos").first()
        if detalle and orden and detalle.orden_id != orden.pk:
            messages.error(request, "La linea no pertenece a la orden indicada.")
            return redirect(inv["create_url"])
        if detalle and orden is None:
            orden = detalle.orden
            if not orden.lista_para_inventario:
                messages.error(
                    request,
                    "La orden debe estar en Terminado y tener lineas para dar de alta equipos.",
                )
                return redirect("ordencompra_update", pk=orden.pk)
        if detalle and detalle.cantidad_disponible() <= 0:
            messages.error(
                request,
                f"La linea '{detalle.descripcion}' ya no tiene cupo disponible "
                f"({detalle.cantidad_recibida()}/{detalle.cantidad_esperada}).",
            )
            return redirect("ordencompra_update", pk=detalle.orden_id)

    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES, tipo=tipo)
        if form.is_valid():
            equipo = form.save()
            _reconciliar_estado_equipo(equipo)
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.EQUIPO,
                titulo=f"{inv['singular_title']} dado de alta: {equipo.codigo_inventario}",
                objeto=equipo,
                enlace_nombre="equipo_detail",
                metadata={
                    "origen_alta": equipo.origen_alta,
                    "orden_compra_id": equipo.orden_compra_id,
                    "detalle_orden_id": equipo.detalle_orden_id,
                    "tipo_inventario": tipo,
                },
            )
            _crear_movimiento(
                equipo,
                TipoMovimiento.DADA_DE_ALTA,
                origen=None,
                destino=equipo.ubicacion,
                responsable=_get_equipo_responsable(equipo),
                request=request,
            )
            messages.success(request, f"{inv['singular_title']} creado correctamente.")
            return redirect("equipo_detail", pk=equipo.pk)
    else:
        initial = {}
        if orden is not None:
            initial = {
                "origen_alta": OrigenAltaEquipo.COMPRA,
                "orden_compra": orden,
                "proveedor": orden.proveedor_id,
                "Numero_Pedimiento": (orden.folio_orden or "")[:15] or None,
            }
            if detalle is not None:
                initial["detalle_orden"] = detalle
                initial["descripcion_equipo"] = (detalle.descripcion or "")[:255]
        else:
            initial = {"origen_alta": OrigenAltaEquipo.LEGADO}
        stock = _get_espacio_stock_default()
        if stock:
            initial["ubicacion"] = stock
        form = EquipoForm(initial=initial, tipo=tipo)

    return render(
        request,
        "equipo/form.html",
        {
            "form": form,
            "inv": inv,
            "orden_vinculada": orden,
            "detalle_vinculado": detalle,
        },
    )


def equipo_update(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    inv = _mark_inventario_nav(request, inventario_ui_for_equipo(equipo))
    tipo = equipo.tipo_inventario
    ubicacion_anterior = equipo.ubicacion
    estado_anterior = equipo.estado_equipo
    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES, instance=equipo, tipo=tipo)
        if form.is_valid():
            equipo = form.save()
            _reconciliar_estado_equipo(equipo)
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.EQUIPO,
                titulo=f"{inv['singular_title']} actualizado: {equipo.codigo_inventario}",
                objeto=equipo,
                form=form,
                enlace_nombre="equipo_detail",
            )
            movimiento_creado = False
            if (
                estado_anterior != equipo.estado_equipo
                and equipo.estado_equipo == EstadoEquipo.EN_MANTENIMIENTO
            ):
                _crear_movimiento(
                    equipo,
                    TipoMovimiento.MANTENIMIENTO,
                    origen=equipo.ubicacion,
                    destino=equipo.ubicacion,
                    responsable=_get_equipo_responsable(equipo),
                    request=request,
                )
                movimiento_creado = True

            if not movimiento_creado and ubicacion_anterior != equipo.ubicacion:
                _crear_movimiento(
                    equipo,
                    TipoMovimiento.CAMBIO_UBICACION,
                    origen=ubicacion_anterior,
                    destino=equipo.ubicacion,
                    responsable=_get_equipo_responsable(equipo),
                    request=request,
                )
            messages.success(request, f"{inv['singular_title']} actualizado correctamente.")
            return redirect("equipo_detail", pk=equipo.pk)
    else:
        form = EquipoForm(instance=equipo, tipo=tipo)
    return render(
        request,
        "equipo/form.html",
        {"form": form, "object": equipo, "inv": inv},
    )


def equipo_delete(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    inv = _mark_inventario_nav(request, inventario_ui_for_equipo(equipo))
    if not equipo.puede_eliminar_fisico:
        messages.error(
            request,
            "No se puede eliminar: el registro tiene historial (asignaciones, "
            "mantenimientos, tickets o movimientos). Usa Dar de baja.",
        )
        return redirect("equipo_detail", pk=pk)

    if request.method == "POST":
        etiqueta = equipo.codigo_inventario
        list_url = inv["list_url"]
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.EQUIPO,
            titulo=f"{inv['singular_title']} eliminado: {etiqueta}",
            objeto=equipo,
            metadata={"codigo_inventario": etiqueta, "tipo_inventario": equipo.tipo_inventario},
            nivel=NivelHistorial.CRITICO,
        )
        equipo.delete()
        messages.success(request, f"{inv['singular_title']} eliminado correctamente.")
        return redirect(list_url)
    return render(
        request,
        "equipo/confirm_delete.html",
        {"object": equipo, "inv": inv, "puede_eliminar": True},
    )


def equipo_dar_baja(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    if not equipo.puede_dar_de_baja:
        messages.error(
            request,
            "No se puede dar de baja: ya esta en Baja o En Mantenimiento "
            "(cierra el mantenimiento primero).",
        )
        return redirect("equipo_detail", pk=pk)

    if request.method == "POST":
        form = EquipoBajaForm(request.POST)
        if form.is_valid():
            _cerrar_asignaciones_activas(
                equipo,
                observaciones="Cerrada automaticamente por baja del equipo.",
            )
            equipo.estado_equipo = EstadoEquipo.BAJA
            equipo.activo = False
            equipo.fecha_baja = form.cleaned_data["fecha_baja"]
            equipo.motivo_baja = form.cleaned_data["motivo_baja"]
            equipo.save(
                update_fields=[
                    "estado_equipo",
                    "activo",
                    "fecha_baja",
                    "motivo_baja",
                ]
            )
            _crear_movimiento(
                equipo,
                TipoMovimiento.DADA_DE_BAJA,
                origen=equipo.ubicacion,
                destino=None,
                responsable=_get_equipo_responsable(equipo),
                observaciones=equipo.motivo_baja,
                request=request,
            )
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.EQUIPO,
                accion=AccionHistorial.CAMBIO_ESTADO,
                titulo=f"Equipo dado de baja: {equipo.codigo_inventario}",
                objeto=equipo,
                enlace_nombre="equipo_detail",
                enlace_pk=equipo.pk,
                nivel=NivelHistorial.ADVERTENCIA,
                metadata={
                    "estado": equipo.estado_equipo,
                    "fecha_baja": equipo.fecha_baja.isoformat(),
                    "motivo_baja": equipo.motivo_baja,
                },
            )
            messages.success(request, f"{equipo.codigo_inventario} dado de baja.")
            return redirect("equipo_detail", pk=pk)
    else:
        form = EquipoBajaForm()

    return render(
        request,
        "equipo/baja.html",
        {"object": equipo, "form": form},
    )


def equipo_reactivar(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    if request.method != "POST":
        return redirect("equipo_detail", pk=pk)
    if not equipo.puede_reactivar:
        messages.error(request, "Solo se pueden reactivar equipos en Baja.")
        return redirect("equipo_detail", pk=pk)

    equipo.activo = True
    equipo.fecha_baja = None
    equipo.motivo_baja = None
    equipo.estado_equipo = EstadoEquipo.DISPONIBLE
    equipo.save(
        update_fields=["activo", "fecha_baja", "motivo_baja", "estado_equipo"]
    )
    _reconciliar_estado_equipo(equipo)
    _crear_movimiento(
        equipo,
        TipoMovimiento.DADA_DE_ALTA,
        origen=None,
        destino=equipo.ubicacion,
        responsable=_get_equipo_responsable(equipo),
        observaciones="Reactivacion de equipo en Baja.",
        request=request,
    )
    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.EQUIPO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Equipo reactivado: {equipo.codigo_inventario}",
        objeto=equipo,
        enlace_nombre="equipo_detail",
        enlace_pk=equipo.pk,
        metadata={"estado": equipo.estado_equipo},
    )
    messages.success(request, f"{equipo.codigo_inventario} reactivado.")
    return redirect("equipo_detail", pk=pk)


def equipo_devolver(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    if request.method != "POST":
        return redirect("equipo_detail", pk=pk)
    asignacion = _get_equipo_asignacion_activa(equipo)
    if not asignacion:
        messages.error(request, "No hay asignacion activa para devolver.")
        return redirect("equipo_detail", pk=pk)

    personal = asignacion.personal
    asignacion.estado_asignacion = EstadoAsignacion.DEVUELTA
    asignacion.fecha_devolucion = timezone.now()
    asignacion.save(update_fields=["estado_asignacion", "fecha_devolucion"])
    _reconciliar_estado_equipo(equipo)
    ubicacion_anterior, ubicacion_nueva = _liberar_equipo_tras_devolucion(
        equipo, request=request
    )
    _crear_movimiento(
        equipo,
        TipoMovimiento.CAMBIO_ASIGNACION,
        origen=ubicacion_anterior,
        destino=ubicacion_nueva,
        responsable=personal,
        observaciones=f"Devolucion de {personal}.",
        request=request,
    )
    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.ASIGNACION,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Devolucion: {equipo.codigo_inventario} / {personal}",
        objeto=asignacion,
        entidad_relacionada=equipo,
        enlace_nombre="equipo_detail",
        enlace_pk=equipo.pk,
    )
    messages.success(request, f"Equipo devuelto por {personal}.")
    return redirect("equipo_detail", pk=pk)


def equipo_asignar(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    if not equipo.puede_asignarse:
        messages.error(
            request,
            "No se puede asignar: solo maquinas principales (Equipos). "
            "Perifericos van en el kit; herramientas no se asignan.",
        )
        return redirect("equipo_detail", pk=pk)

    if request.method == "POST":
        form = EquipoAsignarForm(request.POST)
        if form.is_valid():
            personal = form.cleaned_data["personal"]
            observaciones = form.cleaned_data.get("observaciones") or ""
            existente = _get_equipo_asignacion_activa(equipo)
            if existente:
                _cerrar_asignaciones_activas(
                    equipo,
                    observaciones="Cerrada automaticamente por reasignacion.",
                )
            asignacion = AsignacionEquipo.objects.create(
                equipo=equipo,
                personal=personal,
                estado_asignacion=EstadoAsignacion.ACTIVA,
                observaciones=observaciones or None,
            )
            _reconciliar_estado_equipo(equipo)
            ubicacion_anterior, ubicacion_nueva = _aplicar_asignacion_a_equipo(
                equipo, personal, request=request
            )
            _crear_movimiento(
                equipo,
                TipoMovimiento.CAMBIO_ASIGNACION if existente else TipoMovimiento.ASIGNACION,
                origen=ubicacion_anterior,
                destino=ubicacion_nueva,
                responsable=personal,
                observaciones=observaciones or None,
                request=request,
            )
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.ASIGNACION,
                accion=AccionHistorial.ASIGNACION,
                titulo=f"Asignacion de {equipo} a {personal}",
                objeto=asignacion,
                entidad_relacionada=equipo,
                enlace_nombre="equipo_detail",
                enlace_pk=equipo.pk,
            )
            messages.success(request, f"Equipo asignado a {personal}.")
            return redirect("equipo_detail", pk=pk)
    else:
        form = EquipoAsignarForm()

    personal_resumen = list(
        Personal.objects.filter(activo=True)
        .select_related("area", "ubicacion", "ubicacion__edificio", "ubicacion__zona")
        .order_by("nombre", "apellido_paterno")
        .values(
            "id",
            "area__nombre_area",
            "ubicacion__referencia",
            "ubicacion__pasillo",
            "ubicacion__edificio__nombre_edificio",
            "ubicacion__zona__nombre_zona",
        )
    )

    return render(
        request,
        "equipo/asignar.html",
        {"object": equipo, "form": form, "personal_resumen": personal_resumen},
    )


def equipo_cambiar_ubicacion(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    if not equipo.puede_cambiar_ubicacion:
        messages.error(request, "No se puede cambiar ubicacion de un equipo en Baja.")
        return redirect("equipo_detail", pk=pk)

    if request.method == "POST":
        form = EquipoUbicacionForm(request.POST, equipo=equipo)
        if form.is_valid():
            ubicacion_anterior = equipo.ubicacion
            nueva = form.cleaned_data.get("ubicacion")
            observaciones = form.cleaned_data.get("observaciones") or ""
            if ubicacion_anterior == nueva:
                messages.info(request, "La ubicacion no cambio.")
                return redirect("equipo_detail", pk=pk)
            equipo.ubicacion = nueva
            equipo.save(update_fields=["ubicacion"])
            _sync_perifericos_con_padre(equipo, request=request)
            _crear_movimiento(
                equipo,
                TipoMovimiento.CAMBIO_UBICACION,
                origen=ubicacion_anterior,
                destino=nueva,
                responsable=_get_equipo_responsable(equipo),
                observaciones=observaciones or None,
                request=request,
            )
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.EQUIPO,
                accion=AccionHistorial.ACTUALIZACION,
                titulo=f"Cambio de ubicacion: {equipo.codigo_inventario}",
                objeto=equipo,
                enlace_nombre="equipo_detail",
                enlace_pk=equipo.pk,
                metadata={
                    "origen": str(ubicacion_anterior) if ubicacion_anterior else None,
                    "destino": str(nueva) if nueva else None,
                },
            )
            messages.success(request, "Ubicacion actualizada.")
            return redirect("equipo_detail", pk=pk)
    else:
        form = EquipoUbicacionForm(equipo=equipo)

    return render(
        request,
        "equipo/ubicacion.html",
        {"object": equipo, "form": form},
    )


def equipo_vincular_periferico(request, pk):
    """Desde un equipo: agregar periferico libre al kit."""
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    inv = _mark_inventario_nav(request, inventario_ui_for_equipo(equipo))
    if not equipo.puede_vincular_perifericos:
        messages.error(request, "Este equipo no puede recibir perifericos.")
        return redirect("equipo_detail", pk=pk)

    if request.method == "POST":
        form = EquipoVincularPerifericoForm(request.POST)
        if form.is_valid():
            periferico = form.cleaned_data["periferico"]
            obs = form.cleaned_data.get("observaciones") or ""
            try:
                _vincular_periferico_a_equipo(
                    periferico,
                    equipo,
                    request=request,
                    observaciones=obs or None,
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
            else:
                messages.success(
                    request,
                    f"{periferico.codigo_inventario} vinculado a {equipo.codigo_inventario}.",
                )
                return redirect("equipo_detail", pk=pk)
    else:
        form = EquipoVincularPerifericoForm()

    return render(
        request,
        "equipo/vincular_periferico.html",
        {
            "object": equipo,
            "form": form,
            "inv": inv,
            "modo": "desde_equipo",
        },
    )


def periferico_vincular_equipo(request, pk):
    """Desde un periferico libre: elegir equipo padre."""
    periferico = get_object_or_404(_equipo_queryset(), pk=pk)
    inv = _mark_inventario_nav(request, inventario_ui_for_equipo(periferico))
    if not periferico.puede_vincularse_a_equipo:
        messages.error(
            request,
            "Este periferico no se puede vincular (ya tiene padre, baja o mantenimiento).",
        )
        return redirect("equipo_detail", pk=pk)

    if request.method == "POST":
        form = PerifericoVincularEquipoForm(request.POST)
        if form.is_valid():
            padre = form.cleaned_data["equipo_padre"]
            obs = form.cleaned_data.get("observaciones") or ""
            try:
                _vincular_periferico_a_equipo(
                    periferico,
                    padre,
                    request=request,
                    observaciones=obs or None,
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
            else:
                messages.success(
                    request,
                    f"{periferico.codigo_inventario} vinculado a {padre.codigo_inventario}.",
                )
                return redirect("equipo_detail", pk=padre.pk)
    else:
        form = PerifericoVincularEquipoForm()

    return render(
        request,
        "equipo/vincular_periferico.html",
        {
            "object": periferico,
            "form": form,
            "inv": inv,
            "modo": "desde_periferico",
        },
    )


def periferico_desvincular(request, pk):
    periferico = get_object_or_404(_equipo_queryset(), pk=pk)
    inv = _mark_inventario_nav(request, inventario_ui_for_equipo(periferico))
    if not periferico.puede_desvincularse:
        messages.error(request, "Este periferico no esta vinculado o no se puede desvincular.")
        return redirect("equipo_detail", pk=pk)

    padre = periferico.equipo_padre
    if request.method == "POST":
        form = PerifericoDesvincularForm(request.POST)
        if form.is_valid():
            obs = form.cleaned_data.get("observaciones") or ""
            try:
                _desvincular_periferico(
                    periferico,
                    request=request,
                    observaciones=obs or None,
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
                return redirect("equipo_detail", pk=pk)
            messages.success(
                request,
                f"{periferico.codigo_inventario} desvinculado del kit.",
            )
            return redirect("equipo_detail", pk=padre.pk if padre else pk)
    else:
        form = PerifericoDesvincularForm()

    return render(
        request,
        "equipo/desvincular_periferico.html",
        {
            "object": periferico,
            "padre": padre,
            "form": form,
            "inv": inv,
        },
    )


def periferico_reemplazar(request, pk):
    periferico = get_object_or_404(_equipo_queryset(), pk=pk)
    inv = _mark_inventario_nav(request, inventario_ui_for_equipo(periferico))
    if not periferico.puede_desvincularse:
        messages.error(request, "Solo se pueden reemplazar perifericos vinculados al kit.")
        return redirect("equipo_detail", pk=pk)

    padre = periferico.equipo_padre
    if request.method == "POST":
        form = PerifericoReemplazarForm(request.POST, periferico_actual=periferico)
        if form.is_valid():
            nuevo = form.cleaned_data["periferico_nuevo"]
            motivo = form.cleaned_data.get("motivo") or ""
            try:
                _reemplazar_periferico(
                    periferico,
                    nuevo,
                    request=request,
                    motivo=motivo or None,
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
            else:
                messages.success(
                    request,
                    f"Reemplazo: {periferico.codigo_inventario} → {nuevo.codigo_inventario}.",
                )
                return redirect("equipo_detail", pk=padre.pk)
    else:
        form = PerifericoReemplazarForm(periferico_actual=periferico)

    return render(
        request,
        "equipo/reemplazar_periferico.html",
        {
            "object": periferico,
            "padre": padre,
            "form": form,
            "inv": inv,
        },
    )
