"""Vistas de gobierno: matriz de permisos, coberturas y solicitudes de equipo."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import historial
from .cobertura import coberturas_activas_para_suplente
from .gobierno_forms import (
    CoberturaTicketsForm,
    SeguimientoSolicitudEquipoForm,
    SolicitudEquipoForm,
    SolicitudEquipoRevisionForm,
)
from .models import (
    AccionHistorial,
    AsignacionEquipo,
    CoberturaTickets,
    EstadoAsignacion,
    EstadoSolicitudEquipo,
    ModuloHistorial,
    Personal,
    SeguimientoSolicitudEquipo,
    SolicitudEquipo,
    TipoMovimiento,
)
from .permissions_matrix import matrix_for_template
from .roles import admin_required, is_admin_user, is_operativo, operativo_required


# ---- Matriz de permisos ----

@admin_required
def permisos_matriz(request):
    context = matrix_for_template()
    return render(request, "gobierno/permisos_matriz.html", context)


# ---- Coberturas ----

@operativo_required
def cobertura_list(request):
    today = timezone.localdate()
    items = CoberturaTickets.objects.select_related(
        "ausente", "suplente", "creado_por"
    ).order_by("-fecha_inicio", "-pk")
    filtro = request.GET.get("filtro", "vigentes")
    if filtro == "vigentes":
        items = items.filter(activa=True, fecha_inicio__lte=today, fecha_fin__gte=today)
    elif filtro == "activas":
        items = items.filter(activa=True)
    elif filtro == "mias":
        items = items.filter(Q(suplente=request.user) | Q(ausente=request.user))

    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    mis_coberturas = coberturas_activas_para_suplente(request.user, today)

    return render(
        request,
        "gobierno/cobertura_list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "filtro": filtro,
            "mis_coberturas": mis_coberturas,
            "today": today,
        },
    )


@operativo_required
def cobertura_create(request):
    if request.method == "POST":
        form = CoberturaTicketsForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.creado_por = request.user
            obj.save()
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.GOBIERNO,
                accion=AccionHistorial.CREACION,
                titulo=f"Cobertura: {obj.suplente} cubre a {obj.ausente}",
                objeto=obj,
                enlace_nombre="cobertura_list",
            )
            messages.success(request, "Cobertura creada.")
            return redirect("cobertura_list")
    else:
        form = CoberturaTicketsForm()
    return render(
        request,
        "gobierno/cobertura_form.html",
        {"form": form, "object": None},
    )


@operativo_required
def cobertura_update(request, pk):
    obj = get_object_or_404(CoberturaTickets, pk=pk)
    if request.method == "POST":
        form = CoberturaTicketsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.GOBIERNO,
                accion=AccionHistorial.ACTUALIZACION,
                titulo=f"Cobertura actualizada: {obj}",
                objeto=obj,
                enlace_nombre="cobertura_list",
            )
            messages.success(request, "Cobertura actualizada.")
            return redirect("cobertura_list")
    else:
        form = CoberturaTicketsForm(instance=obj)
    return render(
        request,
        "gobierno/cobertura_form.html",
        {"form": form, "object": obj},
    )


@operativo_required
def cobertura_delete(request, pk):
    obj = get_object_or_404(CoberturaTickets, pk=pk)
    if request.method == "POST":
        etiqueta = str(obj)
        obj.delete()
        historial.registrar_historial(
            request=request,
            modulo=ModuloHistorial.GOBIERNO,
            accion=AccionHistorial.ELIMINACION,
            titulo=f"Cobertura eliminada: {etiqueta}",
        )
        messages.success(request, "Cobertura eliminada.")
        return redirect("cobertura_list")
    return render(
        request,
        "gobierno/cobertura_confirm_delete.html",
        {"object": obj},
    )


# ---- Solicitudes de equipo ----

def _solicitudes_qs_for(user):
    qs = SolicitudEquipo.objects.select_related(
        "solicitante", "personal", "categoria", "equipo", "revisado_por"
    )
    if is_operativo(user):
        return qs
    return qs.filter(solicitante=user)


@login_required
def solicitud_equipo_list(request):
    items = _solicitudes_qs_for(request.user).order_by("-fecha_creacion", "-pk")
    estado = request.GET.get("estado", "")
    if estado:
        items = items.filter(estado=estado)
    if is_operativo(request.user) and request.GET.get("scope") == "mias":
        items = items.filter(solicitante=request.user)

    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "gobierno/solicitud_list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "estado_choices": EstadoSolicitudEquipo.choices,
            "selected_estado": estado,
            "is_staff_user": is_operativo(request.user),
        },
    )


@login_required
def solicitud_equipo_create(request):
    if request.method == "POST":
        form = SolicitudEquipoForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.solicitante = request.user
            if getattr(form.fields.get("personal"), "disabled", False):
                try:
                    personal = request.user.personal_profile
                except Personal.DoesNotExist:
                    personal = None
                if personal:
                    obj.personal = personal
            obj.save()
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.SOLICITUD_EQUIPO,
                accion=AccionHistorial.CREACION,
                titulo=f"Solicitud {obj.folio}: {obj.titulo}",
                objeto=obj,
                enlace_nombre="solicitud_equipo_detail",
                enlace_pk=obj.pk,
            )
            messages.success(request, f"Solicitud {obj.folio} creada.")
            return redirect("solicitud_equipo_detail", pk=obj.pk)
    else:
        form = SolicitudEquipoForm(user=request.user)
    return render(
        request,
        "gobierno/solicitud_form.html",
        {"form": form, "object": None},
    )


def _revision_tiene_avance(cleaned):
    text_fields = (
        "avance_realizado",
        "pendiente",
        "proximo_paso",
        "solucion",
        "observacion",
    )
    if any((cleaned.get(field) or "").strip() for field in text_fields):
        return True
    return bool(cleaned.get("ya_terminado") or cleaned.get("fecha_proximo_seguimiento"))


@login_required
def solicitud_equipo_detail(request, pk):
    obj = get_object_or_404(
        _solicitudes_qs_for(request.user).prefetch_related("seguimientos__usuario"),
        pk=pk,
    )
    is_staff_user = is_operativo(request.user)
    can_manage = is_staff_user and obj.puede_gestionar_it
    revision_form = None
    seguimiento_form = None
    form_types = {"revision", "seguimiento"}

    if can_manage and request.method == "POST" and request.POST.get("form_type") in form_types:
        seguimiento_form = SeguimientoSolicitudEquipoForm(
            request.POST,
            solicitud=obj,
            request_user=request.user,
        )
        revision_form = SolicitudEquipoRevisionForm(
            request.POST,
            solicitud=obj,
            require_estado=False,
        )
        seguimiento_ok = seguimiento_form.is_valid()
        revision_ok = revision_form.is_valid()
        if seguimiento_ok and revision_ok:
            has_avance = _revision_tiene_avance(seguimiento_form.cleaned_data)
            has_decision = bool(revision_form.cleaned_data.get("estado"))
            if has_avance or has_decision:
                if has_avance:
                    revision = seguimiento_form.save()
                    historial.registrar_historial(
                        request=request,
                        modulo=ModuloHistorial.SOLICITUD_EQUIPO,
                        accion=AccionHistorial.CREACION,
                        titulo=f"Revision IT en {obj.folio}",
                        objeto=revision,
                        entidad_relacionada=obj,
                        enlace_nombre="solicitud_equipo_detail",
                        enlace_pk=obj.pk,
                    )
                    messages.success(request, "Revision IT registrada.")
                if has_decision:
                    estado_anterior = obj.estado
                    ok, assign_msg = _aplicar_decision_solicitud(
                        request, obj, revision_form
                    )
                    if not ok:
                        messages.error(request, assign_msg)
                    else:
                        if obj.estado != estado_anterior or not has_avance:
                            messages.success(
                                request,
                                "Solicitud cerrada."
                                if obj.estado == EstadoSolicitudEquipo.COMPLETADA
                                else f"Solicitud actualizada a {obj.estado}.",
                            )
                        if assign_msg:
                            messages.success(request, assign_msg)
                return redirect("solicitud_equipo_detail", pk=obj.pk)
            messages.error(request, "Indica un avance o una decision.")

    if can_manage:
        if revision_form is None:
            revision_form = SolicitudEquipoRevisionForm(
                solicitud=obj,
                require_estado=False,
            )
        if seguimiento_form is None:
            seguimiento_form = SeguimientoSolicitudEquipoForm(
                solicitud=obj,
                request_user=request.user,
            )

    revisiones = obj.seguimientos.select_related("usuario").order_by(
        "-fecha_check", "-pk"
    )

    return render(
        request,
        "gobierno/solicitud_detail.html",
        {
            "object": obj,
            "can_manage": can_manage,
            "can_add_revision": can_manage,
            "can_manage_flow": is_staff_user,
            "can_delete_revision": is_admin_user(request.user),
            "can_cancel": (
                obj.solicitante_id == request.user.id and obj.puede_cancelar_solicitante
            ),
            "revision_form": revision_form,
            "seguimiento_form": seguimiento_form,
            "revisiones": revisiones,
            "is_staff_user": is_staff_user,
        },
    )


def _asignar_equipo_desde_solicitud(request, solicitud, equipo):
    """Asigna equipo disponible al personal de la solicitud."""
    from .views import (
        _cerrar_asignaciones_activas,
        _crear_movimiento,
        _get_equipo_asignacion_activa,
        _reconciliar_estado_equipo,
    )

    personal = solicitud.personal
    if not personal:
        return False, "La solicitud no tiene personal destino para asignar."
    if not equipo.puede_asignarse:
        return False, "El equipo no esta disponible para asignar."

    existente = _get_equipo_asignacion_activa(equipo)
    if existente:
        _cerrar_asignaciones_activas(
            equipo,
            observaciones="Cerrada automaticamente por solicitud de equipo.",
        )
    asignacion = AsignacionEquipo.objects.create(
        equipo=equipo,
        personal=personal,
        estado_asignacion=EstadoAsignacion.ACTIVA,
        observaciones=f"Desde solicitud {solicitud.folio}",
    )
    _reconciliar_estado_equipo(equipo)
    _crear_movimiento(
        equipo,
        TipoMovimiento.CAMBIO_ASIGNACION if existente else TipoMovimiento.ASIGNACION,
        origen=equipo.ubicacion,
        destino=equipo.ubicacion,
        responsable=personal,
        observaciones=f"Solicitud {solicitud.folio}",
        request=request,
    )
    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.ASIGNACION,
        accion=AccionHistorial.ASIGNACION,
        titulo=f"Asignacion por solicitud {solicitud.folio}: {equipo} → {personal}",
        objeto=asignacion,
        entidad_relacionada=equipo,
        enlace_nombre="equipo_detail",
        enlace_pk=equipo.pk,
    )
    return True, f"Equipo {equipo.codigo_inventario} asignado a {personal}."


def _aplicar_decision_solicitud(request, obj, form):
    """Aplica estado, notas IT y equipo. Devuelve (ok, mensaje de asignacion)."""
    nuevo_estado = form.cleaned_data.get("estado")
    if not nuevo_estado:
        return True, None

    notas = form.cleaned_data.get("notas_it") or ""
    equipo = form.cleaned_data.get("equipo")

    obj.notas_it = notas
    obj.revisado_por = request.user
    obj.equipo = equipo
    obj.estado = nuevo_estado

    if nuevo_estado in {
        EstadoSolicitudEquipo.RECHAZADA,
        EstadoSolicitudEquipo.COMPLETADA,
    }:
        obj.fecha_resolucion = timezone.now()

    assign_msg = None
    if (
        nuevo_estado == EstadoSolicitudEquipo.COMPLETADA
        and equipo
        and obj.personal_id
    ):
        ok, assign_msg = _asignar_equipo_desde_solicitud(request, obj, equipo)
        if not ok:
            return False, assign_msg
        obj.fecha_resolucion = timezone.now()
    elif nuevo_estado == EstadoSolicitudEquipo.APROBADA and equipo and obj.personal_id:
        ok, assign_msg = _asignar_equipo_desde_solicitud(request, obj, equipo)
        if ok:
            obj.estado = EstadoSolicitudEquipo.COMPLETADA
            obj.fecha_resolucion = timezone.now()
        else:
            messages.warning(request, f"Aprobada sin asignar: {assign_msg}")
            assign_msg = None

    obj.save()
    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.SOLICITUD_EQUIPO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Solicitud {obj.folio} → {obj.estado}",
        objeto=obj,
        enlace_nombre="solicitud_equipo_detail",
        enlace_pk=obj.pk,
    )
    return True, assign_msg


@operativo_required
def solicitud_equipo_revisar(request, pk):
    obj = get_object_or_404(SolicitudEquipo, pk=pk)
    if not obj.puede_gestionar_it:
        messages.error(request, "Esta solicitud ya no admite revision.")
        return redirect("solicitud_equipo_detail", pk=pk)

    if request.method != "POST":
        return redirect("solicitud_equipo_detail", pk=pk)

    form = SolicitudEquipoRevisionForm(request.POST, solicitud=obj)
    if not form.is_valid():
        messages.error(request, "Revisa los datos de la revision.")
        return redirect("solicitud_equipo_detail", pk=pk)

    ok, assign_msg = _aplicar_decision_solicitud(request, obj, form)
    if not ok:
        messages.error(request, assign_msg)
        return redirect("solicitud_equipo_detail", pk=pk)

    messages.success(
        request,
        "Solicitud cerrada."
        if obj.estado == EstadoSolicitudEquipo.COMPLETADA
        else f"Solicitud actualizada a {obj.estado}.",
    )
    if assign_msg:
        messages.success(request, assign_msg)
    return redirect("solicitud_equipo_detail", pk=pk)


@login_required
def solicitud_equipo_cancelar(request, pk):
    obj = get_object_or_404(SolicitudEquipo, pk=pk)
    if obj.solicitante_id != request.user.id and not is_operativo(request.user):
        messages.error(request, "No puedes cancelar esta solicitud.")
        return redirect("solicitud_equipo_list")
    if not obj.puede_cancelar_solicitante and not is_operativo(request.user):
        messages.error(request, "La solicitud ya no se puede cancelar.")
        return redirect("solicitud_equipo_detail", pk=pk)

    if request.method == "POST":
        obj.estado = EstadoSolicitudEquipo.CANCELADA
        obj.fecha_resolucion = timezone.now()
        obj.save(update_fields=["estado", "fecha_resolucion", "fecha_actualizacion"])
        historial.registrar_historial(
            request=request,
            modulo=ModuloHistorial.SOLICITUD_EQUIPO,
            accion=AccionHistorial.CAMBIO_ESTADO,
            titulo=f"Solicitud {obj.folio} cancelada",
            objeto=obj,
            enlace_nombre="solicitud_equipo_detail",
            enlace_pk=obj.pk,
        )
        messages.success(request, "Solicitud cancelada.")
        return redirect("solicitud_equipo_list")

    return render(
        request,
        "gobierno/solicitud_cancelar.html",
        {"object": obj},
    )


@operativo_required
def seguimiento_solicitud_update(request, pk):
    seguimiento = get_object_or_404(
        SeguimientoSolicitudEquipo.objects.select_related("solicitud", "usuario"),
        pk=pk,
    )
    solicitud = seguimiento.solicitud
    if request.method == "POST":
        form = SeguimientoSolicitudEquipoForm(
            request.POST,
            instance=seguimiento,
            solicitud=solicitud,
            request_user=request.user,
        )
        if form.is_valid():
            form.save()
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.SOLICITUD_EQUIPO,
                accion=AccionHistorial.ACTUALIZACION,
                titulo=f"Revision IT actualizada en {solicitud.folio}",
                objeto=seguimiento,
                entidad_relacionada=solicitud,
                enlace_nombre="solicitud_equipo_detail",
                enlace_pk=solicitud.pk,
            )
            messages.success(request, "Revision IT actualizada.")
            return redirect("solicitud_equipo_detail", pk=solicitud.pk)
    else:
        form = SeguimientoSolicitudEquipoForm(
            instance=seguimiento,
            solicitud=solicitud,
            request_user=request.user,
        )
    return render(
        request,
        "gobierno/seguimiento_solicitud_form.html",
        {"form": form, "object": seguimiento, "solicitud": solicitud},
    )


@admin_required
def seguimiento_solicitud_delete(request, pk):
    seguimiento = get_object_or_404(
        SeguimientoSolicitudEquipo.objects.select_related("solicitud"),
        pk=pk,
    )
    solicitud = seguimiento.solicitud
    if request.method == "POST":
        historial.registrar_historial(
            request=request,
            modulo=ModuloHistorial.SOLICITUD_EQUIPO,
            accion=AccionHistorial.ELIMINACION,
            titulo=f"Revision IT eliminada en {solicitud.folio}",
            objeto=seguimiento,
            entidad_relacionada=solicitud,
            enlace_nombre="solicitud_equipo_detail",
            enlace_pk=solicitud.pk,
        )
        seguimiento.delete()
        messages.success(request, "Revision IT eliminada.")
        return redirect("solicitud_equipo_detail", pk=solicitud.pk)
    return render(
        request,
        "gobierno/seguimiento_solicitud_confirm_delete.html",
        {"object": seguimiento, "solicitud": solicitud},
    )
