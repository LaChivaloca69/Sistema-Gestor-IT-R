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
from django.urls import reverse

from . import document_engine
from . import historial
from .forms import (
	AnswerForm,
	SeguimientoTicketForm,
	TicketITForm,
    UserRegisterForm,
	UbicacionForm,
	get_subtipo_ticket_choices,
)
from .roles import (
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

from .models import (
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


def _ticket_has_seguimientos(ticket):
    if ticket is None:
        return False
    if hasattr(ticket, "seguimientos_count"):
        return bool(ticket.seguimientos_count)
    return ticket.seguimientos.exists()


def user_can_view_ticket(user, ticket):
    if not user or not user.is_authenticated or ticket is None:
        return False
    if is_operativo(user):
        return True
    return ticket.solicitado_por_id == user.id


def user_can_edit_ticket(user, ticket):
    if not user or not user.is_authenticated or ticket is None:
        return False
    if is_operativo(user):
        return True
    if ticket.solicitado_por_id != user.id:
        return False
    # Solicitante solo edita mientras el ticket sigue Abierto y sin checks.
    return ticket.status == EstadoSupport.ABIERTO and not _ticket_has_seguimientos(ticket)


def user_can_delete_ticket(user, ticket):
    if not is_admin_user(user) or ticket is None:
        return False
    return not _ticket_has_seguimientos(ticket)


def user_can_manage_ticket_flow(user):
    return is_operativo(user)


def _deny_ticket_access(request, message="No tienes permisos para este ticket."):
    messages.error(request, message)
    return redirect("ticketit_list")


def _tickets_for_user(user, qs=None):
    qs = qs if qs is not None else TicketIT.objects.all()
    if is_operativo(user):
        return qs
    return qs.filter(solicitado_por=user)


def _ordenes_for_user(user, qs=None):
    qs = qs if qs is not None else OrdenCompra.objects.all()
    if is_operativo(user):
        return qs
    return qs.filter(elaborado_por=user)


def user_can_manage_orden(user, orden):
    if not user or not user.is_authenticated or orden is None:
        return False
    if is_operativo(user):
        return True
    return orden.elaborado_por_id == user.id


def _tickets_sla_vencidos_q(now=None):
    now = now or timezone.now()
    query = Q(pk__in=[])  # empty base
    for prioridad, horas in SLA_HORAS_POR_PRIORIDAD.items():
        query |= Q(
            prioridad=prioridad,
            fecha_support__lt=now - timedelta(hours=horas),
        )
    return query


def _tickets_sla_por_vencer_q(now=None):
    """Tickets activos cuyo SLA(service level agreement) aun no vence pero estan cerca del limite."""
    now = now or timezone.now()
    query = Q(pk__in=[])
    for prioridad, horas in SLA_HORAS_POR_PRIORIDAD.items():
        limite_vencido = now - timedelta(hours=horas)
        umbral = min(timedelta(hours=4), timedelta(hours=horas) * 0.25)
        # Por vencer: fecha_support > limite_vencido (aun no vencido)
        # y fecha_support <= now - (horas*timedelta - umbral)  i.e. within umbral of deadline
        inicio_aviso = now - timedelta(hours=horas) + umbral
        query |= Q(
            prioridad=prioridad,
            fecha_support__gt=limite_vencido,
            fecha_support__lte=inicio_aviso,
        )
    return query


def _tickets_abiertos_qs(user=None):
    qs = TicketIT.objects.exclude(status=EstadoSupport.CERRADO)
    if user is not None:
        qs = _tickets_for_user(user, qs)
    return qs


def _ticket_dashboard_context(user):
    abiertos = _tickets_abiertos_qs(user).annotate(seguimientos_count=Count("seguimientos"))
    now = timezone.now()
    sla_vencidos_qs = abiertos.filter(_tickets_sla_vencidos_q(now)).order_by("fecha_support")
    sla_por_vencer_qs = abiertos.filter(_tickets_sla_por_vencer_q(now)).order_by("fecha_support")
    sin_seguimiento_qs = abiertos.filter(seguimientos_count=0).order_by("-fecha_support")

    por_prioridad = []
    for value, label in PrioridadSupport.choices:
        count = abiertos.filter(prioridad=value).count()
        por_prioridad.append(
            {
                "value": value,
                "label": label,
                "count": count,
                "horas_sla": SLA_HORAS_POR_PRIORIDAD.get(value),
            }
        )

    por_tipo = []
    for value, label in TipoTicketSupport.choices:
        por_tipo.append(
            {
                "value": value,
                "label": label,
                "count": abiertos.filter(tipo_ticket=value).count(),
            }
        )

    por_estado = []
    for value, label in EstadoSupport.choices:
        if value == EstadoSupport.CERRADO:
            continue
        por_estado.append(
            {
                "value": value,
                "label": label,
                "count": abiertos.filter(status=value).count(),
            }
        )

    return {
        "ticket_dashboard": {
            "abiertos": abiertos.count(),
            "sla_vencidos": sla_vencidos_qs.count(),
            "sla_por_vencer": sla_por_vencer_qs.count(),
            "sin_seguimiento": sin_seguimiento_qs.count(),
            "por_prioridad": por_prioridad,
            "por_tipo": por_tipo,
            "por_estado": por_estado,
            "sla_tabla": [
                {"prioridad": label, "horas": SLA_HORAS_POR_PRIORIDAD[value]}
                for value, label in PrioridadSupport.choices
            ],
            "tickets_sla_vencidos": list(
                sla_vencidos_qs.select_related("solicitado_por", "asignado_a")[:8]
            ),
            "tickets_sin_seguimiento": list(
                sin_seguimiento_qs.select_related("solicitado_por", "asignado_a")[:8]
            ),
        }
    }


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _end_of_month(start_date):
    if start_date.month == 12:
        next_month = date(start_date.year + 1, 1, 1)
    else:
        next_month = date(start_date.year, start_date.month + 1, 1)
    return next_month - timedelta(days=1)


def _month_bounds(value):
    if not value:
        return None, None
    try:
        year_str, month_str = value.split("-")
        year = int(year_str)
        month = int(month_str)
    except (ValueError, AttributeError):
        return None, None
    if month < 1 or month > 12:
        return None, None
    start = date(year, month, 1)
    return start, _end_of_month(start)


def _quick_range_bounds(value):
    if not value:
        return None, None
    today = timezone.localdate()
    if value == "last_7":
        return today - timedelta(days=6), today
    if value == "last_30":
        return today - timedelta(days=29), today
    if value == "this_month":
        start = date(today.year, today.month, 1)
        return start, _end_of_month(start)
    if value == "last_month":
        first_this_month = date(today.year, today.month, 1)
        last_month_end = first_this_month - timedelta(days=1)
        start = date(last_month_end.year, last_month_end.month, 1)
        return start, last_month_end
    if value == "this_year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    return None, None


def _apply_date_filters(items, field_name, start_date, end_date):
    if start_date:
        items = items.filter(**{f"{field_name}__gte": start_date})
    if end_date:
        items = items.filter(**{f"{field_name}__lte": end_date})
    return items


def _get_equipo_asignacion_activa(equipo):
    if not equipo:
        return None
    return (
        AsignacionEquipo.objects.select_related("personal")
        .filter(equipo=equipo, estado_asignacion=EstadoAsignacion.ACTIVA)
        .order_by("-fecha_asignacion")
        .first()
    )


def _get_equipo_responsable(equipo):
    asignacion = _get_equipo_asignacion_activa(equipo)
    if asignacion and asignacion.personal_id:
        return asignacion.personal
    return None


def _cerrar_asignaciones_activas(equipo, exclude_pk=None, observaciones=None):
    """Marca como Devuelta cualquier asignacion activa del equipo."""
    if not equipo:
        return 0
    qs = AsignacionEquipo.objects.filter(
        equipo=equipo,
        estado_asignacion=EstadoAsignacion.ACTIVA,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    now = timezone.now()
    updated = 0
    for asignacion in qs:
        asignacion.estado_asignacion = EstadoAsignacion.DEVUELTA
        if not asignacion.fecha_devolucion:
            asignacion.fecha_devolucion = now
        if observaciones and not asignacion.observaciones:
            asignacion.observaciones = observaciones
        asignacion.save(
            update_fields=["estado_asignacion", "fecha_devolucion", "observaciones"]
        )
        updated += 1
    return updated


def _reconciliar_estado_equipo(equipo, save=True):
    """
    Disponible/Asignado siguen a la asignacion activa.
    No toca Baja ni En Mantenimiento.
    """
    if not equipo:
        return None
    if equipo.estado_equipo in {EstadoEquipo.BAJA, EstadoEquipo.EN_MANTENIMIENTO}:
        return equipo
    tiene_activa = AsignacionEquipo.objects.filter(
        equipo=equipo,
        estado_asignacion=EstadoAsignacion.ACTIVA,
    ).exists()
    nuevo = EstadoEquipo.ASIGNADO if tiene_activa else EstadoEquipo.DISPONIBLE
    if equipo.estado_equipo != nuevo:
        equipo.estado_equipo = nuevo
        if save:
            equipo.save(update_fields=["estado_equipo"])
    return equipo


def _crear_movimiento(
    equipo,
    tipo_movimiento,
    origen=None,
    destino=None,
    responsable=None,
    observaciones=None,
    request=None,
):
    if not equipo:
        return None
    movimiento = MovimientoEquipo.objects.create(
        equipo=equipo,
        tipo_movimiento=tipo_movimiento,
        origen=str(origen) if origen else None,
        destino=str(destino) if destino else None,
        responsable=responsable,
        observaciones=observaciones or None,
    )
    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MOVIMIENTO_EQUIPO,
        accion=historial.AccionHistorial.OTRO,
        titulo=f"{tipo_movimiento}: {equipo.codigo_inventario}",
        descripcion=observaciones or "",
        objeto=movimiento,
        objeto_etiqueta=str(equipo),
        entidad_relacionada=equipo,
        enlace_nombre="movimientoequipo_detail",
        es_automatico=True,
        nivel=NivelHistorial.INFO,
        metadata={
            "tipo_movimiento": tipo_movimiento,
            "origen": str(origen) if origen else None,
            "destino": str(destino) if destino else None,
            "responsable": str(responsable) if responsable else None,
        },
    )
    return movimiento

# =========== Area views ==============
# Formulario de area 
class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = "__all__"
        labels = {
            "nombre_area": "Nombre del área",
            "descripcion_area": "Descripción del área",
        }
        help_texts = {
            "nombre_area": "Nombre con el que se identifica el área.",
            "descripcion_area": "Descripcion o cualquier detalle importante.",
        }
        widgets = {
            "descripcion_area": forms.Textarea(attrs={"rows": 4}),
        }

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


# ============  Puesto views ==============
# Formulario de puesto
class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = "__all__"
        labels = {
            "nombre_puesto": "Nombre del puesto",
            "descripcion_puesto": "Descripción del puesto",
        }
        help_texts = {
            "nombre_puesto": "Nombre con el que se identifica el puesto.",
            "descripcion_puesto": "Descripcion o cualquier detalle importante.",
        }
        widgets = {
            "descripcion_puesto": forms.Textarea(attrs={"rows": 4}),
        }

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


# ============  Personal views ==============
class PersonalForm(forms.ModelForm):
    account_action = forms.ChoiceField(
        choices=(
            ("none", "Sin usuario"),
            ("assign", "Asignar usuario existente"),
            ("create", "Crear usuario nuevo"),
        ),
        required=False,
        label="Tipo de Usuario",
    )
    rol = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        label="Rol del sistema",
        help_text="Solo administradores pueden cambiar el rol.",
    )
    user_existing = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        label="Usuario existente",
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        label="Nuevo usuario",
    )
    email = forms.EmailField(
        required=False,
        label="Correo del usuario",
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Contraseña",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Confirmar contrasena",
    )

    class Meta:
        model = Personal
        exclude = ["user", "admin_requested"]
        widgets = {
            "fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        User = get_user_model()
        qs = User.objects.filter(personal_profile__isnull=True)
        if self.instance and self.instance.pk and self.instance.user_id:
            qs = User.objects.filter(pk=self.instance.user_id) | qs
            self.fields["account_action"].initial = "assign"
            self.fields["user_existing"].initial = self.instance.user
        self.fields["user_existing"].queryset = qs.distinct()
        if not self.instance or not self.instance.pk:
            self.fields["account_action"].initial = "none"
        self.fields["account_action"].help_text = "Selecciona crear o asignar un usuario."
        self.account_fields = (
            "account_action",
            "user_existing",
            "username",
            "email",
            "password1",
            "password2",
        )
        if not is_admin_user(self.request_user):
            self.fields.pop("rol", None)
        elif "rol" in self.fields:
            current_user = self.instance.user if self.instance and self.instance.pk else None
            self.fields["rol"].initial = get_user_role(current_user) if current_user else ROLE_USUARIO

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("account_action") or "none"
        existing_user = cleaned.get("user_existing")
        username = (cleaned.get("username") or "").strip()
        email = (cleaned.get("email") or "").strip()
        password1 = cleaned.get("password1") or ""
        password2 = cleaned.get("password2") or ""

        if action == "none":
            if existing_user or username or email or password1 or password2:
                self.add_error(
                    "account_action",
                    "No llenes datos de usuario si eliges Sin usuario.",
                )
        elif action == "assign":
            if not existing_user:
                self.add_error("user_existing", "Selecciona un usuario.")
            if username or email or password1 or password2:
                self.add_error(
                    "username",
                    "No llenes los datos de usuario nuevo si asignas uno existente.",
                )
        elif action == "create":
            if existing_user:
                self.add_error(
                    "user_existing",
                    "No selecciones un usuario existente si vas a crear uno.",
                )
            if not username:
                self.add_error("username", "Captura un nombre de usuario.")
            elif get_user_model().objects.filter(username__iexact=username).exists():
                self.add_error("username", "Ese nombre de usuario ya existe.")
            if not email:
                self.add_error("email", "Captura un correo de usuario.")
            if not password1 or not password2:
                self.add_error("password1", "Captura la contraseña.")
            elif password1 != password2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(password1)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)

        if action == "assign" and existing_user:
            conflict_qs = Personal.objects.filter(user=existing_user)
            if self.instance and self.instance.pk:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)
            if conflict_qs.exists():
                self.add_error(
                    "user_existing",
                    "Ese usuario ya esta asignado a otro personal.",
                )

        if "rol" in cleaned and cleaned.get("rol") in {ROLE_TECNICO, ROLE_ADMIN}:
            if action == "none":
                self.add_error(
                    "rol",
                    "No puedes asignar Tecnico IT o Administrador sin usuario.",
                )

        return cleaned

    def save(self, commit=True):
        action = self.cleaned_data.get("account_action") or "none"
        rol = self.cleaned_data.get("rol") if "rol" in self.cleaned_data else None
        if action == "create":
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    username=self.cleaned_data["username"].strip(),
                    email=self.cleaned_data["email"].strip(),
                    password=self.cleaned_data["password1"],
                )
                set_user_role(user, rol or ROLE_USUARIO)
                personal = super().save(commit=False)
                personal.user = user
                personal.admin_requested = False
                if commit:
                    personal.save()
                return personal

        personal = super().save(commit=False)
        if action == "assign":
            personal.user = self.cleaned_data.get("user_existing")
        elif action == "none":
            personal.user = None
        if commit:
            personal.save()
            if rol and personal.user:
                set_user_role(personal.user, rol)
                if personal.admin_requested:
                    personal.admin_requested = False
                    personal.save(update_fields=["admin_requested"])
            elif personal.user and rol is None:
                # Sin campo rol (no admin): mantener rol actual o Usuario por defecto.
                if not get_user_role(personal.user):
                    set_user_role(personal.user, ROLE_USUARIO)
        return personal


