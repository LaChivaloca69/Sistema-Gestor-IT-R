"""Plantillas y órdenes de compra."""
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
from ..forms.compras import (
    DetalleOrdenCompraCapturaFormSet,
    DetalleOrdenCompraFormSet,
    OrdenCompraCrearForm,
    OrdenCompraSubirForm,
    PlantillaDocumentoForm,
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


def plantilla_list(request):
    items = PlantillaDocumento.objects.all()
    return render(request, "plantilladocumento/list.html", {"items": items})


def plantilla_create(request):
    if request.method == "POST":
        form = PlantillaDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Plantilla creada correctamente.")
            return redirect("plantilla_list")
    else:
        form = PlantillaDocumentoForm()
    return render(request, "plantilladocumento/form.html", {"form": form})


def plantilla_update(request, pk):
    plantilla = get_object_or_404(PlantillaDocumento, pk=pk)
    if request.method == "POST":
        form = PlantillaDocumentoForm(request.POST, request.FILES, instance=plantilla)
        if form.is_valid():
            form.save()
            messages.success(request, "Plantilla actualizada correctamente.")
            return redirect("plantilla_list")
    else:
        form = PlantillaDocumentoForm(instance=plantilla)
    return render(request, "plantilladocumento/form.html", {"form": form, "object": plantilla})


def plantilla_delete(request, pk):
    plantilla = get_object_or_404(PlantillaDocumento, pk=pk)
    if request.method == "POST":
        plantilla.delete()
        messages.success(request, "Plantilla eliminada correctamente.")
        return redirect("plantilla_list")
    return render(request, "plantilladocumento/confirm_delete.html", {"object": plantilla})


def _proveedores_payload():
    return [
        {
            "id": p.pk,
            "nombre": p.nombre_proveedor or "",
            "razon_social": p.razon_social or "",
            "rfc": p.rfc or "",
            "codigo": p.codigo_interno or "",
            "contacto": p.contacto or "",
            "telefono": p.telefono or "",
            "email": p.correo or "",
            "direccion": p.direccion or "",
            "ciudad": p.ciudad or "",
            "estado": p.estado or "",
            "codigo_postal": p.codigo_postal or "",
        }
        for p in Proveedor.objects.filter(activo=True).order_by("nombre_proveedor")
    ]


def _intentar_generar_pdf(orden, request=None):
    try:
        pdf_bytes = document_engine.generar_pdf_orden_compra(orden)
    except document_engine.DocumentEngineError as exc:
        if request is not None:
            messages.warning(request, f"Orden guardada, pero no se genero el PDF: {exc}")
        return False

    from ..media_security import safe_basename

    nombre_pdf = safe_basename(f"{orden.folio_orden or 'orden'}.pdf", forced_ext=".pdf")
    orden.archivo_pdf.save(nombre_pdf, ContentFile(pdf_bytes), save=True)
    return True


def ordencompra_list(request):
    items = _ordenes_for_user(
        request.user,
        OrdenCompra.objects.select_related("proveedor", "elaborado_por")
        .annotate(
            lineas_count=Count("detalles"),
            equipos_count=Count("equipos", distinct=True),
        )
        .all(),
    )
    selected_folio = (request.GET.get("folio_orden") or "").strip()
    selected_estado = request.GET.get("estado", "")
    fecha_desde_raw = request.GET.get("fecha_desde", "")
    fecha_hasta_raw = request.GET.get("fecha_hasta", "")

    if selected_folio:
        items = items.filter(folio_orden__icontains=selected_folio)
    if selected_estado:
        items = items.filter(estado=selected_estado)

    fecha_desde = _parse_date(fecha_desde_raw)
    fecha_hasta = _parse_date(fecha_hasta_raw)
    items = _apply_date_filters(items, "fecha", fecha_desde, fecha_hasta)

    return render(
        request,
        "ordencompra/list.html",
        {
            "items": items,
            "estado_choices": EstadoOrdenCompra.choices,
            "selected_folio": selected_folio,
            "selected_estado": selected_estado,
            "fecha_desde": fecha_desde_raw,
            "fecha_hasta": fecha_hasta_raw,
            "solo_propias": not is_operativo(request.user),
            "puede_alta_inventario": is_operativo(request.user),
        },
    )


def ordencompra_choose(request):
    return render(request, "ordencompra/choose.html")


def ordencompra_create(request):
    orden_vacia = OrdenCompra()
    if request.method == "POST":
        form = OrdenCompraCrearForm(request.POST, instance=orden_vacia)
        formset = DetalleOrdenCompraFormSet(request.POST, instance=orden_vacia)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                orden = form.save(commit=False)
                orden.origen = OrigenOrdenCompra.CREADO
                orden.elaborado_por = request.user
                orden.save()
                formset.instance = orden
                formset.save()
                orden.recalcular_totales(save=True)
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.ORDEN_COMPRA,
                titulo=f"Orden de compra creada: {orden.folio_orden}",
                objeto=orden,
                enlace_nombre="ordencompra_update",
                metadata={"origen": orden.origen},
            )
            _intentar_generar_pdf(orden, request)
            messages.success(request, "Orden de compra creada correctamente.")
            return redirect("ordencompra_list")
    else:
        form = OrdenCompraCrearForm(
            instance=orden_vacia,
            initial={
                "fecha": timezone.localdate(),
                "tipo_moneda": TipoMoneda.MXN,
                "iva_opcion": IvaOpcion.DIECISEIS,
                "iva_porcentaje": 16,
                "estado": EstadoOrdenCompra.BORRADOR,
            },
        )
        formset = DetalleOrdenCompraFormSet(instance=orden_vacia)

    return render(
        request,
        "ordencompra/form_crear.html",
        {
            "form": form,
            "formset": formset,
            "proveedores_json": _proveedores_payload(),
            "elaborado_por_nombre": request.user.get_full_name() or request.user.get_username(),
        },
    )


