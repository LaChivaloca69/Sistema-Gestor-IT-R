"""Tickets, seguimientos, bitácora y answers."""
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
from ..forms.common import get_subtipo_ticket_choices
from ..forms.tickets import (
    AnswerForm,
    BitacoraForm,
    SeguimientoTicketForm,
    TicketITForm,
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

TICKET_LIST_PAGE_SIZE = 20


def _ticketit_queryset():
    return TicketIT.objects.select_related(
        "area",
        "puesto",
        "solicitado_por",
        "asignado_a",
        "equipo",
        "tipo_equipo",
    )


def ticketit_list(request):
    is_staff_user = is_operativo(request.user)
    items = _tickets_for_user(request.user, _ticketit_queryset()).annotate(
        seguimientos_count=Count("seguimientos")
    ).order_by("-fecha_support", "-pk")
    search_query = (request.GET.get("q") or "").strip()
    selected_tipo = request.GET.get("tipo_ticket", "")
    selected_prioridad = request.GET.get("prioridad", "")
    selected_status = request.GET.get("status", "")
    selected_scope = request.GET.get("scope", "")
    selected_alerta = request.GET.get("alerta", "")
    selected_sin_seguimiento = request.GET.get("sin_seguimiento", "")
    selected_equipo = (request.GET.get("equipo") or "").strip()
    now = timezone.now()

    if search_query:
        items = items.filter(
            Q(folio_ticket__icontains=search_query)
            | Q(requerimiento__icontains=search_query)
            | Q(descripcion__icontains=search_query)
            | Q(detalle__icontains=search_query)
            | Q(equipo__codigo_inventario__icontains=search_query)
            | Q(solicitado_por__username__icontains=search_query)
            | Q(asignado_a__username__icontains=search_query)
        )
    if selected_tipo:
        items = items.filter(tipo_ticket=selected_tipo)
    if selected_prioridad:
        items = items.filter(prioridad=selected_prioridad)
    if selected_status:
        items = items.filter(status=selected_status)
    elif selected_alerta in {"sla", "sla_por_vencer", "operacion"} or selected_sin_seguimiento == "1":
        items = items.exclude(status=EstadoSupport.CERRADO)

    if selected_equipo.isdigit():
        items = items.filter(equipo_id=int(selected_equipo))

    if is_staff_user:
        if selected_scope == "mios":
            items = items.filter(solicitado_por=request.user)
        elif selected_scope == "asignados":
            items = items.filter(ticket_asignados_q_for_user(request.user))

    if selected_alerta == "sla":
        items = items.filter(_tickets_sla_vencidos_q(now)).order_by("fecha_support", "pk")
    elif selected_alerta == "sla_por_vencer":
        items = items.filter(_tickets_sla_por_vencer_q(now)).order_by("fecha_support", "pk")
    elif selected_alerta == "operacion":
        items = items.filter(
            _tickets_sla_vencidos_q(now) | Q(seguimientos_count=0)
        ).order_by("fecha_support", "pk")

    if selected_sin_seguimiento == "1":
        items = items.filter(seguimientos_count=0)

    paginator = Paginator(items, TICKET_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    for item in page_obj.object_list:
        item.perm_can_edit = user_can_edit_ticket(request.user, item)
        item.perm_can_delete = user_can_delete_ticket(request.user, item)

    context = {
        "items": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "tipo_choices": TipoTicketSupport.choices,
        "prioridad_choices": PrioridadSupport.choices,
        "status_choices": EstadoSupport.choices,
        "selected_tipo": selected_tipo,
        "selected_prioridad": selected_prioridad,
        "selected_status": selected_status,
        "selected_scope": selected_scope,
        "selected_alerta": selected_alerta,
        "selected_sin_seguimiento": selected_sin_seguimiento,
        "selected_equipo": selected_equipo,
        "can_manage_flow": user_can_manage_ticket_flow(request.user),
        "is_staff_user": is_staff_user,
        "sla_horas": SLA_HORAS_POR_PRIORIDAD,
        "mis_coberturas": coberturas_activas_para_suplente(request.user) if is_staff_user else [],
    }
    return render(request, "ticketit/list.html", context)


def ticketit_dashboard(request):
    context = {
        "is_staff_user": is_operativo(request.user),
        **_ticket_dashboard_context(request.user),
    }
    return render(request, "ticketit/dashboard.html", context)


def ticketit_detail(request, pk):
    ticket = get_object_or_404(
        _ticketit_queryset().prefetch_related("seguimientos__usuario"),
        pk=pk,
    )
    if not user_can_view_ticket(request.user, ticket):
        return _deny_ticket_access(request)

    can_manage_flow = user_can_manage_ticket_flow(request.user)
    can_edit = user_can_edit_ticket(request.user, ticket)
    can_delete = user_can_delete_ticket(request.user, ticket)
    can_add_seguimiento = can_manage_flow and ticket.status != EstadoSupport.CERRADO
    seguimiento_form = None

    if can_add_seguimiento and request.method == "POST" and request.POST.get("form_type") == "seguimiento":
        seguimiento_form = SeguimientoTicketForm(
            request.POST,
            ticket=ticket,
            request_user=request.user,
        )
        if seguimiento_form.is_valid():
            seguimiento = seguimiento_form.save()
            if not ticket.asignado_a_id and request.user.is_authenticated:
                ticket.asignado_a = request.user
                ticket.save(update_fields=["asignado_a"])
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.SEGUIMIENTO,
                titulo=f"Seguimiento en {seguimiento.folio_check or ticket.folio_ticket}",
                objeto=seguimiento,
                entidad_relacionada=ticket,
                enlace_nombre="ticketit_detail",
                enlace_pk=ticket.pk,
                metadata={"ticket_id": ticket.pk},
            )
            messages.success(request, "Seguimiento registrado correctamente.")
            return redirect("ticketit_detail", pk=ticket.pk)

    if can_add_seguimiento and seguimiento_form is None:
        seguimiento_form = SeguimientoTicketForm(
            ticket=ticket,
            request_user=request.user,
        )

    seguimientos = ticket.seguimientos.select_related("usuario").order_by(
        "-fecha_check", "-pk"
    )

    return render(
        request,
        "ticketit/detail.html",
        {
            "object": ticket,
            "seguimientos": seguimientos,
            "seguimiento_form": seguimiento_form,
            "can_manage_flow": can_manage_flow,
            "can_add_seguimiento": can_add_seguimiento,
            "can_edit": can_edit,
            "can_delete": can_delete,
        },
    )


def ticketit_create(request):
    if request.method == "POST":
        form = TicketITForm(request.POST, request.FILES, request_user=request.user)
        if form.is_valid():
            ticket = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.TICKET,
                titulo=f"Ticket creado: {ticket.folio_ticket}",
                objeto=ticket,
                enlace_nombre="ticketit_detail",
                metadata={"estado": ticket.status, "prioridad": ticket.prioridad},
            )
            messages.success(request, "Support creado correctamente.")
            return redirect("ticketit_detail", pk=ticket.pk)
    else:
        form = TicketITForm(request_user=request.user)
    return render(
        request,
        "ticketit/form.html",
        {
            "form": form,
            "can_manage_flow": user_can_manage_ticket_flow(request.user),
            "can_edit": True,
        },
    )