def personal_list(request):
    items = Personal.objects.select_related("user", "area", "puesto").all()
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
        Personal.objects.select_related("user", "area", "puesto"),
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
    """Panel admin para previsualizar y aplicar archivar/purgar del historial."""
    from django.conf import settings as django_settings

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

        if accion == "archivar":
            resultado = {"archivo": historial.archivar_historial(), "purga": {"omitido": True}}
        elif accion == "purgar":
            resultado = {"archivo": {"omitido": True}, "purga": historial.purgar_historial()}
        else:
            resultado = historial.aplicar_retencion()

        archivados = (resultado.get("archivo") or {}).get("archivados", 0)
        purgados = (resultado.get("purga") or {}).get("purgados", 0)
        messages.success(
            request,
            f"Retencion aplicada. Archivados: {archivados}. Purgados: {purgados}.",
        )
        historial.registrar_historial(
            request=request,
            modulo=ModuloHistorial.SISTEMA,
            accion=historial.AccionHistorial.OTRO,
            titulo=f"Retencion de historial ({accion})",
            descripcion=f"Archivados={archivados}, Purgados={purgados}",
            nivel=NivelHistorial.ADVERTENCIA if accion in {"purgar", "ambos"} else NivelHistorial.INFO,
            es_automatico=False,
            metadata={"accion": accion, "resultado": resultado, "config": cfg},
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
    if request.method == "POST":
        form = PersonalForm(request.POST, instance=personal, request_user=request.user)
        if form.is_valid():
            personal = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.PERSONAL,
                titulo=f"Personal actualizado: {personal}",
                objeto=personal,
                form=form,
                enlace_nombre="personal_update",
            )
            messages.success(request, "Personal actualizado correctamente.")
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

# ============  Proveedor views ==============
# == Formulario de proveedor
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nombre_proveedor",
            "razon_social",
            "rfc",
            "tipo",
            "contacto",
            "correo",
            "telefono",
            "sitio_web",
            "direccion",
            "ciudad",
            "estado",
            "codigo_postal",
            "notas",
            "activo",
        ]
        labels = {
            "nombre_proveedor": "Nombre comercial",
            "razon_social": "Razon social",
            "rfc": "RFC",
            "tipo": "Tipo de proveedor",
            "contacto": "Contacto",
            "telefono": "Telefono",
            "correo": "Correo electronico",
            "sitio_web": "Sitio web",
            "direccion": "Direccion",
            "ciudad": "Ciudad",
            "estado": "Estado",
            "codigo_postal": "Codigo postal",
            "notas": "Notas / condiciones",
            "activo": "Activo",
        }
        help_texts = {
            "razon_social": "Nombre legal para facturacion, si difiere del comercial.",
            "rfc": "RFC para facturas y ordenes formales.",
            "contacto": "Nombre de la persona de contacto.",
            "notas": "Plazo de pago, garantia, observaciones, etc.",
        }
        widgets = {
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
            "sitio_web": forms.URLInput(attrs={"placeholder": "https://"}),
        }

    def clean_rfc(self):
        rfc = (self.cleaned_data.get("rfc") or "").strip().upper()
        return rfc or None

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
class EdificioForm(forms.ModelForm):
    class Meta:
        model = Edificio
        fields = "__all__"
        labels = {
            "nombre_edificio": "Nombre del edificio",
            "descripcion": "Descripción",
        }
        help_texts = {
            "descripcion": "Breve descripción del edificio.",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }

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

# ============  ZonaEdificio views ==============
class ZonaEdificioForm(forms.ModelForm):
    class Meta:
        model = ZonaEdificio
        fields = "__all__"
        labels = {
            "nombre_zona": "Nombre de la zona",
            "descripcion": "Descripción",
        }
        help_texts = {
            "descripcion": "Breve descripción de la zona.",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }

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

# ============  CategoriaEquipo views ==============
# Formulario de categoria de equipo
class CategoriaEquipoForm(forms.ModelForm):
    class Meta:
        model = CategoriaEquipo
        fields = "__all__"
        labels = {
            "nombre_categoria": "Nombre de la categoría",
            "descripcion_categoria": "Descripción",
        }
        help_texts = {
            "descripcion_categoria": "Breve descripción de la categoría.",
        }
        widgets = {
            "descripcion_categoria": forms.Textarea(attrs={"rows": 3}),
        }

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
EQUIPO_LIST_PAGE_SIZE = 20
EQUIPO_ASIGNACION_ALERTA_DIAS = 180
EQUIPO_MANTENIMIENTO_LARGO_DIAS = 14


def _equipo_queryset():
    return Equipo.objects.select_related(
        "categoria",
        "proveedor",
        "ubicacion",
        "ubicacion__edificio",
        "ubicacion__zona",
    )


def _equipos_sin_ubicacion_qs():
    return (
        _equipo_queryset()
        .filter(ubicacion__isnull=True)
        .exclude(estado_equipo=EstadoEquipo.BAJA)
        .filter(activo=True)
    )


def _equipos_mantenimiento_largo_qs(now=None, dias=EQUIPO_MANTENIMIENTO_LARGO_DIAS):
    now = now or timezone.now()
    limite = now - timedelta(days=dias)
    return (
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


def _asignaciones_antiguas_qs(today=None, dias=EQUIPO_ASIGNACION_ALERTA_DIAS):
    today = today or timezone.localdate()
    cutoff = today - timedelta(days=dias)
    return (
        AsignacionEquipo.objects.select_related("equipo", "personal", "equipo__categoria")
        .filter(
            estado_asignacion=EstadoAsignacion.ACTIVA,
            fecha_asignacion__date__lte=cutoff,
        )
        .exclude(equipo__estado_equipo=EstadoEquipo.BAJA)
        .order_by("fecha_asignacion", "pk")
    )


def _equipos_alerta_context(
    today=None,
    asignacion_dias=EQUIPO_ASIGNACION_ALERTA_DIAS,
    mant_dias=EQUIPO_MANTENIMIENTO_LARGO_DIAS,
):
    today = today or timezone.localdate()
    sin_ubicacion_qs = _equipos_sin_ubicacion_qs().order_by("codigo_inventario")
    mant_largo_qs = _equipos_mantenimiento_largo_qs(dias=mant_dias)
    asign_antiguas_qs = _asignaciones_antiguas_qs(today=today, dias=asignacion_dias)
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


def _equipo_dashboard_context(today=None):
    today = today or timezone.localdate()
    alerta = _equipos_alerta_context(today=today)
    qs = _equipo_queryset()

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


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = "__all__"
        labels = {
            "codigo_inventario": "Código de inventario (ID)",
            "numero_serie": "Número de serie",
            "marca": "Marca",
            "modelo": "Modelo",
            "categoria": "Categoría",
            "proveedor": "Proveedor",
            "Numero_Pedimiento": "Número de pedimiento",
            "descripcion_equipo": "Descripción del equipo",
            "estado_equipo": "Estado del equipo",
            "ubicacion": "Ubicación",
            "fecha_alta": "Fecha de alta",
            "fecha_baja": "Fecha de baja",
            "motivo_baja": "Motivo de baja",
            "activo": "Activo",
            "imagen": "Imagen",
        }
        help_texts = {
            "codigo_inventario": "Código único de inventario del equipo.",
            "numero_serie": "Número de serie del equipo.",
            "marca": "Marca del equipo.",
            "modelo": "Modelo del equipo.",
            "categoria": "Categoría a la que pertenece el equipo.",
            "proveedor": "Proveedor del equipo.",
            "Numero_Pedimiento": "Número de pedimiento del equipo(si aplica).",
            "descripcion_equipo": "Descripción detallada del equipo.",
            "estado_equipo": (
                "Disponible/Asignado se sincronizan con la asignacion activa. "
                "Usa En Mantenimiento/Baja con cuidado."
            ),
            "ubicacion": "Ubicación física del equipo.",
            "fecha_alta": "Fecha en que se dio de alta el equipo.",
            "fecha_baja": "Fecha en que se dio de baja el equipo (si aplica).",
        }
        widgets = {
            "descripcion_equipo": forms.Textarea(attrs={"rows": 4}),
            "fecha_alta": forms.DateInput(attrs={"type": "date"}),
            "fecha_baja": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        if not imagen:
            return imagen

        max_size = 50 * 1024 * 1024
        if imagen.size > max_size:
            raise forms.ValidationError("La imagen debe pesar menos de 50 MB.")

        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        content_type = getattr(imagen, "content_type", None)
        if content_type and content_type not in allowed_types:
            raise forms.ValidationError("Formato no permitido. Usa JPG, JPEG, PNG, GIF o WEBP.")

        return imagen


def _filtrar_equipos(request):
    items = _equipo_queryset().order_by("-fecha_alta", "-pk")
    search_query = (request.GET.get("q") or "").strip()
    selected_categoria = request.GET.get("categoria", "")
    selected_estado = request.GET.get("estado_equipo", "")
    selected_activo = request.GET.get("activo", "")
    selected_ubicacion = request.GET.get("ubicacion", "")
    selected_sin_ubicacion = request.GET.get("sin_ubicacion", "")
    selected_alerta = (request.GET.get("alerta") or "").strip()
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
        items = items.filter(ubicacion__isnull=True)
    elif selected_ubicacion:
        items = items.filter(ubicacion_id=selected_ubicacion)

    if selected_alerta == "sin_ubicacion":
        items = _equipos_sin_ubicacion_qs().order_by("codigo_inventario")
    elif selected_alerta == "mant_largo":
        items = _equipos_mantenimiento_largo_qs()
    elif selected_alerta == "asignacion_antigua":
        ids = _asignaciones_antiguas_qs(today=today).values_list("equipo_id", flat=True)
        items = _equipo_queryset().filter(pk__in=ids).order_by("codigo_inventario")
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
        "fecha_alta_desde": fecha_desde_raw,
        "fecha_alta_hasta": fecha_hasta_raw,
        "fecha_alta_mes": fecha_mes,
        "fecha_alta_rango": fecha_rango,
    }
    return items, filters


def _export_equipos_csv(queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="inventario_equipos.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Codigo",
            "Serie",
            "Marca",
            "Modelo",
            "Categoria",
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
    for equipo in queryset.select_related("categoria", "proveedor", "ubicacion"):
        writer.writerow(
            [
                equipo.codigo_inventario,
                equipo.numero_serie or "",
                equipo.marca or "",
                equipo.modelo or "",
                str(equipo.categoria) if equipo.categoria_id else "",
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


def equipo_list(request):
    items, filters = _filtrar_equipos(request)
    if (request.GET.get("export") or "").lower() == "csv":
        return _export_equipos_csv(items)

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
        "categoria_choices": CategoriaEquipo.objects.order_by(
            "nombre_categoria"
        ).values_list("id", "nombre_categoria"),
        "estado_choices": EstadoEquipo.choices,
        "ubicacion_choices": [(ubicacion.pk, str(ubicacion)) for ubicacion in ubicaciones],
        "equipos_asignacion_alerta_dias": EQUIPO_ASIGNACION_ALERTA_DIAS,
        "equipos_mant_largo_dias": EQUIPO_MANTENIMIENTO_LARGO_DIAS,
        **filters,
    }
    return render(request, "equipo/list.html", context)


def equipo_detail(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    asignacion_activa = _get_equipo_asignacion_activa(equipo)
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
            "asignacion_activa": asignacion_activa,
            "movimientos": movimientos,
            "asignaciones": asignaciones,
            "mantenimientos": mantenimientos,
            "tickets": tickets,
        },
    )


def equipo_create(request):
    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES)
        if form.is_valid():
            equipo = form.save()
            _reconciliar_estado_equipo(equipo)
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.EQUIPO,
                titulo=f"Equipo dado de alta: {equipo.codigo_inventario}",
                objeto=equipo,
                enlace_nombre="equipo_detail",
            )
            _crear_movimiento(
                equipo,
                TipoMovimiento.DADA_DE_ALTA,
                origen=None,
                destino=equipo.ubicacion,
                responsable=_get_equipo_responsable(equipo),
                request=request,
            )
            messages.success(request, "Equipo creado correctamente.")
            return redirect("equipo_detail", pk=equipo.pk)
    else:
        form = EquipoForm()
    return render(request, "equipo/form.html", {"form": form})