def ordencompra_upload(request):
    if request.method == "POST":
        form = OrdenCompraSubirForm(request.POST, request.FILES)
        if form.is_valid():
            orden = form.save(commit=False)
            orden.origen = OrigenOrdenCompra.SUBIDO
            orden.elaborado_por = request.user
            orden.fecha = timezone.localdate()
            orden.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.ORDEN_COMPRA,
                titulo=f"Orden de compra subida: {orden.folio_orden}",
                objeto=orden,
                enlace_nombre="ordencompra_update",
                metadata={"origen": OrigenOrdenCompra.SUBIDO},
            )
            messages.success(request, "Orden de compra subida correctamente.")
            return redirect("ordencompra_list")
    else:
        form = OrdenCompraSubirForm()

    return render(
        request,
        "ordencompra/form_subir.html",
        {
            "form": form,
            "elaborado_por_nombre": request.user.get_full_name() or request.user.get_username(),
        },
    )


def ordencompra_update(request, pk):
    orden = get_object_or_404(
        OrdenCompra.objects.prefetch_related("detalles", "detalles__equipos"),
        pk=pk,
    )
    if not user_can_manage_orden(request.user, orden):
        messages.error(request, "No tienes permisos para esta orden de compra.")
        return redirect("ordencompra_list")

    puede_alta = orden.puede_recibir_equipos and is_operativo(request.user)
    equipos_ligados = (
        Equipo.objects.filter(orden_compra=orden).order_by("codigo_inventario")
        if orden.pk
        else Equipo.objects.none()
    )
    lineas_cupo = []
    for linea in orden.detalles.all():
        lineas_cupo.append(
            {
                "detalle": linea,
                "esperada": linea.cantidad_esperada,
                "recibida": linea.cantidad_recibida(),
                "disponible": linea.cantidad_disponible(),
            }
        )

    if orden.origen == OrigenOrdenCompra.SUBIDO:
        if request.method == "POST":
            form = OrdenCompraSubirForm(request.POST, request.FILES, instance=orden)
            if form.is_valid():
                nuevo_estado = form.cleaned_data.get("estado")
                if (
                    nuevo_estado == EstadoOrdenCompra.TERMINADO
                    and not orden.detalles.exists()
                ):
                    messages.warning(
                        request,
                        "Para marcar como Terminado una orden subida, captura las lineas de productos.",
                    )
                    return redirect("ordencompra_terminar", pk=orden.pk)
                form.save()
                historial.registrar_actualizacion(
                    request,
                    modulo=ModuloHistorial.ORDEN_COMPRA,
                    titulo=f"Orden de compra actualizada: {orden.folio_orden}",
                    objeto=orden,
                    form=form,
                    enlace_nombre="ordencompra_update",
                )
                messages.success(request, "Orden de compra actualizada correctamente.")
                return redirect("ordencompra_update", pk=orden.pk)
        else:
            form = OrdenCompraSubirForm(instance=orden)
        return render(
            request,
            "ordencompra/form_subir.html",
            {
                "form": form,
                "object": orden,
                "puede_alta": puede_alta,
                "equipos_ligados": equipos_ligados,
                "lineas_cupo": lineas_cupo,
                "elaborado_por_nombre": (
                    (orden.elaborado_por.get_full_name() or orden.elaborado_por.get_username())
                    if orden.elaborado_por
                    else (request.user.get_full_name() or request.user.get_username())
                ),
            },
        )

    if request.method == "POST":
        form = OrdenCompraCrearForm(request.POST, instance=orden)
        formset = DetalleOrdenCompraFormSet(request.POST, instance=orden)
        if form.is_valid() and formset.is_valid():
            nuevo_estado = form.cleaned_data.get("estado")
            with transaction.atomic():
                orden = form.save()
                formset.save()
                orden.recalcular_totales(save=True)
            if nuevo_estado == EstadoOrdenCompra.TERMINADO and not orden.detalles.exists():
                orden.estado = EstadoOrdenCompra.EN_PROCESO
                orden.save(update_fields=["estado"])
                messages.error(
                    request,
                    "No se puede terminar una orden sin lineas de producto.",
                )
                return redirect("ordencompra_update", pk=orden.pk)
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.ORDEN_COMPRA,
                titulo=f"Orden de compra actualizada: {orden.folio_orden}",
                objeto=orden,
                form=form,
                enlace_nombre="ordencompra_update",
            )
            _intentar_generar_pdf(orden, request)
            if orden.puede_recibir_equipos:
                messages.success(
                    request,
                    "Orden terminada y lista para inventariar. Puedes dar de alta equipos.",
                )
            else:
                messages.success(request, "Orden de compra actualizada correctamente.")
            return redirect("ordencompra_update", pk=orden.pk)
    else:
        form = OrdenCompraCrearForm(instance=orden)
        formset = DetalleOrdenCompraFormSet(instance=orden)

    return render(
        request,
        "ordencompra/form_crear.html",
        {
            "form": form,
            "formset": formset,
            "object": orden,
            "puede_alta": puede_alta,
            "equipos_ligados": equipos_ligados,
            "lineas_cupo": lineas_cupo,
            "proveedores_json": _proveedores_payload(),
            "elaborado_por_nombre": (
                (orden.elaborado_por.get_full_name() or orden.elaborado_por.get_username())
                if orden.elaborado_por
                else (request.user.get_full_name() or request.user.get_username())
            ),
        },
    )