def ticketit_update(request, pk):
    ticket = get_object_or_404(_ticketit_queryset(), pk=pk)
    if not user_can_view_ticket(request.user, ticket):
        return _deny_ticket_access(request)
    if not user_can_edit_ticket(request.user, ticket):
        messages.error(
            request,
            "No puedes editar este ticket. Solo staff, o el solicitante mientras este Abierto y sin seguimientos.",
        )
        return redirect("ticketit_detail", pk=ticket.pk)

    if request.method == "POST":
        form = TicketITForm(
            request.POST,
            request.FILES,
            instance=ticket,
            request_user=request.user,
        )
        if form.is_valid():
            ticket = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.TICKET,
                titulo=f"Ticket actualizado: {ticket.folio_ticket}",
                objeto=ticket,
                form=form,
                enlace_nombre="ticketit_detail",
            )
            messages.success(request, "Support actualizado correctamente.")
            return redirect("ticketit_detail", pk=ticket.pk)
    else:
        form = TicketITForm(instance=ticket, request_user=request.user)
    return render(
        request,
        "ticketit/form.html",
        {
            "form": form,
            "object": ticket,
            "can_manage_flow": user_can_manage_ticket_flow(request.user),
            "can_edit": True,
            "can_delete": user_can_delete_ticket(request.user, ticket),
        },
    )