def equipo_update(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    ubicacion_anterior = equipo.ubicacion
    estado_anterior = equipo.estado_equipo
    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES, instance=equipo)
        if form.is_valid():
            equipo = form.save()
            _reconciliar_estado_equipo(equipo)
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.EQUIPO,
                titulo=f"Equipo actualizado: {equipo.codigo_inventario}",
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
            messages.success(request, "Equipo actualizado correctamente.")
            return redirect("equipo_detail", pk=equipo.pk)
    else:
        form = EquipoForm(instance=equipo)
    return render(request, "equipo/form.html", {"form": form, "object": equipo})


def equipo_delete(request, pk):
    equipo = get_object_or_404(_equipo_queryset(), pk=pk)
    if not equipo.puede_eliminar_fisico:
        messages.error(
            request,
            "No se puede eliminar: el equipo tiene historial (asignaciones, "
            "mantenimientos, tickets o movimientos). Usa Dar de baja.",
        )
        return redirect("equipo_detail", pk=pk)

    if request.method == "POST":
        etiqueta = equipo.codigo_inventario
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.EQUIPO,
            titulo=f"Equipo eliminado: {etiqueta}",
            objeto=equipo,
            metadata={"codigo_inventario": etiqueta},
            nivel=NivelHistorial.CRITICO,
        )
        equipo.delete()
        messages.success(request, "Equipo eliminado correctamente.")
        return redirect("equipo_list")
    return render(
        request,
        "equipo/confirm_delete.html",
        {"object": equipo, "puede_eliminar": True},
    )