def ordencompra_terminar(request, pk):
    """Marca OC como Terminado. Si es PDF, exige capturar lineas de productos."""
    orden = get_object_or_404(
        OrdenCompra.objects.prefetch_related("detalles"),
        pk=pk,
    )
    if not user_can_manage_orden(request.user, orden):
        messages.error(request, "No tienes permisos para esta orden de compra.")
        return redirect("ordencompra_list")

    if orden.estado == EstadoOrdenCompra.TERMINADO and orden.lista_para_inventario:
        messages.info(request, "Esta orden ya esta terminada y lista para inventariar.")
        return redirect("ordencompra_update", pk=orden.pk)

    if orden.estado == EstadoOrdenCompra.CANCELADO:
        messages.error(request, "No se puede terminar una orden cancelada.")
        return redirect("ordencompra_update", pk=orden.pk)

    es_pdf = orden.origen == OrigenOrdenCompra.SUBIDO

    if not es_pdf:
        if not orden.detalles.exists():
            messages.error(request, "Agrega lineas de producto antes de terminar la orden.")
            return redirect("ordencompra_update", pk=orden.pk)
        if request.method == "POST":
            orden.estado = EstadoOrdenCompra.TERMINADO
            orden.save(update_fields=["estado"])
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.ORDEN_COMPRA,
                accion=AccionHistorial.CAMBIO_ESTADO,
                titulo=f"Orden terminada (lista para inventariar): {orden.folio_orden}",
                objeto=orden,
                enlace_nombre="ordencompra_update",
            )
            messages.success(
                request,
                "Orden marcada como Terminado. Ya puedes dar de alta equipos.",
            )
            return redirect("ordencompra_update", pk=orden.pk)
        return render(
            request,
            "ordencompra/terminar.html",
            {
                "object": orden,
                "es_pdf": False,
                "detalles": orden.detalles.all(),
            },
        )

    # OC subida: capturar lineas
    if request.method == "POST":
        formset = DetalleOrdenCompraCapturaFormSet(request.POST, instance=orden)
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
                orden.estado = EstadoOrdenCompra.TERMINADO
                orden.save(update_fields=["estado"])
                orden.recalcular_totales(save=True)
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.ORDEN_COMPRA,
                accion=AccionHistorial.CAMBIO_ESTADO,
                titulo=f"Orden PDF terminada con lineas: {orden.folio_orden}",
                objeto=orden,
                enlace_nombre="ordencompra_update",
                metadata={"lineas": orden.detalles.count()},
            )
            messages.success(
                request,
                "Lineas capturadas y orden terminada. Ya puedes dar de alta equipos.",
            )
            return redirect("ordencompra_update", pk=orden.pk)
    else:
        formset = DetalleOrdenCompraCapturaFormSet(instance=orden)

    return render(
        request,
        "ordencompra/terminar.html",
        {
            "object": orden,
            "es_pdf": True,
            "formset": formset,
            "detalles": orden.detalles.all(),
        },
    )