def ticketit_delete(request, pk):
    ticket = get_object_or_404(_ticketit_queryset(), pk=pk)
    if not user_can_view_ticket(request.user, ticket):
        return _deny_ticket_access(request)
    if not user_can_delete_ticket(request.user, ticket):
        if not is_admin_user(request.user):
            messages.error(request, "Solo el personal de soporte puede eliminar tickets.")
        else:
            messages.error(
                request,
                "No se puede eliminar un ticket con seguimientos. Elimina los checks primero.",
            )
        return redirect("ticketit_detail", pk=ticket.pk)

    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.TICKET,
            titulo=f"Ticket eliminado: {ticket.folio_ticket}",
            objeto=ticket,
            nivel=NivelHistorial.CRITICO,
        )
        ticket.delete()
        messages.success(request, "Support eliminado correctamente.")
        return redirect("ticketit_list")
    return render(
        request,
        "ticketit/confirm_delete.html",
        {"object": ticket, "can_delete": True},
    )


def ticketit_marcar_revision(request, pk):
    ticket = get_object_or_404(TicketIT, pk=pk)
    if request.method != "POST":
        return redirect("ticketit_detail", pk=pk)
    if not user_can_manage_ticket_flow(request.user):
        return _deny_ticket_access(request, "Solo staff puede cambiar el estado del ticket.")

    try:
        ticket.marcar_en_revision()
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("ticketit_detail", pk=pk)

    if not ticket.asignado_a_id:
        ticket.asignado_a = request.user
        ticket.save(update_fields=["asignado_a"])

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.TICKET,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Ticket en revision: {ticket.folio_ticket}",
        objeto=ticket,
        enlace_nombre="ticketit_detail",
        metadata={"estado": ticket.status},
    )
    messages.success(request, f"{ticket.folio_ticket} marcado En Revision.")
    return redirect("ticketit_detail", pk=pk)


def ticketit_reabrir(request, pk):
    ticket = get_object_or_404(TicketIT, pk=pk)
    if request.method != "POST":
        return redirect("ticketit_detail", pk=pk)
    if not user_can_manage_ticket_flow(request.user):
        return _deny_ticket_access(request, "Solo staff puede reabrir tickets.")

    motivo = (request.POST.get("motivo") or "").strip()
    try:
        ticket.reabrir(usuario=request.user, motivo=motivo)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("ticketit_detail", pk=pk)

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.TICKET,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Ticket reabierto: {ticket.folio_ticket}",
        objeto=ticket,
        enlace_nombre="ticketit_detail",
        metadata={"estado": ticket.status, "motivo": motivo or "Ticket reabierto."},
    )
    messages.success(request, f"{ticket.folio_ticket} reabierto ({ticket.status}).")
    return redirect("ticketit_detail", pk=pk)


def ticketit_subtipo_choices(request):
    tipo_ticket = request.GET.get("tipo_ticket")
    choices = get_subtipo_ticket_choices(tipo_ticket)
    data = [{"value": value, "label": label} for value, label in choices]
    return JsonResponse({"choices": data})

# ============ SeguimientoTicket views ==============

SEGUIMIENTO_LIST_PAGE_SIZE = 20
SEGUIMIENTO_ALERTA_DIAS = 7


def _seguimientos_base_qs():
    return SeguimientoTicket.objects.select_related(
        "ticket",
        "ticket__asignado_a",
        "usuario",
    )


def _seguimientos_pendientes_qs():
    return (
        _seguimientos_base_qs()
        .filter(
            ya_terminado=False,
            fecha_proximo_seguimiento__isnull=False,
        )
        .exclude(ticket__status=EstadoSupport.CERRADO)
    )


def _seguimientos_alerta_context(today=None, horizon_days=SEGUIMIENTO_ALERTA_DIAS):
    today = today or timezone.localdate()
    pendientes = _seguimientos_pendientes_qs()
    vencidos_qs = pendientes.filter(
        fecha_proximo_seguimiento__lt=today
    ).order_by("fecha_proximo_seguimiento", "pk")
    por_vencer_qs = pendientes.filter(
        fecha_proximo_seguimiento__gte=today,
        fecha_proximo_seguimiento__lte=today + timedelta(days=horizon_days),
    ).order_by("fecha_proximo_seguimiento", "pk")
    return {
        "seguimientos_vencidos": list(vencidos_qs[:8]),
        "seguimientos_por_vencer": list(por_vencer_qs[:8]),
        "seguimientos_vencidos_count": vencidos_qs.count(),
        "seguimientos_por_vencer_count": por_vencer_qs.count(),
        "seguimientos_alerta_dias": horizon_days,
    }