class EquipoBajaForm(forms.Form):
    fecha_baja = forms.DateField(
        label="Fecha de baja",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    motivo_baja = forms.CharField(
        label="Motivo de baja",
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=255,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["fecha_baja"].initial = timezone.localdate()


class EquipoUbicacionForm(forms.Form):
    ubicacion = forms.ModelChoiceField(
        queryset=Ubicacion.objects.none(),
        required=False,
        label="Nueva ubicacion",
        empty_label="Sin ubicacion",
    )
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        max_length=255,
        widget=forms.TextInput(),
    )

    def __init__(self, *args, **kwargs):
        equipo = kwargs.pop("equipo", None)
        super().__init__(*args, **kwargs)
        self.fields["ubicacion"].queryset = Ubicacion.objects.select_related(
            "edificio", "zona"
        ).order_by(
            "edificio__nombre_edificio",
            "zona__nombre_zona",
            "referencia",
        )
        if equipo and not self.is_bound:
            self.fields["ubicacion"].initial = equipo.ubicacion_id


class EquipoAsignarForm(forms.Form):
    personal = forms.ModelChoiceField(
        queryset=Personal.objects.none(),
        label="Personal",
    )
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        max_length=255,
        widget=forms.TextInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["personal"].queryset = Personal.objects.order_by(
            "numero_empleado",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
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
    _crear_movimiento(
        equipo,
        TipoMovimiento.CAMBIO_ASIGNACION,
        origen=equipo.ubicacion,
        destino=equipo.ubicacion,
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
            "No se puede asignar este equipo (Baja, En Mantenimiento o inactivo).",
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
            _crear_movimiento(
                equipo,
                TipoMovimiento.CAMBIO_ASIGNACION if existente else TipoMovimiento.ASIGNACION,
                origen=equipo.ubicacion,
                destino=equipo.ubicacion,
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

    return render(
        request,
        "equipo/asignar.html",
        {"object": equipo, "form": form},
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

# ============  MovimientoEquipo views ==============
MOVIMIENTO_LIST_PAGE_SIZE = 25


def _movimiento_queryset():
    return MovimientoEquipo.objects.select_related(
        "equipo",
        "equipo__categoria",
        "responsable",
    )


def _filtrar_movimientos(request):
    items = _movimiento_queryset().order_by("-fecha_movimiento", "-pk")
    search_query = (request.GET.get("q") or "").strip()
    selected_tipo = request.GET.get("tipo_movimiento", "")
    selected_equipo = request.GET.get("equipo", "")
    fecha_desde_raw = request.GET.get("fecha_desde", "")
    fecha_hasta_raw = request.GET.get("fecha_hasta", "")

    if search_query:
        items = items.filter(
            Q(equipo__codigo_inventario__icontains=search_query)
            | Q(origen__icontains=search_query)
            | Q(destino__icontains=search_query)
            | Q(observaciones__icontains=search_query)
            | Q(responsable__nombre__icontains=search_query)
            | Q(responsable__apellido_paterno__icontains=search_query)
        )
    if selected_tipo:
        items = items.filter(tipo_movimiento=selected_tipo)
    if selected_equipo:
        items = items.filter(equipo_id=selected_equipo)

    fecha_desde = _parse_date(fecha_desde_raw)
    fecha_hasta = _parse_date(fecha_hasta_raw)
    items = _apply_date_filters(items, "fecha_movimiento", fecha_desde, fecha_hasta)

    filters = {
        "search_query": search_query,
        "selected_tipo": selected_tipo,
        "selected_equipo": selected_equipo,
        "fecha_desde": fecha_desde_raw,
        "fecha_hasta": fecha_hasta_raw,
    }
    return items, filters


def _export_movimientos_csv(queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="movimientos_equipo.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Fecha",
            "Equipo",
            "Tipo",
            "Origen",
            "Destino",
            "Responsable",
            "Observaciones",
        ]
    )
    for item in queryset:
        writer.writerow(
            [
                timezone.localtime(item.fecha_movimiento).strftime("%Y-%m-%d %H:%M")
                if item.fecha_movimiento
                else "",
                str(item.equipo) if item.equipo_id else "",
                item.tipo_movimiento,
                item.origen or "",
                item.destino or "",
                str(item.responsable) if item.responsable_id else "",
                item.observaciones or "",
            ]
        )
    return response


class MovimientoEquipoForm(forms.ModelForm):
    ubicacion_origen = forms.ModelChoiceField(
        queryset=Ubicacion.objects.none(),
        required=False,
        label="Ubicacion origen",
    )
    ubicacion_destino = forms.ModelChoiceField(
        queryset=Ubicacion.objects.none(),
        required=False,
        label="Ubicacion destino",
    )

    class Meta:
        model = MovimientoEquipo
        fields = [
            "equipo",
            "tipo_movimiento",
            "ubicacion_origen",
            "ubicacion_destino",
            "responsable",
            "observaciones",
        ]
        labels = {
            "equipo": "Equipo",
            "tipo_movimiento": "Tipo de movimiento",
            "ubicacion_origen": "Ubicacion origen",
            "ubicacion_destino": "Ubicacion destino",
            "responsable": "Responsable",
            "observaciones": "Observaciones",
        }
        help_texts = {
            "responsable": "Responsable actual del equipo.",
            "observaciones": "Opcional. Puedes agregar comentarios sobre el movimiento.",
            "tipo_movimiento": (
                "Preferible usar las acciones del detalle del equipo "
                "(asignar, devolver, ubicacion, baja). Este registro es solo auditoria."
            ),
        }
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ubicacion_origen"].label = "Ubicacion actual"
        self.fields["ubicacion_destino"].label = "Nueva ubicacion"
        self.fields["ubicacion_origen"].disabled = True
        self.fields["responsable"].disabled = True
        self.fields["responsable"].help_text = "Se toma de la asignacion activa del equipo."

        ubicaciones = Ubicacion.objects.select_related("edificio", "zona").order_by(
            "edificio__nombre_edificio",
            "zona__nombre_zona",
            "referencia",
        )
        self.fields["ubicacion_origen"].queryset = ubicaciones
        self.fields["ubicacion_destino"].queryset = ubicaciones

        equipo = None
        if self.instance and self.instance.pk and self.instance.equipo_id:
            equipo = self.instance.equipo
        elif self.data.get("equipo"):
            try:
                equipo = Equipo.objects.select_related("ubicacion").get(
                    pk=self.data.get("equipo")
                )
            except (Equipo.DoesNotExist, ValueError, TypeError):
                equipo = None

        if equipo and equipo.ubicacion_id:
            self.fields["ubicacion_origen"].initial = equipo.ubicacion_id

        asignacion = _get_equipo_asignacion_activa(equipo)
        if asignacion and asignacion.personal_id:
            self.fields["responsable"].initial = asignacion.personal_id

    def save(self, commit=True):
        instance = super().save(commit=False)
        equipo = self.cleaned_data.get("equipo")
        origen = self.cleaned_data.get("ubicacion_origen")
        destino = self.cleaned_data.get("ubicacion_destino")

        asignacion = _get_equipo_asignacion_activa(equipo)
        if asignacion and asignacion.personal_id:
            instance.responsable = asignacion.personal
        else:
            instance.responsable = self.cleaned_data.get("responsable")

        if not origen and equipo and equipo.ubicacion_id:
            origen = equipo.ubicacion
        instance.origen = str(origen) if origen else None
        instance.destino = str(destino) if destino else None

        if commit:
            instance.save()
            self.save_m2m()
            if equipo and destino and equipo.ubicacion_id != destino.pk:
                equipo.ubicacion = destino
                equipo.save(update_fields=["ubicacion"])
        return instance


def movimientoequipo_list(request):
    items = HistorialActividad.objects.select_related("usuario").order_by("-fecha")
    selected_modulo = request.GET.get("modulo", "")
    selected_accion = request.GET.get("accion", "")
    selected_nivel = request.GET.get("nivel", "")
    selected_origen = request.GET.get("origen", "")  # automatico | manual | ""
    selected_estado = request.GET.get("estado", "activo")  # activo | archivado | todos
    busqueda = (request.GET.get("q") or "").strip()
    fecha_desde = _parse_date(request.GET.get("fecha_desde"))
    fecha_hasta = _parse_date(request.GET.get("fecha_hasta"))

    if selected_estado == "activo" or selected_estado == "":
        items = items.filter(archivado=False)
    elif selected_estado == "archivado":
        items = items.filter(archivado=True)
    # "todos" no filtra por archivado

    if selected_modulo:
        items = items.filter(modulo=selected_modulo)
    if selected_accion:
        items = items.filter(accion=selected_accion)
    if selected_nivel:
        items = items.filter(nivel=selected_nivel)
    if selected_origen == "automatico":
        items = items.filter(es_automatico=True)
    elif selected_origen == "manual":
        items = items.filter(es_automatico=False)
    if busqueda:
        items = items.filter(
            Q(titulo__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(objeto_etiqueta__icontains=busqueda)
            | Q(entidad_relacionada_etiqueta__icontains=busqueda)
        )
    items = _apply_date_filters(items, "fecha", fecha_desde, fecha_hasta)

    context = {
        "items": items[:500],
        "modulo_choices": ModuloHistorial.choices,
        "accion_choices": historial.AccionHistorial.choices,
        "nivel_choices": NivelHistorial.choices,
        "selected_modulo": selected_modulo,
        "selected_accion": selected_accion,
        "selected_nivel": selected_nivel,
        "selected_origen": selected_origen,
        "selected_estado": selected_estado or "activo",
        "busqueda": busqueda,
        "fecha_desde": request.GET.get("fecha_desde", ""),
        "fecha_hasta": request.GET.get("fecha_hasta", ""),
    }
    return render(request, "movimientoequipo/list.html", context)


def movimientoequipo_registros(request):
    items, filters = _filtrar_movimientos(request)
    if (request.GET.get("export") or "").lower() == "csv":
        return _export_movimientos_csv(items)

    paginator = Paginator(items, MOVIMIENTO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "items": page_obj,
        "page_obj": page_obj,
        "tipo_choices": TipoMovimiento.choices,
        "equipo_choices": Equipo.objects.order_by("codigo_inventario").values_list(
            "id", "codigo_inventario"
        ),
        **filters,
    }
    return render(request, "movimientoequipo/registros.html", context)


def movimientoequipo_detail(request, pk):
    movimiento = get_object_or_404(_movimiento_queryset(), pk=pk)
    return render(
        request,
        "movimientoequipo/detail.html",
        {
            "object": movimiento,
            "equipo": movimiento.equipo,
        },
    )


def movimientoequipo_equipo_info(request):
    equipo_id = request.GET.get("equipo_id")
    data = {
        "ubicacion_id": "",
        "ubicacion_label": "",
        "responsable_id": "",
        "responsable_label": "",
    }
    if equipo_id:
        try:
            equipo = Equipo.objects.select_related("ubicacion").get(pk=equipo_id)
        except (Equipo.DoesNotExist, ValueError, TypeError):
            equipo = None

        if equipo and equipo.ubicacion_id:
            data["ubicacion_id"] = str(equipo.ubicacion_id)
            data["ubicacion_label"] = str(equipo.ubicacion)

        asignacion = _get_equipo_asignacion_activa(equipo)
        if asignacion and asignacion.personal_id:
            data["responsable_id"] = str(asignacion.personal_id)
            data["responsable_label"] = str(asignacion.personal)

    return JsonResponse(data)


def movimientoequipo_create(request):
    if request.method == "POST":
        form = MovimientoEquipoForm(request.POST)
        if form.is_valid():
            movimiento = form.save()
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.MOVIMIENTO_EQUIPO,
                accion=historial.AccionHistorial.CREACION,
                titulo=f"Movimiento manual: {movimiento.equipo}",
                descripcion=movimiento.observaciones or "",
                objeto=movimiento,
                enlace_nombre="movimientoequipo_detail",
                metadata={"tipo_movimiento": movimiento.tipo_movimiento},
            )
            messages.success(
                request,
                "Movimiento registrado. Queda como auditoria (no editable).",
            )
            return redirect("movimientoequipo_detail", pk=movimiento.pk)
    else:
        initial = {}
        equipo_id = request.GET.get("equipo")
        if equipo_id and str(equipo_id).isdigit():
            initial["equipo"] = int(equipo_id)
        form = MovimientoEquipoForm(initial=initial)
    return render(request, "movimientoequipo/form.html", {"form": form})


def movimientoequipo_update(request, pk):
    messages.warning(
        request,
        "Los movimientos son solo auditoria y no se pueden editar.",
    )
    return redirect("movimientoequipo_detail", pk=pk)


def movimientoequipo_delete(request, pk):
    messages.warning(
        request,
        "Los movimientos son solo auditoria y no se pueden eliminar.",
    )
    return redirect("movimientoequipo_detail", pk=pk)

# ============  AsignacionEquipo views ==============
# Formulario de asignacion de equipo
class AsignacionEquipoForm(forms.ModelForm):
    class Meta:
        model = AsignacionEquipo
        fields = "__all__"
        labels = {
            "equipo": "Equipo",
            "personal": "Personal",
            "fecha_asignacion": "Fecha de asignación",
            "fecha_devolucion": "Fecha de devolución",
            "estado_asignacion": "Estado de asignación",
            "observaciones": "Observaciones",
        }
        help_texts = {
            "observaciones": "Observaciones o notas a tomar encuenta.",
            "estado_asignacion": (
                "Activa pone el equipo en Asignado. Devuelta/Extraviada lo libera "
                "(si no hay otra activa)."
            ),
        }
        widgets = {
            "fecha_asignacion": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "fecha_devolucion": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fecha_devolucion = self.fields.get("fecha_devolucion")
        if fecha_devolucion:
            fecha_devolucion.widget = forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            )
            fecha_devolucion.input_formats = ["%Y-%m-%dT%H:%M"]
        equipo_field = self.fields.get("equipo")
        if equipo_field:
            if self.instance and self.instance.pk:
                equipo_field.queryset = Equipo.objects.order_by("codigo_inventario")
            else:
                equipo_field.queryset = (
                    Equipo.objects.exclude(
                        estado_equipo__in=[EstadoEquipo.BAJA, EstadoEquipo.EN_MANTENIMIENTO]
                    )
                    .filter(activo=True)
                    .order_by("codigo_inventario")
                )

    def clean(self):
        cleaned = super().clean()
        equipo = cleaned.get("equipo")
        estado = cleaned.get("estado_asignacion") or EstadoAsignacion.ACTIVA
        if equipo and estado == EstadoAsignacion.ACTIVA:
            if equipo.estado_equipo == EstadoEquipo.BAJA:
                raise ValidationError("No se puede asignar un equipo en Baja.")
            if equipo.estado_equipo == EstadoEquipo.EN_MANTENIMIENTO:
                raise ValidationError(
                    "No se puede asignar un equipo En Mantenimiento. "
                    "Cierra o cancela el mantenimiento primero."
                )
            if not equipo.activo:
                raise ValidationError("No se puede asignar un equipo inactivo.")
        if estado in {EstadoAsignacion.DEVUELTA, EstadoAsignacion.EXTRAVIADA}:
            if not cleaned.get("fecha_devolucion"):
                cleaned["fecha_devolucion"] = timezone.now()
        return cleaned


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
class MantenimientoForm(forms.ModelForm):
    tecnico_responsable = forms.ChoiceField(
        required=False,
        choices=(),
        label="Tecnico responsable",
    )
    proveedor_responsable = forms.ModelChoiceField(
        queryset=Proveedor.objects.none(),
        required=False,
        label="Proveedor",
    )

    class Meta:
        model = Mantenimiento
        fields = [
            "equipo",
            "tipo_mantenimiento",
            "fecha_programada",
            "tecnico_responsable",
            "costo_mantenimiento",
            "descripcion_falla",
        ]
        labels = {
            "equipo": "Equipo",
            "tipo_mantenimiento": "Tipo de mantenimiento",
            "fecha_programada": "Fecha programada",
            "tecnico_responsable": "Técnico responsable",
            "proveedor_responsable": "Proveedor responsable",
            "costo_mantenimiento": "Costo del mantenimiento",
            "descripcion_falla": "Descripción de la falla o razón",
        }
        help_texts = {
            "descripcion_falla": "Describe la falla o razón del mantenimiento.",
            "costo_mantenimiento": "Costo estimado o real del mantenimiento.",
        }
        widgets = {
            "fecha_programada": forms.DateInput(attrs={"type": "date"}),
            "descripcion_falla": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "equipo" in self.fields:
            self.fields["equipo"].label_from_instance = (
                lambda obj: f"{obj.codigo_inventario} - {obj.categoria}"
            )

        User = get_user_model()
        user_qs = User.objects.filter(is_staff=True)
        if any(field.name == "is_active" for field in User._meta.fields):
            user_qs = user_qs.filter(is_active=True)
        user_qs = user_qs.order_by(User.USERNAME_FIELD)

        choices = [("", "---------"), ("Proveedores", "Proveedores")]
        for user in user_qs:
            label = user.get_full_name().strip()
            if not label:
                try:
                    personal = user.personal_profile
                except Personal.DoesNotExist:
                    personal = None
                if personal:
                    label_parts = [
                        personal.nombre,
                        personal.apellido_paterno,
                        personal.apellido_materno,
                    ]
                    label = " ".join(part for part in label_parts if part)
            if not label:
                label = (
                    getattr(user, User.USERNAME_FIELD, "")
                    or getattr(user, "email", "")
                    or f"Usuario {user.pk}"
                )
            value = getattr(user, User.USERNAME_FIELD, "") or str(user.pk)
            choices.append((value, label))
        current_value = (self.instance.tecnico_responsable or "").strip()
        if current_value and current_value not in {value for value, _ in choices}:
            choices.append((current_value, current_value))
        self.fields["tecnico_responsable"].choices = choices

        proveedores = Proveedor.objects.filter(activo=True).order_by("nombre_proveedor")
        self.fields["proveedor_responsable"].queryset = proveedores
        if current_value.lower().startswith("proveedor:"):
            self.fields["tecnico_responsable"].initial = "Proveedores"
            nombre = current_value.split(":", 1)[1].strip()
            if nombre:
                proveedor = proveedores.filter(nombre_proveedor__iexact=nombre).first()
                if proveedor:
                    self.fields["proveedor_responsable"].initial = proveedor.pk

        self.order_fields([
            "equipo",
            "tipo_mantenimiento",
            "fecha_programada",
            "tecnico_responsable",
            "proveedor_responsable",
            "costo_mantenimiento",
            "descripcion_falla",
        ])

    def clean(self):
        cleaned = super().clean()
        tecnico = (cleaned.get("tecnico_responsable") or "").strip()
        proveedor = cleaned.get("proveedor_responsable")
        if tecnico == "Proveedores":
            if not proveedor:
                self.add_error("proveedor_responsable", "Selecciona un proveedor.")
            else:
                cleaned["tecnico_responsable"] = (
                    f"Proveedor: {proveedor.nombre_proveedor}"
                )
        elif proveedor:
            cleaned["proveedor_responsable"] = None
        return cleaned


def _estado_equipo_tras_mantenimiento(equipo):
    if not equipo or equipo.estado_equipo == EstadoEquipo.BAJA:
        return EstadoEquipo.BAJA if equipo else None
    if AsignacionEquipo.objects.filter(
        equipo=equipo,
        estado_asignacion=EstadoAsignacion.ACTIVA,
    ).exists():
        return EstadoEquipo.ASIGNADO
    return EstadoEquipo.DISPONIBLE


def _sync_equipo_inicio_mantenimiento(mantenimiento, request=None):
    equipo = mantenimiento.equipo
    if not equipo or equipo.estado_equipo == EstadoEquipo.BAJA:
        raise ValidationError("No se puede iniciar mantenimiento sobre un equipo en Baja.")
    if equipo.estado_equipo == EstadoEquipo.EN_MANTENIMIENTO:
        return equipo
    equipo.estado_equipo = EstadoEquipo.EN_MANTENIMIENTO
    equipo.save(update_fields=["estado_equipo"])
    _crear_movimiento(
        equipo,
        TipoMovimiento.MANTENIMIENTO,
        origen=equipo.ubicacion,
        destino=equipo.ubicacion,
        responsable=_get_equipo_responsable(equipo),
        observaciones=f"Inicio mantenimiento {mantenimiento.folio_mantenimiento()}",
        request=request,
    )
    return equipo


def _sync_equipo_fin_mantenimiento(mantenimiento, request=None):
    equipo = mantenimiento.equipo
    if not equipo or equipo.estado_equipo != EstadoEquipo.EN_MANTENIMIENTO:
        return equipo
    # Si otro mantenimiento sigue En Proceso sobre el mismo equipo, no restaurar.
    otros_activos = (
        Mantenimiento.objects.filter(
            equipo=equipo,
            estado_mantenimiento=EstadoMantenimiento.EN_PROCESO,
        )
        .exclude(pk=mantenimiento.pk)
        .exists()
    )
    if otros_activos:
        return equipo
    nuevo_estado = _estado_equipo_tras_mantenimiento(equipo)
    if nuevo_estado and nuevo_estado != equipo.estado_equipo:
        equipo.estado_equipo = nuevo_estado
        equipo.save(update_fields=["estado_equipo"])
        _crear_movimiento(
            equipo,
            TipoMovimiento.MANTENIMIENTO,
            origen=equipo.ubicacion,
            destino=equipo.ubicacion,
            responsable=_get_equipo_responsable(equipo),
            observaciones=(
                f"Fin mantenimiento {mantenimiento.folio_mantenimiento()} "
                f"→ {nuevo_estado}"
            ),
            request=request,
        )
    return equipo


MANTENIMIENTO_ALERTA_DIAS = 7
MANTENIMIENTO_PROXIMOS_DIAS = 30
MANTENIMIENTO_LIST_PAGE_SIZE = 20


def _mantenimiento_queryset():
    return Mantenimiento.objects.select_related("equipo", "equipo__categoria", "cierre")


def _mantenimientos_activos_qs():
    return _mantenimiento_queryset().filter(
        estado_mantenimiento__in=[
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        ]
    )


def _equipos_con_mantenimiento_activo_ids():
    return (
        Mantenimiento.objects.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ]
        )
        .values_list("equipo_id", flat=True)
        .distinct()
    )


def _proximos_ciclos_mantenimiento_qs(today=None, horizon_days=MANTENIMIENTO_ALERTA_DIAS):
    """Cierres con proxima_fecha pendiente y sin mantenimiento abierto del mismo equipo."""
    today = today or timezone.localdate()
    return (
        AgendaMantenimiento.objects.select_related(
            "mantenimiento",
            "mantenimiento__equipo",
        )
        .filter(
            proxima_fecha_mantenimiento__isnull=False,
            mantenimiento__estado_mantenimiento=EstadoMantenimiento.COMPLETADO,
            proxima_fecha_mantenimiento__lte=today + timedelta(days=horizon_days),
        )
        .exclude(mantenimiento__equipo_id__in=_equipos_con_mantenimiento_activo_ids())
        .order_by("proxima_fecha_mantenimiento", "pk")
    )


def _mantenimientos_alerta_context(
    today=None,
    horizon_days=MANTENIMIENTO_ALERTA_DIAS,
    proximos_days=MANTENIMIENTO_PROXIMOS_DIAS,
):
    today = today or timezone.localdate()
    activos = _mantenimientos_activos_qs()
    vencidos_qs = activos.filter(fecha_programada__lt=today).order_by(
        "fecha_programada", "pk"
    )
    por_vencer_qs = activos.filter(
        fecha_programada__gte=today,
        fecha_programada__lte=today + timedelta(days=horizon_days),
    ).order_by("fecha_programada", "pk")
    proximos_30_qs = activos.filter(
        fecha_programada__gte=today,
        fecha_programada__lte=today + timedelta(days=proximos_days),
    ).order_by("fecha_programada", "pk")
    ciclos_qs = _proximos_ciclos_mantenimiento_qs(today=today, horizon_days=horizon_days)
    ciclos_vencidos_qs = ciclos_qs.filter(proxima_fecha_mantenimiento__lt=today)
    ciclos_por_vencer_qs = ciclos_qs.filter(proxima_fecha_mantenimiento__gte=today)
    return {
        "mantenimientos_vencidos": list(vencidos_qs[:8]),
        "mantenimientos_por_vencer": list(por_vencer_qs[:8]),
        "mantenimientos_proximos_lista": list(proximos_30_qs[:6]),
        "mantenimientos_ciclos": list(ciclos_qs[:8]),
        "mantenimientos_vencidos_count": vencidos_qs.count(),
        "mantenimientos_por_vencer_count": por_vencer_qs.count(),
        "mantenimientos_proximos_count": proximos_30_qs.count(),
        "mantenimientos_ciclos_count": ciclos_qs.count(),
        "mantenimientos_ciclos_vencidos_count": ciclos_vencidos_qs.count(),
        "mantenimientos_ciclos_por_vencer_count": ciclos_por_vencer_qs.count(),
        "mantenimientos_alerta_dias": horizon_days,
        "mantenimientos_proximos_dias": proximos_days,
    }


def _parse_date_param(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _crear_proximo_mantenimiento_desde_cierre(agenda, crear=True):
    """
    Si el cierre trae proxima_fecha y crear=True, programa el siguiente ciclo
    (Programado) salvo que el equipo ya tenga uno abierto.
    """
    if not crear:
        return None, "omitido"
    proxima = agenda.proxima_fecha_mantenimiento
    if not proxima:
        return None, "sin_fecha"

    origen = agenda.mantenimiento
    equipo = origen.equipo
    abiertos = Mantenimiento.objects.filter(
        equipo=equipo,
        estado_mantenimiento__in=[
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        ],
    )
    if abiertos.exists():
        return abiertos.order_by("fecha_programada").first(), "ya_abierto"

    existente = Mantenimiento.objects.filter(
        equipo=equipo,
        fecha_programada=proxima,
        estado_mantenimiento=EstadoMantenimiento.PROGRAMADO,
    ).first()
    if existente:
        return existente, "ya_programado"

    tipo = origen.tipo_mantenimiento or TipoMantenimiento.PREVENTIVO
    if tipo == TipoMantenimiento.CORRECTIVO:
        tipo = TipoMantenimiento.PREVENTIVO

    nuevo = Mantenimiento.objects.create(
        equipo=equipo,
        tipo_mantenimiento=tipo,
        estado_mantenimiento=EstadoMantenimiento.PROGRAMADO,
        fecha_programada=proxima,
        tecnico_responsable=origen.tecnico_responsable,
        costo_mantenimiento=0,
        descripcion_falla=(
            f"Ciclo automatico tras {origen.folio_mantenimiento()}."
        ),
    )
    return nuevo, "creado"


def _mantenimiento_dashboard_context(today=None):
    today = today or timezone.localdate()
    alerta = _mantenimientos_alerta_context(today=today)
    qs = _mantenimiento_queryset()
    activos = _mantenimientos_activos_qs()

    por_estado = []
    for value, label in EstadoMantenimiento.choices:
        por_estado.append(
            {
                "value": value,
                "label": label,
                "count": qs.filter(estado_mantenimiento=value).count(),
            }
        )

    por_tipo = []
    for value, label in TipoMantenimiento.choices:
        por_tipo.append(
            {
                "value": value,
                "label": label,
                "count": activos.filter(tipo_mantenimiento=value).count(),
                "total": qs.filter(tipo_mantenimiento=value).count(),
            }
        )

    costo_completados = (
        qs.filter(estado_mantenimiento=EstadoMantenimiento.COMPLETADO).aggregate(
            total=Sum("costo_mantenimiento")
        )["total"]
        or 0
    )
    costo_activos = activos.aggregate(total=Sum("costo_mantenimiento"))["total"] or 0

    por_equipo = list(
        qs.values(
            "equipo_id",
            "equipo__codigo_inventario",
        )
        .annotate(total=Count("id"))
        .order_by("-total", "equipo__codigo_inventario")[:8]
    )

    return {
        "mantenimiento_dashboard": {
            "total": qs.count(),
            "activos": activos.count(),
            "completados": qs.filter(
                estado_mantenimiento=EstadoMantenimiento.COMPLETADO
            ).count(),
            "cancelados": qs.filter(
                estado_mantenimiento=EstadoMantenimiento.CANCELADO
            ).count(),
            "vencidos": alerta["mantenimientos_vencidos_count"],
            "por_vencer": alerta["mantenimientos_por_vencer_count"],
            "proximos_30": alerta["mantenimientos_proximos_count"],
            "ciclos": alerta["mantenimientos_ciclos_count"],
            "costo_completados": costo_completados,
            "costo_activos": costo_activos,
            "por_estado": por_estado,
            "por_tipo": por_tipo,
            "por_equipo": por_equipo,
            "lista_vencidos": alerta["mantenimientos_vencidos"],
            "lista_por_vencer": alerta["mantenimientos_por_vencer"],
            "lista_ciclos": alerta["mantenimientos_ciclos"],
            "alerta_dias": alerta["mantenimientos_alerta_dias"],
            "proximos_dias": alerta["mantenimientos_proximos_dias"],
        }
    }


def mantenimiento_dashboard(request):
    return render(
        request,
        "mantenimiento/dashboard.html",
        {
            "today": timezone.localdate(),
            **_mantenimiento_dashboard_context(),
        },
    )


def mantenimiento_list(request):
    items = _mantenimiento_queryset()
    search_query = (request.GET.get("q") or "").strip()
    selected_alerta = (request.GET.get("alerta") or "").strip()
    selected_estado = (request.GET.get("estado") or "").strip()
    selected_tipo = (request.GET.get("tipo") or "").strip()
    selected_equipo = (request.GET.get("equipo") or "").strip()
    selected_tecnico = (request.GET.get("tecnico") or "").strip()
    selected_orden = (request.GET.get("orden") or "programada").strip()
    fecha_desde = _parse_date_param(request.GET.get("fecha_desde"))
    fecha_hasta = _parse_date_param(request.GET.get("fecha_hasta"))
    today = timezone.localdate()
    horizon = today + timedelta(days=MANTENIMIENTO_ALERTA_DIAS)

    if search_query:
        folio_q = Q(
            equipo__codigo_inventario__icontains=search_query
        ) | Q(
            equipo__numero_serie__icontains=search_query
        ) | Q(
            equipo__marca__icontains=search_query
        ) | Q(
            equipo__modelo__icontains=search_query
        ) | Q(
            tecnico_responsable__icontains=search_query
        ) | Q(
            descripcion_falla__icontains=search_query
        ) | Q(
            tipo_mantenimiento__icontains=search_query
        )
        digits = "".join(ch for ch in search_query if ch.isdigit())
        if digits.isdigit():
            folio_q |= Q(pk=int(digits))
        items = items.filter(folio_q)

    if selected_estado:
        items = items.filter(estado_mantenimiento=selected_estado)
    if selected_tipo:
        items = items.filter(tipo_mantenimiento=selected_tipo)
    if selected_equipo.isdigit():
        items = items.filter(equipo_id=int(selected_equipo))
    if selected_tecnico:
        items = items.filter(tecnico_responsable=selected_tecnico)
    if fecha_desde:
        items = items.filter(fecha_programada__gte=fecha_desde)
    if fecha_hasta:
        items = items.filter(fecha_programada__lte=fecha_hasta)

    if selected_alerta == "vencidos":
        items = items.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            fecha_programada__lt=today,
        )
    elif selected_alerta == "proximos":
        items = items.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            fecha_programada__gte=today,
            fecha_programada__lte=horizon,
        )
    elif selected_alerta == "atencion":
        items = items.filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            fecha_programada__lte=horizon,
        )
    elif selected_alerta == "ciclo":
        ciclos = _proximos_ciclos_mantenimiento_qs(today=today)
        items = items.filter(pk__in=ciclos.values_list("mantenimiento_id", flat=True))

    order_map = {
        "programada": ("fecha_programada", "pk"),
        "programada_desc": ("-fecha_programada", "-pk"),
        "reciente": ("-pk",),
        "estado": ("estado_mantenimiento", "fecha_programada", "pk"),
        "equipo": ("equipo__codigo_inventario", "fecha_programada", "pk"),
    }
    if selected_alerta in {"vencidos", "proximos", "atencion"}:
        items = items.order_by("fecha_programada", "pk")
    elif selected_alerta == "ciclo":
        items = items.order_by("cierre__proxima_fecha_mantenimiento", "pk")
    else:
        items = items.order_by(*order_map.get(selected_orden, order_map["programada"]))

    paginator = Paginator(items, MANTENIMIENTO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    tecnicos = (
        Mantenimiento.objects.exclude(tecnico_responsable__isnull=True)
        .exclude(tecnico_responsable="")
        .values_list("tecnico_responsable", flat=True)
        .distinct()
        .order_by("tecnico_responsable")
    )
    equipos = (
        Equipo.objects.filter(mantenimientos__isnull=False)
        .distinct()
        .order_by("codigo_inventario")
    )

    return render(
        request,
        "mantenimiento/list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "selected_alerta": selected_alerta,
            "selected_estado": selected_estado,
            "selected_tipo": selected_tipo,
            "selected_equipo": selected_equipo,
            "selected_tecnico": selected_tecnico,
            "selected_orden": selected_orden,
            "fecha_desde": fecha_desde.isoformat() if fecha_desde else "",
            "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else "",
            "estado_choices": EstadoMantenimiento.choices,
            "tipo_choices": TipoMantenimiento.choices,
            "equipo_choices": equipos,
            "tecnico_choices": tecnicos,
            "mantenimientos_alerta_dias": MANTENIMIENTO_ALERTA_DIAS,
            "today": today,
            "alerta_hasta": horizon,
        },
    )


def mantenimiento_detail(request, pk):
    mantenimiento = get_object_or_404(_mantenimiento_queryset(), pk=pk)
    cierre = getattr(mantenimiento, "cierre", None)
    return render(
        request,
        "mantenimiento/detail.html",
        {
            "object": mantenimiento,
            "cierre": cierre,
        },
    )


def mantenimiento_create(request):
    if request.method == "POST":
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            mantenimiento = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Mantenimiento programado: {mantenimiento.folio_mantenimiento()}",
                objeto=mantenimiento,
                entidad_relacionada=mantenimiento.equipo,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=mantenimiento.pk,
            )
            messages.success(request, "Mantenimiento creado correctamente.")
            return redirect("mantenimiento_detail", pk=mantenimiento.pk)
    else:
        initial = {}
        equipo_id = request.GET.get("equipo")
        fecha = request.GET.get("fecha")
        if equipo_id:
            initial["equipo"] = equipo_id
        if fecha:
            initial["fecha_programada"] = fecha
        form = MantenimientoForm(initial=initial)
    return render(request, "mantenimiento/form.html", {"form": form})