def ordencompra_delete(request, pk):
    orden = get_object_or_404(OrdenCompra, pk=pk)
    if not user_can_manage_orden(request.user, orden):
        messages.error(request, "No tienes permisos para esta orden de compra.")
        return redirect("ordencompra_list")
    if request.method == "POST":
        folio = orden.folio_orden
        nivel = (
            NivelHistorial.CRITICO
            if not is_admin_user(request.user)
            else NivelHistorial.ADVERTENCIA
        )
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.ORDEN_COMPRA,
            titulo=f"Orden de compra eliminada: {folio}",
            objeto=orden,
            descripcion=(
                f"Eliminada por {request.user.get_username()} "
                f"(rol: {get_user_role(request.user) or 'Usuario'})."
            ),
            metadata={
                "folio_orden": folio,
                "eliminado_por_id": request.user.pk,
                "eliminado_por": request.user.get_username(),
                "rol": get_user_role(request.user),
                "elaborado_por_id": orden.elaborado_por_id,
                "aviso_admin": True,
            },
            nivel=nivel,
        )
        orden.delete()
        messages.success(request, "Orden de compra eliminada correctamente.")
        return redirect("ordencompra_list")
    return render(request, "ordencompra/confirm_delete.html", {"object": orden})


def mis_equipos(request):
    """Equipos asignados al personal vinculado al usuario autenticado."""
    try:
        personal = request.user.personal_profile
    except Personal.DoesNotExist:
        personal = None

    asignaciones = AsignacionEquipo.objects.none()
    if personal is not None:
        asignaciones = (
            AsignacionEquipo.objects.select_related(
                "equipo",
                "equipo__categoria",
                "equipo__ubicacion",
            )
            .filter(personal=personal, estado_asignacion=EstadoAsignacion.ACTIVA)
            .order_by("-fecha_asignacion")
        )

    return render(
        request,
        "equipo/mis_equipos.html",
        {
            "personal": personal,
            "asignaciones": asignaciones,
        },
    )


def ordencompra_preview(request):
    """Vista previa PDF fiel de la plantilla (incluye imagenes y formato)."""
    import json

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Metodo no permitido."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON invalido."}, status=400)

    plantilla = None
    plantilla_id = payload.get("plantilla_id")
    if plantilla_id:
        plantilla = PlantillaDocumento.objects.filter(pk=plantilla_id, activo=True).first()
        if plantilla is None:
            return JsonResponse({"ok": False, "error": "Plantilla no encontrada."}, status=404)

    valores = document_engine.valores_desde_payload(payload)
    try:
        pdf_bytes = document_engine.render_preview_pdf(valores, plantilla=plantilla)
    except document_engine.DocumentEngineError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    nombre = plantilla.nombre if plantilla else "Plantilla por defecto"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["X-Plantilla-Nombre"] = nombre.encode("ascii", "replace").decode("ascii")
    response["Content-Disposition"] = 'inline; filename="vista_previa_orden.pdf"'
    response["Cache-Control"] = "no-store"
    response["Access-Control-Expose-Headers"] = "X-Plantilla-Nombre"
    return response