def seguimientoticket_list(request):
    items = _seguimientos_base_qs().order_by("-fecha_check", "-pk")
    search_query = (request.GET.get("q") or "").strip()
    selected_status = request.GET.get("status", "")
    selected_terminado = request.GET.get("terminado", "")
    selected_alerta = request.GET.get("alerta", "")
    selected_scope = request.GET.get("scope", "")
    today = timezone.localdate()

    if search_query:
        items = items.filter(
            Q(folio_check__icontains=search_query)
            | Q(ticket__folio_ticket__icontains=search_query)
            | Q(avance_realizado__icontains=search_query)
            | Q(pendiente__icontains=search_query)
            | Q(proximo_paso__icontains=search_query)
            | Q(solucion__icontains=search_query)
            | Q(usuario__username__icontains=search_query)
        )
    if selected_status:
        items = items.filter(ticket__status=selected_status)
    if selected_terminado == "si":
        items = items.filter(ya_terminado=True)
    elif selected_terminado == "no":
        items = items.filter(ya_terminado=False)

    if selected_alerta == "vencidos":
        items = items.filter(
            ya_terminado=False,
            fecha_proximo_seguimiento__lt=today,
        ).exclude(ticket__status=EstadoSupport.CERRADO).order_by(
            "fecha_proximo_seguimiento", "pk"
        )
    elif selected_alerta == "proximos":
        items = items.filter(
            ya_terminado=False,
            fecha_proximo_seguimiento__gte=today,
            fecha_proximo_seguimiento__lte=today + timedelta(days=SEGUIMIENTO_ALERTA_DIAS),
        ).exclude(ticket__status=EstadoSupport.CERRADO).order_by(
            "fecha_proximo_seguimiento", "pk"
        )
    elif selected_alerta == "atencion":
        items = items.filter(
            ya_terminado=False,
            fecha_proximo_seguimiento__isnull=False,
            fecha_proximo_seguimiento__lte=today + timedelta(days=SEGUIMIENTO_ALERTA_DIAS),
        ).exclude(ticket__status=EstadoSupport.CERRADO).order_by(
            "fecha_proximo_seguimiento", "pk"
        )

    if selected_scope == "mios":
        items = items.filter(usuario=request.user)

    paginator = Paginator(items, SEGUIMIENTO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "items": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "status_choices": EstadoSupport.choices,
        "selected_status": selected_status,
        "selected_terminado": selected_terminado,
        "selected_alerta": selected_alerta,
        "selected_scope": selected_scope,
        "today": today,
    }
    return render(request, "seguimientoticket/list.html", context)


def seguimientoticket_create(request):
    if request.method == "POST":
        form = SeguimientoTicketForm(request.POST, request_user=request.user)
        if form.is_valid():
            seguimiento = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.SEGUIMIENTO,
                titulo=f"Seguimiento en {seguimiento.folio_check or seguimiento.ticket}",
                objeto=seguimiento,
                entidad_relacionada=seguimiento.ticket,
                enlace_nombre="ticketit_detail",
                enlace_pk=seguimiento.ticket_id,
                metadata={"ticket_id": seguimiento.ticket_id},
            )
            messages.success(request, "Check creado correctamente.")
            if seguimiento.ticket_id:
                return redirect("ticketit_detail", pk=seguimiento.ticket_id)
            return redirect("seguimientoticket_list")
    else:
        initial_ticket = request.GET.get("ticket")
        form = SeguimientoTicketForm(request_user=request.user)
        if initial_ticket:
            form.fields["ticket"].initial = initial_ticket
    return render(request, "seguimientoticket/form.html", {"form": form})