def mantenimiento_update(request, pk):
    mantenimiento = get_object_or_404(_mantenimiento_queryset(), pk=pk)
    if request.method == "POST":
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        if form.is_valid():
            mantenimiento = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Mantenimiento actualizado: {mantenimiento.folio_mantenimiento()}",
                objeto=mantenimiento,
                form=form,
                entidad_relacionada=mantenimiento.equipo,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=mantenimiento.pk,
            )
            messages.success(request, "Mantenimiento actualizado correctamente.")
            return redirect("mantenimiento_detail", pk=mantenimiento.pk)
    else:
        form = MantenimientoForm(instance=mantenimiento)
    return render(
        request,
        "mantenimiento/form.html",
        {"form": form, "object": mantenimiento},
    )


def mantenimiento_delete(request, pk):
    mantenimiento = get_object_or_404(_mantenimiento_queryset(), pk=pk)
    if request.method == "POST":
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.EN_PROCESO:
            try:
                _sync_equipo_fin_mantenimiento(mantenimiento, request=request)
            except ValidationError:
                pass
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.MANTENIMIENTO,
            titulo=f"Mantenimiento eliminado: {mantenimiento.folio_mantenimiento()}",
            objeto=mantenimiento,
        )
        mantenimiento.delete()
        messages.success(request, "Mantenimiento eliminado correctamente.")
        return redirect("mantenimiento_list")
    return render(request, "mantenimiento/confirm_delete.html", {"object": mantenimiento})


def mantenimiento_iniciar(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method != "POST":
        return redirect("mantenimiento_detail", pk=pk)
    try:
        mantenimiento.iniciar()
        _sync_equipo_inicio_mantenimiento(mantenimiento, request=request)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("mantenimiento_detail", pk=pk)

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MANTENIMIENTO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Mantenimiento iniciado: {mantenimiento.folio_mantenimiento()}",
        objeto=mantenimiento,
        entidad_relacionada=mantenimiento.equipo,
        enlace_nombre="mantenimiento_detail",
        metadata={"estado": mantenimiento.estado_mantenimiento},
    )
    messages.success(request, f"{mantenimiento.folio_mantenimiento()} en proceso.")
    return redirect("mantenimiento_detail", pk=pk)


