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
from django.utils.http import urlencode
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
    _get_espacio_stock_default,
    _month_bounds,
    _ordenes_for_user,
    _parse_date,
    _quick_range_bounds,
    _reconciliar_estado_equipo,
    _set_espacio_stock_default,
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

def _parse_int_param(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mapa_sedes_url(*, edificio=None, sector=None, espacio=None, activo=None, q=None):
    params = {}
    if edificio:
        params["edificio"] = edificio
    if sector:
        params["sector"] = sector
    if espacio:
        params["espacio"] = espacio
    if activo:
        params["activo"] = activo
    if q:
        params["q"] = q
    base = reverse("mapa_sedes")
    if not params:
        return base
    return f"{base}?{urlencode(params)}"


def _zona_referencias(zona):
    refs = []
    n_ubi = Ubicacion.objects.filter(zona=zona).count()
    if n_ubi:
        refs.append(f"{n_ubi} espacio(s) fisico(s)")
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


def _split_lines(value):
    if not value:
        return []
    items = []
    for raw in str(value).replace(",", "\n").splitlines():
        name = raw.strip()
        if name:
            items.append(name)
    return items


def _crear_espacios_en_sector(edificio, sector, referencias, marcar_stock=False):
    creados = []
    for ref in referencias:
        espacio = Ubicacion.objects.create(
            edificio=edificio,
            zona=sector,
            referencia=ref[:255],
            activo=True,
            es_stock_default=False,
        )
        creados.append(espacio)
    if marcar_stock and creados:
        _set_espacio_stock_default(creados[0])
    return creados


def _handle_mapa_sedes_post(request):
    accion = (request.POST.get("accion") or "").strip()

    if accion == "plantilla_rapida":
        nombre = (request.POST.get("nombre_edificio") or "").strip()
        sectores = _split_lines(request.POST.get("sectores"))
        espacios_texto = (request.POST.get("espacios") or "").strip()
        espacios_n = _parse_int_param(request.POST.get("espacios_por_sector")) or 0
        incluir_almacen = request.POST.get("incluir_almacen") == "1"
        marcar_stock = request.POST.get("marcar_stock") == "1"

        if not nombre:
            messages.error(request, "Captura el nombre del edificio o sede.")
            return redirect("mapa_sedes")
        if Edificio.objects.filter(nombre_edificio__iexact=nombre).exists():
            messages.error(request, f'Ya existe un edificio llamado "{nombre}".')
            return redirect("mapa_sedes")

        with transaction.atomic():
            edificio = Edificio.objects.create(
                nombre_edificio=nombre[:100],
                activo=True,
            )
            if not sectores:
                sectores = ["Piso 1"]
            if incluir_almacen and "Almacen" not in sectores and "Almacén" not in sectores:
                sectores.append("Almacen")

            refs_base = _split_lines(espacios_texto)
            if not refs_base and espacios_n > 0:
                refs_base = [f"Espacio {i}" for i in range(1, espacios_n + 1)]

            stock_espacio = None
            first_sector = None
            for nombre_sector in sectores:
                sector = ZonaEdificio.objects.create(
                    edificio=edificio,
                    nombre_zona=nombre_sector[:100],
                    activo=True,
                )
                if first_sector is None:
                    first_sector = sector
                es_almacen = nombre_sector.lower() in {"almacen", "almacén", "bodega", "stock"}
                if es_almacen:
                    refs = refs_base or ["Stock principal"]
                    creados = _crear_espacios_en_sector(
                        edificio, sector, refs, marcar_stock=marcar_stock
                    )
                    if marcar_stock and creados:
                        stock_espacio = creados[0]
                elif refs_base:
                    _crear_espacios_en_sector(edificio, sector, refs_base)

            if marcar_stock and stock_espacio is None:
                sector_stock = ZonaEdificio.objects.create(
                    edificio=edificio,
                    nombre_zona="Almacen",
                    activo=True,
                )
                creados = _crear_espacios_en_sector(
                    edificio, sector_stock, ["Stock principal"], marcar_stock=True
                )
                stock_espacio = creados[0] if creados else None
                first_sector = first_sector or sector_stock

        messages.success(
            request,
            f'Sede "{edificio.nombre_edificio}" creada'
            + (" con almacén de stock." if stock_espacio else "."),
        )
        return redirect(
            _mapa_sedes_url(
                edificio=edificio.pk,
                sector=first_sector.pk if first_sector else None,
                espacio=stock_espacio.pk if stock_espacio else None,
            )
        )

    if accion == "crear_edificio":
        nombre = (request.POST.get("nombre_edificio") or "").strip()
        if not nombre:
            messages.error(request, "Captura el nombre del edificio.")
            return redirect("mapa_sedes")
        edificio = Edificio.objects.create(nombre_edificio=nombre[:100], activo=True)
        messages.success(request, "Edificio creado.")
        return redirect(_mapa_sedes_url(edificio=edificio.pk))

    if accion == "crear_sector":
        edificio_id = _parse_int_param(request.POST.get("edificio"))
        nombre = (request.POST.get("nombre_sector") or "").strip()
        edificio = Edificio.objects.filter(pk=edificio_id).first()
        if not edificio or not nombre:
            messages.error(request, "Indica edificio y nombre del sector.")
            return redirect(_mapa_sedes_url(edificio=edificio_id))
        sector = ZonaEdificio.objects.create(
            edificio=edificio,
            nombre_zona=nombre[:100],
            activo=True,
        )
        messages.success(request, "Sector creado.")
        return redirect(_mapa_sedes_url(edificio=edificio.pk, sector=sector.pk))

    if accion == "crear_espacios":
        sector_id = _parse_int_param(request.POST.get("sector"))
        sector = (
            ZonaEdificio.objects.select_related("edificio").filter(pk=sector_id).first()
        )
        refs = _split_lines(request.POST.get("espacios"))
        marcar_stock = request.POST.get("marcar_stock") == "1"
        if not sector or not refs:
            messages.error(request, "Indica sector y al menos un espacio (uno por linea).")
            return redirect(_mapa_sedes_url(edificio=sector.edificio_id if sector else None, sector=sector_id))
        creados = _crear_espacios_en_sector(
            sector.edificio, sector, refs, marcar_stock=marcar_stock
        )
        messages.success(request, f"{len(creados)} espacio(s) fisico(s) creado(s).")
        destino = creados[0] if len(creados) == 1 else None
        return redirect(
            _mapa_sedes_url(
                edificio=sector.edificio_id,
                sector=sector.pk,
                espacio=destino.pk if destino else None,
            )
        )

    if accion == "marcar_stock":
        espacio_id = _parse_int_param(request.POST.get("espacio"))
        espacio = Ubicacion.objects.filter(pk=espacio_id).first()
        if not espacio:
            messages.error(request, "Espacio no encontrado.")
            return redirect("mapa_sedes")
        _set_espacio_stock_default(espacio)
        messages.success(request, f'"{espacio}" es ahora el almacén / stock por defecto.')
        return redirect(
            _mapa_sedes_url(
                edificio=espacio.edificio_id,
                sector=espacio.zona_id,
                espacio=espacio.pk,
            )
        )

    messages.error(request, "Accion no reconocida.")
    return redirect("mapa_sedes")


def mapa_sedes(request):
    if request.method == "POST":
        return _handle_mapa_sedes_post(request)

    show_all = request.GET.get("activo") == "all"
    search_q = (request.GET.get("q") or "").strip()

    sel_edificio = _parse_int_param(request.GET.get("edificio"))
    sel_sector = _parse_int_param(request.GET.get("sector"))
    sel_espacio = _parse_int_param(request.GET.get("espacio"))

    edificios_qs = Edificio.objects.order_by("nombre_edificio")
    if not show_all:
        edificios_qs = edificios_qs.filter(activo=True)

    zonas_qs = ZonaEdificio.objects.select_related("edificio").order_by(
        "edificio__nombre_edificio", "nombre_zona"
    )
    if not show_all:
        zonas_qs = zonas_qs.filter(activo=True)

    ubicaciones_qs = Ubicacion.objects.select_related("edificio", "zona").order_by(
        "edificio__nombre_edificio", "zona__nombre_zona", "referencia", "pasillo"
    )
    if not show_all:
        ubicaciones_qs = ubicaciones_qs.filter(activo=True)
    if search_q:
        ubicaciones_qs = ubicaciones_qs.filter(
            Q(referencia__icontains=search_q)
            | Q(pasillo__icontains=search_q)
            | Q(edificio__nombre_edificio__icontains=search_q)
            | Q(zona__nombre_zona__icontains=search_q)
        )

    zonas_by_edificio = {}
    for zona in zonas_qs:
        zonas_by_edificio.setdefault(zona.edificio_id, []).append(zona)

    espacios_by_sector = {}
    for espacio in ubicaciones_qs:
        espacios_by_sector.setdefault(espacio.zona_id, []).append(espacio)

    equipo_por_espacio = dict(
        Equipo.objects.filter(
            activo=True,
            ubicacion_id__isnull=False,
        )
        .exclude(estado_equipo=EstadoEquipo.BAJA)
        .values("ubicacion_id")
        .annotate(n=Count("id"))
        .values_list("ubicacion_id", "n")
    )

    panel = None
    panel_type = None
    panel_espacios = []
    panel_equipos = 0

    if sel_espacio:
        panel = get_object_or_404(
            Ubicacion.objects.select_related("edificio", "zona"), pk=sel_espacio
        )
        panel_type = "espacio"
        sel_sector = panel.zona_id
        sel_edificio = panel.edificio_id
        panel_equipos = equipo_por_espacio.get(panel.pk, 0)
    elif sel_sector:
        panel = get_object_or_404(
            ZonaEdificio.objects.select_related("edificio"), pk=sel_sector
        )
        panel_type = "sector"
        sel_edificio = panel.edificio_id
        panel_espacios = [
            {
                "espacio": espacio,
                "equipos": equipo_por_espacio.get(espacio.pk, 0),
            }
            for espacio in espacios_by_sector.get(panel.pk, [])
        ]
        panel_equipos = sum(row["equipos"] for row in panel_espacios)
    elif sel_edificio:
        panel = get_object_or_404(Edificio, pk=sel_edificio)
        panel_type = "edificio"
        sectores = zonas_by_edificio.get(panel.pk, [])
        for sector in sectores:
            for espacio in espacios_by_sector.get(sector.pk, []):
                panel_equipos += equipo_por_espacio.get(espacio.pk, 0)

    tree = []
    for edificio in edificios_qs:
        sectores = []
        for sector in zonas_by_edificio.get(edificio.pk, []):
            espacios = espacios_by_sector.get(sector.pk, [])
            if search_q and not espacios and sel_edificio != edificio.pk:
                continue
            sectores.append({"sector": sector, "espacios": espacios})
        if search_q and not sectores and sel_edificio != edificio.pk:
            continue
        tree.append({"edificio": edificio, "sectores": sectores})

    stock_default = _get_espacio_stock_default()
    total_edificios = len(tree)
    total_sectores = sum(len(node["sectores"]) for node in tree)
    total_espacios = sum(
        len(item["espacios"]) for node in tree for item in node["sectores"]
    )
    panel_sectores = []
    if panel_type == "edificio" and panel:
        for sector in zonas_by_edificio.get(panel.pk, []):
            espacios = espacios_by_sector.get(sector.pk, [])
            panel_sectores.append(
                {
                    "sector": sector,
                    "espacios_count": len(espacios),
                    "equipos": sum(
                        equipo_por_espacio.get(espacio.pk, 0) for espacio in espacios
                    ),
                }
            )

    return render(
        request,
        "espacios/mapa_sedes.html",
        {
            "tree": tree,
            "panel": panel,
            "panel_type": panel_type,
            "panel_espacios": panel_espacios,
            "panel_sectores": panel_sectores,
            "panel_equipos": panel_equipos,
            "equipo_por_espacio": equipo_por_espacio,
            "sel_edificio": sel_edificio,
            "sel_sector": sel_sector,
            "sel_espacio": sel_espacio,
            "selected_activo": "all" if show_all else "active",
            "search_q": search_q,
            "stock_default": stock_default,
            "total_edificios": total_edificios,
            "total_sectores": total_sectores,
            "total_espacios": total_espacios,
            "mapa_vacio": total_edificios == 0,
        },
    )


def edificio_list(request):
    return redirect("mapa_sedes")


def edificio_create(request):
    if request.method == "POST":
        form = EdificioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Edificio creado correctamente.")
            return redirect(_mapa_sedes_url(edificio=form.instance.pk))
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
            return redirect(_mapa_sedes_url(edificio=edificio.pk))
    else:
        form = EdificioForm(instance=edificio)
    return render(request, "edificio/form.html", {"form": form, "object": edificio})


@require_POST
def edificio_toggle_activo(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    return _toggle_activo_and_redirect(
        request, edificio, "mapa_sedes", "Edificio"
    )


def edificio_delete(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    # Solo ubicaciones bloquean (PROTECT). Las zonas sin ubicacion si se pueden cascader.
    n_ubi = Ubicacion.objects.filter(edificio=edificio).count()
    referencias = []
    if n_ubi:
        referencias.append(f"{n_ubi} espacio(s) fisico(s)")
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
                    f'Edificio "{edificio}" desactivado. Conserva sectores y espacios fisicos.',
                )
            else:
                messages.info(request, "El edificio ya estaba inactivo.")
            return redirect(_mapa_sedes_url(edificio=edificio.pk))

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
        return redirect("mapa_sedes")

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
    return redirect("mapa_sedes")


def zonaedificio_create(request):
    if request.method == "POST":
        form = ZonaEdificioForm(request.POST)
        if form.is_valid():
            sector = form.save()
            messages.success(request, "Sector creado correctamente.")
            return redirect(
                _mapa_sedes_url(edificio=sector.edificio_id, sector=sector.pk)
            )
    else:
        form = ZonaEdificioForm()
        edificio_id = _parse_int_param(request.GET.get("edificio"))
        if edificio_id:
            form.fields["edificio"].initial = edificio_id
    return render(request, "zonaedificio/form.html", {"form": form})


def zonaedificio_update(request, pk):
    zona = get_object_or_404(ZonaEdificio, pk=pk)
    if request.method == "POST":
        form = ZonaEdificioForm(request.POST, instance=zona)
        if form.is_valid():
            sector = form.save()
            messages.success(request, "Sector actualizado correctamente.")
            return redirect(
                _mapa_sedes_url(edificio=sector.edificio_id, sector=sector.pk)
            )
    else:
        form = ZonaEdificioForm(instance=zona)
    return render(request, "zonaedificio/form.html", {"form": form, "object": zona})


@require_POST
def zonaedificio_toggle_activo(request, pk):
    zona = get_object_or_404(ZonaEdificio, pk=pk)
    return _toggle_activo_and_redirect(request, zona, "mapa_sedes", "Sector")


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
                    f'Sector "{zona}" desactivado. Conserva los espacios fisicos vinculados.',
                )
            else:
                messages.info(request, "El sector ya estaba inactivo.")
            return redirect(_mapa_sedes_url(edificio=zona.edificio_id, sector=zona.pk))

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
            edificio_id = zona.edificio_id
            zona.delete()
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar: hay espacios fisicos que lo referencian. "
                "Desactivalo en su lugar.",
            )
            return redirect("zonaedificio_delete", pk=pk)

        messages.success(request, f'Sector "{nombre}" eliminado correctamente.')
        return redirect(_mapa_sedes_url(edificio=edificio_id))

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
    return redirect("mapa_sedes")


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
            espacio = form.save()
            messages.success(request, "Espacio fisico creado correctamente.")
            return redirect(
                _mapa_sedes_url(
                    edificio=espacio.edificio_id,
                    sector=espacio.zona_id,
                    espacio=espacio.pk,
                )
            )
    else:
        form = UbicacionForm()
        edificio_id = _parse_int_param(request.GET.get("edificio"))
        sector_id = _parse_int_param(request.GET.get("sector"))
        if edificio_id:
            form.fields["edificio"].initial = edificio_id
        if sector_id:
            form.fields["zona"].initial = sector_id
            if edificio_id:
                form.fields["zona"].queryset = ZonaEdificio.objects.filter(
                    edificio_id=edificio_id,
                    activo=True,
                ).order_by("nombre_zona")
    return render(request, "ubicacion/form.html", {"form": form})


def ubicacion_update(request, pk):
    ubicacion = get_object_or_404(Ubicacion, pk=pk)
    if request.method == "POST":
        form = UbicacionForm(request.POST, instance=ubicacion)
        if form.is_valid():
            espacio = form.save()
            messages.success(request, "Espacio fisico actualizado correctamente.")
            return redirect(
                _mapa_sedes_url(
                    edificio=espacio.edificio_id,
                    sector=espacio.zona_id,
                    espacio=espacio.pk,
                )
            )
    else:
        form = UbicacionForm(instance=ubicacion)
    return render(request, "ubicacion/form.html", {"form": form, "object": ubicacion})


def ubicacion_delete(request, pk):
    ubicacion = get_object_or_404(Ubicacion, pk=pk)
    if request.method == "POST":
        edificio_id = ubicacion.edificio_id
        sector_id = ubicacion.zona_id
        ubicacion.delete()
        messages.success(request, "Espacio fisico eliminado correctamente.")
        return redirect(_mapa_sedes_url(edificio=edificio_id, sector=sector_id))
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