def seguimientoticket_update(request, pk):
    seguimiento = get_object_or_404(
        _seguimientos_base_qs(),
        pk=pk,
    )
    if request.method == "POST":
        form = SeguimientoTicketForm(
            request.POST,
            instance=seguimiento,
            request_user=request.user,
        )
        if form.is_valid():
            seguimiento = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.SEGUIMIENTO,
                titulo=f"Seguimiento actualizado: {seguimiento.folio_check or seguimiento.pk}",
                objeto=seguimiento,
                form=form,
                entidad_relacionada=seguimiento.ticket,
                enlace_nombre="ticketit_detail",
                enlace_pk=seguimiento.ticket_id,
            )
            messages.success(request, "Check actualizado correctamente.")
            if seguimiento.ticket_id:
                return redirect("ticketit_detail", pk=seguimiento.ticket_id)
            return redirect("seguimientoticket_list")
    else:
        form = SeguimientoTicketForm(instance=seguimiento, request_user=request.user)
    return render(
        request,
        "seguimientoticket/form.html",
        {"form": form, "object": seguimiento},
    )


def seguimientoticket_delete(request, pk):
    seguimiento = get_object_or_404(SeguimientoTicket, pk=pk)
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.SEGUIMIENTO,
            titulo=f"Seguimiento eliminado: {seguimiento.folio_check or seguimiento.pk}",
            objeto=seguimiento,
        )
        ticket_pk = seguimiento.ticket_id
        seguimiento.delete()
        messages.success(request, "Check eliminado correctamente.")
        if ticket_pk and request.GET.get("next") == "ticket":
            return redirect("ticketit_detail", pk=ticket_pk)
        return redirect("seguimientoticket_list")
    return render(request, "seguimientoticket/confirm_delete.html", {"object": seguimiento})

def bitacora_list(request):
    items = Bitacora.objects.all()
    return render(request, "bitacora/list.html", {"items": items})


def bitacora_create(request):
    if request.method == "POST":
        form = BitacoraForm(request.POST)
        if form.is_valid():
            bitacora = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.BITACORA,
                titulo=f"Bitacora creada: {bitacora.folio_bitacora}",
                objeto=bitacora,
                enlace_nombre="bitacora_update",
            )
            messages.success(request, "Bitacora creada correctamente.")
            return redirect("bitacora_list")
    else:
        form = BitacoraForm()
    return render(request, "bitacora/form.html", {"form": form})


def bitacora_update(request, pk):
    bitacora = get_object_or_404(Bitacora, pk=pk)
    if request.method == "POST":
        form = BitacoraForm(request.POST, instance=bitacora)
        if form.is_valid():
            bitacora = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.BITACORA,
                titulo=f"Bitacora actualizada: {bitacora.folio_bitacora}",
                objeto=bitacora,
                form=form,
                enlace_nombre="bitacora_update",
            )
            messages.success(request, "Bitacora actualizada correctamente.")
            return redirect("bitacora_list")
    else:
        form = BitacoraForm(instance=bitacora)
    return render(request, "bitacora/form.html", {"form": form, "object": bitacora})


def bitacora_delete(request, pk):
    bitacora = get_object_or_404(Bitacora, pk=pk)
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.BITACORA,
            titulo=f"Bitacora eliminada: {bitacora.folio_bitacora}",
            objeto=bitacora,
        )
        bitacora.delete()
        messages.success(request, "Bitacora eliminada correctamente.")
        return redirect("bitacora_list")
    return render(request, "bitacora/confirm_delete.html", {"object": bitacora})

def answer_list(request):
    items = Answer.objects.all()
    return render(request, "answer/list.html", {"items": items})


def answer_create(request):
    if request.method == "POST":
        form = AnswerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Answer creado correctamente.")
            return redirect("answer_list")
    else:
        form = AnswerForm()
    return render(request, "answer/form.html", {"form": form})


def answer_update(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    if request.method == "POST":
        form = AnswerForm(request.POST, instance=answer)
        if form.is_valid():
            form.save()
            messages.success(request, "Answer actualizado correctamente.")
            return redirect("answer_list")
    else:
        form = AnswerForm(instance=answer)
    return render(request, "answer/form.html", {"form": form, "object": answer})


def answer_delete(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    if request.method == "POST":
        answer.delete()
        messages.success(request, "Answer eliminado correctamente.")
        return redirect("answer_list")
    return render(request, "answer/confirm_delete.html", {"object": answer})


# =========== PlantillaDocumento views =============