def mantenimiento_cancelar(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method != "POST":
        return redirect("mantenimiento_detail", pk=pk)
    try:
        estaba_en_proceso = (
            mantenimiento.estado_mantenimiento == EstadoMantenimiento.EN_PROCESO
        )
        mantenimiento.cancelar()
        if estaba_en_proceso:
            _sync_equipo_fin_mantenimiento(mantenimiento, request=request)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("mantenimiento_detail", pk=pk)

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MANTENIMIENTO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Mantenimiento cancelado: {mantenimiento.folio_mantenimiento()}",
        objeto=mantenimiento,
        entidad_relacionada=mantenimiento.equipo,
        enlace_nombre="mantenimiento_detail",
        metadata={"estado": mantenimiento.estado_mantenimiento},
    )
    messages.success(request, f"{mantenimiento.folio_mantenimiento()} cancelado.")
    return redirect("mantenimiento_detail", pk=pk)


def mantenimiento_reabrir(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method != "POST":
        return redirect("mantenimiento_detail", pk=pk)
    try:
        estado_anterior = mantenimiento.estado_mantenimiento
        mantenimiento.reabrir()
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.EN_PROCESO:
            _sync_equipo_inicio_mantenimiento(mantenimiento, request=request)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
        return redirect("mantenimiento_detail", pk=pk)

    historial.registrar_historial(
        request=request,
        modulo=ModuloHistorial.MANTENIMIENTO,
        accion=AccionHistorial.CAMBIO_ESTADO,
        titulo=f"Mantenimiento reabierto: {mantenimiento.folio_mantenimiento()}",
        objeto=mantenimiento,
        entidad_relacionada=mantenimiento.equipo,
        enlace_nombre="mantenimiento_detail",
        metadata={
            "estado_anterior": estado_anterior,
            "estado": mantenimiento.estado_mantenimiento,
        },
    )
    messages.success(
        request,
        f"{mantenimiento.folio_mantenimiento()} reabierto ({mantenimiento.estado_mantenimiento}).",
    )
    return redirect("mantenimiento_detail", pk=pk)


# ============ AgendaMantenimiento views ==============
class AgendaMantenimientoForm(forms.ModelForm):
    fecha_inicio = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
        label="Fecha inicio",
    )
    fecha_fin = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
        label="Fecha fin",
    )
    crear_proximo_ciclo = forms.BooleanField(
        required=False,
        initial=True,
        label="Crear proximo mantenimiento automaticamente",
        help_text=(
            "Si indicas proxima fecha, programa un mantenimiento Preventivo "
            "en esa fecha (salvo que el equipo ya tenga uno abierto)."
        ),
    )

    class Meta:
        model = AgendaMantenimiento
        fields = [
            "mantenimiento",
            "fecha_inicio",
            "fecha_fin",
            "acciones_realizadas",
            "observaciones",
            "proxima_fecha_mantenimiento",
        ]
        labels = {
            "mantenimiento": "Mantenimiento",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de fin",
            "acciones_realizadas": "Acciones realizadas",
            "observaciones": "Observaciones",
            "proxima_fecha_mantenimiento": "Próxima fecha de mantenimiento",
        }
        help_texts = {
            "mantenimiento": "Seleccione el mantenimiento a cerrar.",
            "acciones_realizadas": "Describa las acciones realizadas durante el mantenimiento.",
            "observaciones": "Opcional. Puede agregar observaciones adicionales.",
            "proxima_fecha_mantenimiento": "Opcional. Genera aviso de proximo ciclo en el panel (sin email).",
        }
        widgets = {
            "fecha_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "fecha_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
            "proxima_fecha_mantenimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        fixed_mantenimiento = kwargs.pop("mantenimiento", None)
        super().__init__(*args, **kwargs)
        self.fields["acciones_realizadas"].required = True
        self.fields["fecha_fin"].required = True
        qs = Mantenimiento.objects.select_related("equipo").filter(
            estado_mantenimiento__in=[
                EstadoMantenimiento.PROGRAMADO,
                EstadoMantenimiento.EN_PROCESO,
            ],
            cierre__isnull=True,
        ).order_by("fecha_programada")
        if self.instance and self.instance.pk:
            qs = Mantenimiento.objects.filter(pk=self.instance.mantenimiento_id) | qs
            self.fields["mantenimiento"].disabled = True
            self.fields["crear_proximo_ciclo"].initial = False
        elif fixed_mantenimiento is not None:
            qs = Mantenimiento.objects.filter(pk=fixed_mantenimiento.pk)
            self.fields["mantenimiento"].initial = fixed_mantenimiento
            self.fields["mantenimiento"].disabled = True
        self.fields["mantenimiento"].queryset = qs.distinct()
        self.fixed_mantenimiento = fixed_mantenimiento

    def clean(self):
        cleaned = super().clean()
        if getattr(self, "fixed_mantenimiento", None) is not None:
            cleaned["mantenimiento"] = self.fixed_mantenimiento
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if getattr(self, "fixed_mantenimiento", None) is not None:
            instance.mantenimiento = self.fixed_mantenimiento
        if commit:
            instance.save()
            self.save_m2m()
            mantenimiento = instance.mantenimiento
            mantenimiento.marcar_completado()
        return instance


def _mensaje_proximo_ciclo(request, resultado, motivo):
    if motivo == "creado" and resultado is not None:
        messages.success(
            request,
            f"Proximo ciclo programado: {resultado.folio_mantenimiento()} "
            f"({resultado.fecha_programada}).",
        )
        historial.registrar_creacion(
            request,
            modulo=ModuloHistorial.MANTENIMIENTO,
            titulo=f"Proximo ciclo programado: {resultado.folio_mantenimiento()}",
            objeto=resultado,
            entidad_relacionada=resultado.equipo,
            enlace_nombre="mantenimiento_detail",
            enlace_pk=resultado.pk,
        )
    elif motivo == "ya_abierto" and resultado is not None:
        messages.info(
            request,
            f"No se creo otro ciclo: el equipo ya tiene "
            f"{resultado.folio_mantenimiento()} abierto.",
        )
    elif motivo == "ya_programado" and resultado is not None:
        messages.info(
            request,
            f"Ya existia el ciclo {resultado.folio_mantenimiento()} "
            f"para esa fecha.",
        )


def agendamantenimiento_list(request):
    items = AgendaMantenimiento.objects.select_related(
        "mantenimiento", "mantenimiento__equipo"
    )
    search_query = (request.GET.get("q") or "").strip()
    if search_query:
        q = (
            Q(mantenimiento__equipo__codigo_inventario__icontains=search_query)
            | Q(mantenimiento__equipo__marca__icontains=search_query)
            | Q(mantenimiento__equipo__modelo__icontains=search_query)
            | Q(acciones_realizadas__icontains=search_query)
            | Q(observaciones__icontains=search_query)
            | Q(mantenimiento__tecnico_responsable__icontains=search_query)
        )
        digits = "".join(ch for ch in search_query if ch.isdigit())
        if digits.isdigit():
            q |= Q(mantenimiento_id=int(digits)) | Q(pk=int(digits))
        items = items.filter(q)

    items = items.order_by("-fecha_fin", "-pk")
    paginator = Paginator(items, MANTENIMIENTO_LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "agendamantenimiento/list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
        },
    )


def agendamantenimiento_create(request):
    mantenimiento_id = request.GET.get("mantenimiento")
    fixed = None
    if mantenimiento_id:
        fixed = get_object_or_404(Mantenimiento, pk=mantenimiento_id)
        if not fixed.puede_completar:
            messages.error(request, "Ese mantenimiento no se puede cerrar en su estado actual.")
            return redirect("mantenimiento_detail", pk=fixed.pk)

    if request.method == "POST":
        form = AgendaMantenimientoForm(request.POST, mantenimiento=fixed)
        if form.is_valid():
            agenda = form.save()
            _sync_equipo_fin_mantenimiento(agenda.mantenimiento, request=request)
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Cierre de {agenda.mantenimiento.folio_mantenimiento()}",
                objeto=agenda,
                entidad_relacionada=agenda.mantenimiento,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=agenda.mantenimiento_id,
            )
            proximo, motivo = _crear_proximo_mantenimiento_desde_cierre(
                agenda,
                crear=form.cleaned_data.get("crear_proximo_ciclo", False),
            )
            messages.success(request, "Mantenimiento cerrado correctamente.")
            _mensaje_proximo_ciclo(request, proximo, motivo)
            if motivo == "creado" and proximo is not None:
                return redirect("mantenimiento_detail", pk=proximo.pk)
            return redirect("mantenimiento_detail", pk=agenda.mantenimiento_id)
    else:
        form = AgendaMantenimientoForm(mantenimiento=fixed)
    return render(
        request,
        "agendamantenimiento/form.html",
        {"form": form, "mantenimiento": fixed},
    )


def agendamantenimiento_update(request, pk):
    agenda = get_object_or_404(
        AgendaMantenimiento.objects.select_related("mantenimiento", "mantenimiento__equipo"),
        pk=pk,
    )
    if request.method == "POST":
        form = AgendaMantenimientoForm(request.POST, instance=agenda)
        if form.is_valid():
            agenda = form.save()
            _sync_equipo_fin_mantenimiento(agenda.mantenimiento, request=request)
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.MANTENIMIENTO,
                titulo=f"Cierre actualizado: {agenda.mantenimiento.folio_mantenimiento()}",
                objeto=agenda,
                form=form,
                entidad_relacionada=agenda.mantenimiento,
                enlace_nombre="mantenimiento_detail",
                enlace_pk=agenda.mantenimiento_id,
            )
            proximo, motivo = _crear_proximo_mantenimiento_desde_cierre(
                agenda,
                crear=form.cleaned_data.get("crear_proximo_ciclo", False),
            )
            messages.success(request, "Cierre actualizado correctamente.")
            _mensaje_proximo_ciclo(request, proximo, motivo)
            if motivo == "creado" and proximo is not None:
                return redirect("mantenimiento_detail", pk=proximo.pk)
            return redirect("mantenimiento_detail", pk=agenda.mantenimiento_id)
    else:
        form = AgendaMantenimientoForm(instance=agenda)
    return render(
        request,
        "agendamantenimiento/form.html",
        {"form": form, "object": agenda, "mantenimiento": agenda.mantenimiento},
    )


def agendamantenimiento_delete(request, pk):
    agenda = get_object_or_404(AgendaMantenimiento, pk=pk)
    mantenimiento = agenda.mantenimiento
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.MANTENIMIENTO,
            titulo=f"Cierre eliminado: {mantenimiento.folio_mantenimiento()}",
            objeto=agenda,
            entidad_relacionada=mantenimiento,
        )
        agenda.delete()
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.COMPLETADO:
            mantenimiento.estado_mantenimiento = EstadoMantenimiento.EN_PROCESO
            mantenimiento.save(update_fields=["estado_mantenimiento"])
            try:
                _sync_equipo_inicio_mantenimiento(mantenimiento, request=request)
            except ValidationError:
                pass
        messages.success(request, "Cierre eliminado correctamente.")
        return redirect("mantenimiento_detail", pk=mantenimiento.pk)
    return render(request, "agendamantenimiento/confirm_delete.html", {"object": agenda})


# ============ TicketIT views ==============
# Formulario de ticket

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
            items = items.filter(asignado_a=request.user)

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



# =========== Bitacora views =============
class BitacoraForm(forms.ModelForm):
    class Meta:
        model = Bitacora
        fields = "__all__"
        labels = {
            "folio_bitacora": "Folio de bitacora",
            "fecha_bitacora": "Fecha de bitacora",
            "Situacion": "Situacion",
            "descripcion_situacion": "Descripcion de la situacion",
        }
        help_texts = {
            "descripcion_bitacora": "Descripcion",
            "Situacion": "Problema o situacion que se presenta.",
        }
        widgets = {
            "fecha_bitacora": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "descripcion_situacion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fecha_bitacora = self.fields.get("fecha_bitacora")
        if fecha_bitacora:
            fecha_bitacora.widget = forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            )
            fecha_bitacora.input_formats = ["%Y-%m-%dT%H:%M"]

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


# =========== Answer views =============
class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = "__all__"
        labels = {
            "folio_answer": "Folio",
            "fecha_answer": "Fecha",
            "solucion": "Solucion",
            "descripcion_solucion": "Descripcion de la solucion",
        }
        help_texts = {
            "descripcion_answer": "Descripcion",
            "descripcion_solucion": "Descripcion de la solucion",
        }
        widgets = {
            "fecha_answer": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "descripcion_solucion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fecha_answer = self.fields.get("fecha_answer")
        if fecha_answer:
            fecha_answer.widget = forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            )
            fecha_answer.input_formats = ["%Y-%m-%dT%H:%M"]

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
class PlantillaDocumentoForm(forms.ModelForm):
    class Meta:
        model = PlantillaDocumento
        fields = ["nombre", "descripcion", "archivo", "activo"]
        labels = {
            "nombre": "Nombre",
            "descripcion": "Descripcion",
            "archivo": "Archivo de la plantilla",
            "activo": "Activa",
        }
        help_texts = {
            "archivo": (
                "Sube un archivo .docx, .xlsx o .pdf (maximo 50 MB). En Word/Excel "
                "escribe los campos como {{nombre_campo}}; en PDF usa un archivo "
                "con campos de formulario."
            ),
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo

        max_size = 50 * 1024 * 1024
        if archivo.size > max_size:
            raise forms.ValidationError("El archivo debe pesar menos de 50 MB.")

        nombre_archivo = archivo.name.lower()
        if nombre_archivo.endswith(".docx"):
            tipo_archivo = TipoPlantillaDocumento.DOCX
        elif nombre_archivo.endswith(".xlsx"):
            tipo_archivo = TipoPlantillaDocumento.XLSX
        elif nombre_archivo.endswith(".pdf"):
            tipo_archivo = TipoPlantillaDocumento.PDF
        else:
            raise forms.ValidationError("Formato no permitido. Usa .docx, .xlsx o .pdf.")

        try:
            campos = document_engine.detectar_campos(archivo, tipo_archivo)
        except document_engine.DocumentEngineError as exc:
            raise forms.ValidationError(str(exc))

        self.instance.tipo_archivo = tipo_archivo
        self.instance.campos = campos
        return archivo


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


# =========== OrdenCompra views =============
def _validar_pdf_upload(archivo):
    if not archivo:
        return archivo

    max_size = 50 * 1024 * 1024
    if archivo.size > max_size:
        raise forms.ValidationError("El archivo debe pesar menos de 50 MB.")

    content_type = getattr(archivo, "content_type", None)
    if content_type and content_type not in {"application/pdf"}:
        raise forms.ValidationError("Formato no permitido. Solo PDF.")

    if not archivo.name.lower().endswith(".pdf"):
        raise forms.ValidationError("El archivo debe tener extension .pdf.")

    return archivo


def _sync_iva_porcentaje(form, cleaned_data):
    from decimal import Decimal

    opcion = cleaned_data.get("iva_opcion")
    if opcion == IvaOpcion.OCHO:
        cleaned_data["iva_porcentaje"] = Decimal("8")
    elif opcion == IvaOpcion.DIECISEIS:
        cleaned_data["iva_porcentaje"] = Decimal("16")
    elif opcion == IvaOpcion.OTRO and cleaned_data.get("iva_porcentaje") is None:
        form.add_error("iva_porcentaje", "Indica el porcentaje de IVA.")
    return cleaned_data


class OrdenCompraCrearForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = [
            "folio_orden",
            "fecha",
            "proveedor",
            "tipo_moneda",
            "iva_opcion",
            "iva_porcentaje",
            "comentarios",
            "estado",
            "notas",
            "plantilla",
        ]
        labels = {
            "folio_orden": "Folio / orden",
            "fecha": "Fecha",
            "proveedor": "Proveedor",
            "tipo_moneda": "Tipo de moneda",
            "iva_opcion": "IVA",
            "iva_porcentaje": "Porcentaje IVA",
            "comentarios": "Comentarios",
            "estado": "Estado",
            "notas": "Notas",
            "plantilla": "Plantilla PDF",
        }
        widgets = {
            "folio_orden": forms.TextInput(attrs={"class": "form-control"}),
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "proveedor": forms.Select(attrs={"class": "form-select"}),
            "comentarios": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "notas": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "plantilla": forms.Select(attrs={"class": "form-select"}),
            "iva_porcentaje": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "iva_opcion": forms.RadioSelect,
            "tipo_moneda": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folio_orden"].required = False
        self.fields["folio_orden"].help_text = "Dejalo vacio para generar uno automatico (OC-000001)."
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True).order_by("nombre_proveedor")
        self.fields["proveedor"].required = True
        self.fields["plantilla"].queryset = PlantillaDocumento.objects.filter(activo=True).order_by("nombre")
        self.fields["plantilla"].required = False
        self.fields["plantilla"].empty_label = "Plantilla por defecto"
        self.fields["iva_porcentaje"].required = False

    def clean(self):
        cleaned = super().clean()
        return _sync_iva_porcentaje(self, cleaned)


class OrdenCompraSubirForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = ["folio_orden", "archivo_pdf", "estado", "notas"]
        labels = {
            "folio_orden": "Folio / orden",
            "archivo_pdf": "Archivo PDF",
            "estado": "Estado",
            "notas": "Notas",
        }
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folio_orden"].required = False
        self.fields["folio_orden"].help_text = "Dejalo vacio para generar uno automatico (OC-000001)."
        self.fields["archivo_pdf"].required = True

    def clean_archivo_pdf(self):
        return _validar_pdf_upload(self.cleaned_data.get("archivo_pdf"))


class DetalleOrdenCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleOrdenCompra
        fields = ["id_producto", "descripcion", "cantidad", "precio_unitario"]
        labels = {
            "id_producto": "ID producto",
            "descripcion": "Descripcion",
            "cantidad": "Cantidad",
            "precio_unitario": "P.U. / unit price",
        }
        widgets = {
            "id_producto": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "descripcion": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "min": "0"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "min": "0"}),
        }


DetalleOrdenCompraFormSet = forms.inlineformset_factory(
    OrdenCompra,
    DetalleOrdenCompra,
    form=DetalleOrdenCompraForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


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

    nombre_pdf = f"orden_compra_{orden.folio_orden}.pdf"
    orden.archivo_pdf.save(nombre_pdf, ContentFile(pdf_bytes), save=True)
    return True


def ordencompra_list(request):
    items = _ordenes_for_user(
        request.user,
        OrdenCompra.objects.select_related("proveedor", "elaborado_por").all(),
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
    orden = get_object_or_404(OrdenCompra.objects.prefetch_related("detalles"), pk=pk)
    if not user_can_manage_orden(request.user, orden):
        messages.error(request, "No tienes permisos para esta orden de compra.")
        return redirect("ordencompra_list")

    if orden.origen == OrigenOrdenCompra.SUBIDO:
        if request.method == "POST":
            form = OrdenCompraSubirForm(request.POST, request.FILES, instance=orden)
            if form.is_valid():
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
                return redirect("ordencompra_list")
        else:
            form = OrdenCompraSubirForm(instance=orden)
        return render(
            request,
            "ordencompra/form_subir.html",
            {
                "form": form,
                "object": orden,
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
            with transaction.atomic():
                orden = form.save()
                formset.save()
                orden.recalcular_totales(save=True)
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.ORDEN_COMPRA,
                titulo=f"Orden de compra actualizada: {orden.folio_orden}",
                objeto=orden,
                form=form,
                enlace_nombre="ordencompra_update",
            )
            _intentar_generar_pdf(orden, request)
            messages.success(request, "Orden de compra actualizada correctamente.")
            return redirect("ordencompra_list")
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
            "proveedores_json": _proveedores_payload(),
            "elaborado_por_nombre": (
                (orden.elaborado_por.get_full_name() or orden.elaborado_por.get_username())
                if orden.elaborado_por
                else (request.user.get_full_name() or request.user.get_username())
            ),
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


def _calendar_event(
    title,
    start,
    *,
    color,
    details,
    case_type,
    case_type_label,
    case_label,
    action_url,
    action_text,
    end=None,
    all_day=True,
    urgency="ok",
    urgency_label=None,
):
    class_names = [f"cal-type-{case_type}"]
    if urgency and urgency != "ok":
        class_names.append(f"cal-urgency-{urgency}")

    event = {
        "title": title,
        "start": start.isoformat(),
        "allDay": all_day,
        "backgroundColor": color,
        "borderColor": color,
        "textColor": "#ffffff",
        "classNames": class_names,
        "extendedProps": {
            "details": details,
            "caseType": case_type,
            "caseTypeLabel": case_type_label,
            "caseLabel": case_label,
            "actionUrl": action_url,
            "actionText": action_text,
            "urgency": urgency or "ok",
            "urgencyLabel": urgency_label,
        },
    }
    if end is not None:
        event["end"] = end.isoformat()
    return event


def _calendar_label(value):
    return value if value else "Sin dato"


def _calendar_day(value):
    if not value:
        return timezone.localdate()
    if timezone.is_aware(value):
        return timezone.localtime(value).date()
    if hasattr(value, "date") and not isinstance(value, date):
        return value.date()
    return value


CALENDAR_PAST_DAYS = 30
CALENDAR_FUTURE_DAYS = 90
CALENDAR_COLOR_VENCIDO = "#dc2626"
CALENDAR_COLOR_POR_VENCER = "#f59e0b"


def _calendar_window(today=None):
    today = today or timezone.localdate()
    return (
        today - timedelta(days=CALENDAR_PAST_DAYS),
        today + timedelta(days=CALENDAR_FUTURE_DAYS),
        today,
    )


def _calendar_urgency_from_date(event_date, today=None, alerta_dias=7, active=True):
    if not active or not event_date:
        return "ok", None
    today = today or timezone.localdate()
    if isinstance(event_date, datetime):
        event_date = _calendar_day(event_date)
    if event_date < today:
        return "vencido", "Vencido"
    if event_date <= today + timedelta(days=alerta_dias):
        return "por_vencer", "Por vencer"
    return "ok", None


def _ticket_calendar_urgency(ticket, now=None):
    if ticket.status == EstadoSupport.CERRADO:
        return "ok", None
    now = now or timezone.now()
    horas = SLA_HORAS_POR_PRIORIDAD.get(ticket.prioridad)
    if not horas or not ticket.fecha_support:
        return "ok", None
    deadline = ticket.fecha_support + timedelta(hours=horas)
    if timezone.is_naive(deadline) and timezone.is_aware(now):
        deadline = timezone.make_aware(deadline, timezone.get_current_timezone())
    elif timezone.is_aware(deadline) and timezone.is_naive(now):
        now = timezone.make_aware(now, timezone.get_current_timezone())
    if now >= deadline:
        return "vencido", "SLA vencido"
    umbral = min(timedelta(hours=4), timedelta(hours=horas) * 0.25)
    if now >= deadline - umbral:
        return "por_vencer", "SLA por vencer"
    return "ok", None


def _calendar_apply_urgency_color(base_color, urgency):
    if urgency == "vencido":
        return CALENDAR_COLOR_VENCIDO
    if urgency == "por_vencer":
        return CALENDAR_COLOR_POR_VENCER
    return base_color


def _build_home_calendar_events(user=None):
    window_start, window_end, today = _calendar_window()
    now = timezone.now()
    events = []
    staff_user = is_operativo(user)

    tickets_qs = (
        TicketIT.objects.select_related("area", "puesto", "solicitado_por")
        .filter(
            fecha_support__date__gte=window_start,
            fecha_support__date__lte=window_end,
        )
        .order_by("-fecha_support")
    )
    if user is not None and not staff_user:
        tickets_qs = tickets_qs.filter(solicitado_por=user)

    for ticket in tickets_qs:
        ticket_date = _calendar_day(ticket.fecha_support)
        urgency, urgency_label = _ticket_calendar_urgency(ticket, now=now)
        base_color = {
            EstadoSupport.CERRADO: "#0f766e",
            EstadoSupport.EN_PROCESO: "#1d4ed8",
            EstadoSupport.EN_REVISION: "#7c3aed",
            EstadoSupport.ABIERTO: "#f59e0b",
        }.get(ticket.status, "#475569")
        color = _calendar_apply_urgency_color(base_color, urgency)
        details = [
            {"label": "Estado", "value": _calendar_label(ticket.status)},
            {"label": "Prioridad", "value": _calendar_label(ticket.prioridad)},
            {"label": "Area", "value": _calendar_label(getattr(ticket.area, "nombre_area", None))},
            {"label": "Puesto", "value": _calendar_label(getattr(ticket.puesto, "nombre_puesto", None))},
            {
                "label": "Solicitado por",
                "value": _calendar_label(getattr(ticket.solicitado_por, "username", None)),
            },
            {"label": "Requerimiento", "value": _calendar_label(ticket.requerimiento)},
        ]
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        events.append(
            _calendar_event(
                f"Ticket {ticket.folio_ticket}",
                ticket_date,
                color=color,
                details=details,
                case_type="ticket",
                case_type_label="Ticket de soporte",
                case_label=ticket.folio_ticket,
                action_url=reverse("ticketit_detail", args=[ticket.pk]),
                action_text="Abrir ticket",
                urgency=urgency,
                urgency_label=urgency_label,
            )
        )

    if not staff_user:
        events.sort(key=lambda event: event["start"])
        return events

    movimientos_qs = (
        MovimientoEquipo.objects.select_related("equipo", "responsable")
        .filter(
            fecha_movimiento__date__gte=window_start,
            fecha_movimiento__date__lte=window_end,
        )
        .order_by("-fecha_movimiento")
    )
    for movimiento in movimientos_qs:
        color = {
            TipoMovimiento.DADA_DE_ALTA: "#16a34a",
            TipoMovimiento.DADA_DE_BAJA: "#b42318",
            TipoMovimiento.ASIGNACION: "#1d4ed8",
            TipoMovimiento.CAMBIO_ASIGNACION: "#7c3aed",
            TipoMovimiento.MANTENIMIENTO: "#f59e0b",
            TipoMovimiento.CAMBIO_UBICACION: "#0f766e",
        }.get(movimiento.tipo_movimiento, "#475569")
        events.append(
            _calendar_event(
                f"Movimiento {movimiento.equipo.codigo_inventario if getattr(movimiento, 'equipo', None) else 'de equipo'}",
                _calendar_day(movimiento.fecha_movimiento),
                color=color,
                details=[
                    {"label": "Tipo", "value": _calendar_label(movimiento.tipo_movimiento)},
                    {
                        "label": "Equipo",
                        "value": _calendar_label(
                            getattr(movimiento.equipo, "codigo_inventario", None)
                        ),
                    },
                    {"label": "Origen", "value": _calendar_label(movimiento.origen)},
                    {"label": "Destino", "value": _calendar_label(movimiento.destino)},
                    {
                        "label": "Responsable",
                        "value": _calendar_label(
                            str(movimiento.responsable) if movimiento.responsable else None
                        ),
                    },
                    {
                        "label": "Observaciones",
                        "value": _calendar_label(movimiento.observaciones),
                    },
                ],
                case_type="movimiento",
                case_type_label="Movimiento de equipo",
                case_label=_calendar_label(movimiento.tipo_movimiento),
                action_url=reverse("movimientoequipo_detail", args=[movimiento.pk]),
                action_text="Ver movimiento",
                urgency="ok",
            )
        )

    mantenimientos_qs = (
        Mantenimiento.objects.select_related("equipo", "cierre")
        .filter(
            fecha_programada__gte=window_start,
            fecha_programada__lte=window_end,
        )
        .order_by("-fecha_programada")
    )
    for mantenimiento in mantenimientos_qs:
        base_color = "#1d4ed8"
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.COMPLETADO:
            base_color = "#0f766e"
        elif mantenimiento.estado_mantenimiento == EstadoMantenimiento.CANCELADO:
            base_color = "#b42318"

        activo = mantenimiento.estado_mantenimiento in {
            EstadoMantenimiento.PROGRAMADO,
            EstadoMantenimiento.EN_PROCESO,
        }
        urgency, urgency_label = _calendar_urgency_from_date(
            mantenimiento.fecha_programada,
            today=today,
            alerta_dias=MANTENIMIENTO_ALERTA_DIAS,
            active=activo,
        )
        color = _calendar_apply_urgency_color(base_color, urgency)
        details = [
            {"label": "Estado", "value": _calendar_label(mantenimiento.estado_mantenimiento)},
            {"label": "Tipo", "value": _calendar_label(mantenimiento.tipo_mantenimiento)},
            {
                "label": "Equipo",
                "value": _calendar_label(
                    getattr(mantenimiento.equipo, "codigo_inventario", None)
                ),
            },
            {"label": "Responsable", "value": _calendar_label(mantenimiento.tecnico_responsable)},
            {"label": "Costo", "value": _calendar_label(mantenimiento.costo_mantenimiento)},
        ]
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        events.append(
            _calendar_event(
                f"Mantenimiento {mantenimiento.folio_mantenimiento()}",
                mantenimiento.fecha_programada,
                color=color,
                details=details,
                case_type="mantenimiento",
                case_type_label="Mantenimiento",
                case_label=mantenimiento.folio_mantenimiento(),
                action_url=reverse("mantenimiento_detail", args=[mantenimiento.pk]),
                action_text="Abrir mantenimiento",
                urgency=urgency,
                urgency_label=urgency_label,
            )
        )

    ciclos_qs = (
        AgendaMantenimiento.objects.select_related("mantenimiento", "mantenimiento__equipo")
        .filter(
            proxima_fecha_mantenimiento__isnull=False,
            proxima_fecha_mantenimiento__gte=window_start,
            proxima_fecha_mantenimiento__lte=window_end,
        )
        .order_by("-proxima_fecha_mantenimiento")
    )
    for agenda in ciclos_qs:
        urgency, urgency_label = _calendar_urgency_from_date(
            agenda.proxima_fecha_mantenimiento,
            today=today,
            alerta_dias=MANTENIMIENTO_ALERTA_DIAS,
            active=True,
        )
        color = _calendar_apply_urgency_color("#7c3aed", urgency)
        details = [
            {"label": "Mantenimiento", "value": agenda.mantenimiento.folio_mantenimiento()},
            {
                "label": "Equipo",
                "value": _calendar_label(
                    getattr(agenda.mantenimiento.equipo, "codigo_inventario", None)
                ),
            },
            {
                "label": "Inicio",
                "value": agenda.fecha_inicio.strftime("%Y-%m-%d %H:%M")
                if agenda.fecha_inicio
                else "Sin inicio",
            },
            {
                "label": "Fin",
                "value": agenda.fecha_fin.strftime("%Y-%m-%d %H:%M")
                if agenda.fecha_fin
                else "Sin fin",
            },
            {"label": "Acciones", "value": _calendar_label(agenda.acciones_realizadas)},
            {"label": "Observaciones", "value": _calendar_label(agenda.observaciones)},
            {
                "label": "Proximo mantenimiento",
                "value": agenda.proxima_fecha_mantenimiento.strftime("%Y-%m-%d"),
            },
        ]
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        events.append(
            _calendar_event(
                f"Ciclo {agenda.mantenimiento.folio_mantenimiento()}",
                agenda.proxima_fecha_mantenimiento,
                color=color,
                details=details,
                case_type="ciclo",
                case_type_label="Proximo ciclo",
                case_label=agenda.mantenimiento.folio_mantenimiento(),
                action_url=reverse("mantenimiento_detail", args=[agenda.mantenimiento_id]),
                action_text="Abrir mantenimiento",
                urgency=urgency,
                urgency_label=urgency_label,
            )
        )

    checks_qs = (
        SeguimientoTicket.objects.select_related("ticket", "usuario")
        .filter(
            Q(
                fecha_proximo_seguimiento__gte=window_start,
                fecha_proximo_seguimiento__lte=window_end,
            )
            | Q(
                fecha_proximo_seguimiento__isnull=True,
                fecha_check__date__gte=window_start,
                fecha_check__date__lte=window_end,
            )
        )
        .order_by("-fecha_check")
    )
    for seguimiento in checks_qs:
        event_date = seguimiento.fecha_proximo_seguimiento or _calendar_day(
            seguimiento.fecha_check
        )
        activo = (
            not seguimiento.ya_terminado
            and seguimiento.fecha_proximo_seguimiento is not None
            and getattr(seguimiento.ticket, "status", None) != EstadoSupport.CERRADO
        )
        urgency, urgency_label = _calendar_urgency_from_date(
            seguimiento.fecha_proximo_seguimiento,
            today=today,
            alerta_dias=SEGUIMIENTO_ALERTA_DIAS,
            active=activo,
        )
        base_color = "#0f766e" if seguimiento.ya_terminado else "#7c3aed"
        color = _calendar_apply_urgency_color(base_color, urgency)
        details = [
            {
                "label": "Ticket",
                "value": _calendar_label(getattr(seguimiento.ticket, "folio_ticket", None)),
            },
            {
                "label": "Estado",
                "value": "Terminado" if seguimiento.ya_terminado else "Pendiente",
            },
            {"label": "Avance", "value": _calendar_label(seguimiento.avance_realizado)},
            {"label": "Pendiente", "value": _calendar_label(seguimiento.pendiente)},
            {"label": "Proximo paso", "value": _calendar_label(seguimiento.proximo_paso)},
            {
                "label": "Usuario",
                "value": _calendar_label(
                    str(seguimiento.usuario) if seguimiento.usuario else None
                ),
            },
            {"label": "Observacion", "value": _calendar_label(seguimiento.observacion)},
        ]
        if urgency_label:
            details.insert(0, {"label": "Aviso", "value": urgency_label})
        events.append(
            _calendar_event(
                f"Check {seguimiento.folio_check or seguimiento.ticket.folio_ticket}",
                event_date,
                color=color,
                details=details,
                case_type="seguimiento_ticket",
                case_type_label="Check",
                case_label=seguimiento.folio_check or seguimiento.ticket.folio_ticket,
                action_url=reverse("ticketit_detail", args=[seguimiento.ticket_id]),
                action_text="Abrir ticket",
                urgency=urgency,
                urgency_label=urgency_label,
            )
        )

    events.sort(key=lambda event: event["start"])
    return events


def home(request):
    today = timezone.localdate()
    is_staff_user = is_operativo(request.user)
    tickets_abiertos_qs = _tickets_abiertos_qs(request.user)

    alerta_seguimientos = {}
    alerta_mantenimientos = {}
    alerta_equipos = {}
    if is_staff_user:
        alerta_seguimientos = _seguimientos_alerta_context(today=today)
        alerta_mantenimientos = _mantenimientos_alerta_context(today=today)
        alerta_equipos = _equipos_alerta_context(today=today)

    ticket_ops = _ticket_dashboard_context(request.user)["ticket_dashboard"]

    quick_links = [
        {"label": "Tickets", "url_name": "ticketit_list", "hint": "Soporte activo"},
        {"label": "Mis equipos", "url_name": "mis_equipos", "hint": "Asignados a ti"},
        {"label": "Ordenes", "url_name": "ordencompra_list", "hint": "Compras"},
        {"label": "Calendario", "url_name": "home", "hint": "Agenda", "anchor": "#calendario"},
    ]
    if is_staff_user:
        quick_links = [
            {"label": "Tickets", "url_name": "ticketit_list", "hint": "Soporte activo"},
            {"label": "Inventario", "url_name": "equipo_dashboard", "hint": "Equipos y avisos"},
            {"label": "Seguimientos", "url_name": "seguimientoticket_list", "hint": "Checks y avisos"},
            {"label": "Mantenimientos", "url_name": "mantenimiento_dashboard", "hint": "Dashboard y avisos"},
        ]

    seguimientos_atencion = (
        alerta_seguimientos.get("seguimientos_vencidos_count", 0)
        + alerta_seguimientos.get("seguimientos_por_vencer_count", 0)
    )
    mantenimientos_atencion = (
        alerta_mantenimientos.get("mantenimientos_vencidos_count", 0)
        + alerta_mantenimientos.get("mantenimientos_por_vencer_count", 0)
    )
    equipos_atencion = (
        alerta_equipos.get("equipos_sin_ubicacion_count", 0)
        + alerta_equipos.get("equipos_mant_largo_count", 0)
        + alerta_equipos.get("asignaciones_antiguas_count", 0)
    )

    calendar_events = _build_home_calendar_events(user=request.user)
    calendar_counts = {
        "ticket": 0,
        "mantenimiento": 0,
        "seguimiento_ticket": 0,
        "ciclo": 0,
        "movimiento": 0,
        "vencido": 0,
        "por_vencer": 0,
    }
    for event in calendar_events:
        props = event.get("extendedProps") or {}
        case_type = props.get("caseType")
        if case_type in calendar_counts:
            calendar_counts[case_type] += 1
        urgency = props.get("urgency")
        if urgency in {"vencido", "por_vencer"}:
            calendar_counts[urgency] += 1

    context = {
        "calendar_events": calendar_events,
        "calendar_counts": calendar_counts,
        "calendar_past_days": CALENDAR_PAST_DAYS,
        "calendar_future_days": CALENDAR_FUTURE_DAYS,
        "dashboard_counts": {
            "tickets": _tickets_for_user(request.user).count(),
            "tickets_abiertos": tickets_abiertos_qs.count(),
            "tickets_sla_vencidos": ticket_ops["sla_vencidos"],
            "tickets_sin_seguimiento": ticket_ops["sin_seguimiento"],
            "equipos_activos": Equipo.objects.filter(activo=True).exclude(
                estado_equipo=EstadoEquipo.BAJA
            ).count() if is_staff_user else None,
            "equipos_atencion": equipos_atencion,
            "equipos_sin_ubicacion": alerta_equipos.get("equipos_sin_ubicacion_count", 0),
            "equipos_mant_largo": alerta_equipos.get("equipos_mant_largo_count", 0),
            "asignaciones_antiguas": alerta_equipos.get("asignaciones_antiguas_count", 0),
            "mantenimientos_proximos": alerta_mantenimientos.get("mantenimientos_proximos_count", 0),
            "mantenimientos_atencion": mantenimientos_atencion,
            "mantenimientos_vencidos": alerta_mantenimientos.get("mantenimientos_vencidos_count", 0),
            "mantenimientos_por_vencer": alerta_mantenimientos.get("mantenimientos_por_vencer_count", 0),
            "mantenimientos_ciclos": alerta_mantenimientos.get("mantenimientos_ciclos_count", 0),
            "seguimientos_atencion": seguimientos_atencion,
            "seguimientos_vencidos": alerta_seguimientos.get("seguimientos_vencidos_count", 0),
            "seguimientos_por_vencer": alerta_seguimientos.get("seguimientos_por_vencer_count", 0),
            "historial_hoy": HistorialActividad.objects.filter(
                fecha__date=today,
                archivado=False,
            ).count() if is_staff_user else None,
        },
        "quick_links": quick_links,
        "recent_tickets": tickets_abiertos_qs.select_related(
            "area", "solicitado_por", "tipo_equipo"
        ).order_by("-fecha_support")[:6],
        "upcoming_mantenimientos": alerta_mantenimientos.get("mantenimientos_proximos_lista", []),
        "recent_historial": list(
            HistorialActividad.objects.select_related("usuario")
            .filter(archivado=False)
            .order_by("-fecha")[:8]
        ) if is_staff_user else [],
        "is_admin_dashboard": is_staff_user,
        "ticket_dashboard": ticket_ops,
        "today": today,
        **alerta_seguimientos,
        **alerta_mantenimientos,
        **alerta_equipos,
    }
    return render(request, "home.html", context)


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Usuario creado correctamente.")
            return redirect("home")
    else:
        form = UserRegisterForm()

    return render(request, "signup.html", {"form": form})





















































