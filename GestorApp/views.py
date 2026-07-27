from datetime import date, datetime, timedelta
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
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

from .models import (
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
    SeguimientoTicket,
    TicketIT,
    TipoMoneda,
    TipoMovimiento,
    TipoTicketSupport,
    TipoPlantillaDocumento,
    Ubicacion,
    ZonaEdificio,
)


def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.is_staff


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not is_admin_user(request.user):
            messages.error(request, "No tienes permisos para acceder a esta seccion.")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped


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
        enlace_nombre="movimientoequipo_update",
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
    es_admin = forms.BooleanField(
        required=False,
        label="Admin",
        help_text="Solo admins pueden asignar este permiso.",
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
        label="Contrasena",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Confirmar contrasena",
    )

    class Meta:
        model = Personal
        exclude = ["user"]
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
            self.fields.pop("es_admin", None)
            self.fields.pop("admin_requested", None)
        elif "es_admin" in self.fields:
            current_user = self.instance.user if self.instance and self.instance.pk else None
            self.fields["es_admin"].initial = bool(current_user and current_user.is_staff)

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

        if "es_admin" in self.cleaned_data and self.cleaned_data.get("es_admin"):
            if action == "none":
                self.add_error(
                    "es_admin",
                    "No puedes asignar admin si no hay usuario.",
                )

        return cleaned

    def save(self, commit=True):
        action = self.cleaned_data.get("account_action") or "none"
        make_admin = None
        if "es_admin" in self.cleaned_data:
            make_admin = bool(self.cleaned_data.get("es_admin"))
        if action == "create":
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    username=self.cleaned_data["username"].strip(),
                    email=self.cleaned_data["email"].strip(),
                    password=self.cleaned_data["password1"],
                )
                if make_admin is not None:
                    user.is_staff = make_admin
                    user.save(update_fields=["is_staff"])
                personal = super().save(commit=False)
                personal.user = user
                if make_admin:
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
            if make_admin is not None and personal.user:
                if personal.user.is_staff != make_admin:
                    personal.user.is_staff = make_admin
                    personal.user.save(update_fields=["is_staff"])
                if make_admin and personal.admin_requested:
                    personal.admin_requested = False
                    personal.save(update_fields=["admin_requested"])
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
    }
    return render(request, "personal/list.html", context)


def personal_admin_requests(request):
    if request.method == "POST":
        personal_id = request.POST.get("personal_id")
        action = (request.POST.get("action") or "approve").strip().lower()
        personal = get_object_or_404(Personal, pk=personal_id, admin_requested=True)
        if action not in {"approve", "reject"}:
            messages.error(request, "Accion no valida.")
            return redirect("personal_admin_requests")
        if action == "approve":
            if not personal.user_id:
                messages.error(request, "El personal no tiene usuario asignado.")
                return redirect("personal_admin_requests")
            if not personal.user.is_staff:
                personal.user.is_staff = True
                personal.user.save(update_fields=["is_staff"])
            if personal.admin_requested:
                personal.admin_requested = False
                personal.save(update_fields=["admin_requested"])
            messages.success(request, "Solicitud aprobada.")
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.PERSONAL,
                accion=historial.AccionHistorial.CAMBIO_ESTADO,
                titulo=f"Admin aprobado para {personal}",
                objeto=personal,
                enlace_nombre="personal_update",
            )
        else:
            if personal.admin_requested:
                personal.admin_requested = False
                personal.save(update_fields=["admin_requested"])
            messages.success(request, "Solicitud rechazada.")
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.PERSONAL,
                accion=historial.AccionHistorial.CAMBIO_ESTADO,
                titulo=f"Solicitud de admin rechazada: {personal}",
                objeto=personal,
            )
        return redirect("personal_admin_requests")
    items = Personal.objects.select_related("user").filter(admin_requested=True)
    return render(request, "personal/admin_requests.html", {"items": items})


def personal_admin_remove(request):
    if request.method == "POST":
        personal_id = request.POST.get("personal_id")
        personal = get_object_or_404(Personal, pk=personal_id)
        if not personal.user_id:
            messages.error(request, "El personal no tiene usuario asignado.")
            return redirect("personal_admin_remove")
        if personal.user.is_superuser:
            messages.error(request, "No se puede quitar admin a un superusuario.")
            return redirect("personal_admin_remove")
        if request.user.pk == personal.user_id:
            messages.error(request, "No puedes quitarte admin a ti mismo.")
            return redirect("personal_admin_remove")
        if personal.user.is_staff:
            personal.user.is_staff = False
            personal.user.save(update_fields=["is_staff"])
        if personal.admin_requested:
            personal.admin_requested = False
            personal.save(update_fields=["admin_requested"])
        messages.success(request, "Admin retirado correctamente.")
        historial.registrar_historial(
            request=request,
            modulo=ModuloHistorial.PERSONAL,
            accion=historial.AccionHistorial.CAMBIO_ESTADO,
            titulo=f"Permisos de admin retirados: {personal}",
            objeto=personal,
            enlace_nombre="personal_update",
        )
        return redirect("personal_admin_remove")
    items = (
        Personal.objects.select_related("user")
        .filter(user__is_staff=True)
        .exclude(user__is_superuser=True)
    )
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
        fields = "__all__"
        labels = {
            "nombre_proveedor": "Nombre del proveedor",
            "contacto": "Contacto",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
            "direccion": "Dirección",
        }
        help_texts = {
            "contacto": "Nombre de la persona de contacto.",
        }
        widgets = {
            "direccion": forms.Textarea(attrs={"rows": 2}),
        }

def proveedor_list(request):
    items = Proveedor.objects.all()
    return render(request, "proveedor/list.html", {"items": items})


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
            "proveedor": "Proveedor",
            "estado_equipo": "Estado del equipo",
            "ubicacion": "Ubicación",
            "fecha_alta": "Fecha de alta",
            "fecha_baja": "Fecha de baja",
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
            "estado_equipo": "Estado actual del equipo.",
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

def equipo_list(request):
    items = Equipo.objects.select_related("categoria", "proveedor", "ubicacion").all()
    search_query = (request.GET.get("q") or "").strip()
    selected_categoria = request.GET.get("categoria", "")
    selected_estado = request.GET.get("estado_equipo", "")
    selected_activo = request.GET.get("activo", "")
    selected_ubicacion = request.GET.get("ubicacion", "")
    fecha_desde_raw = request.GET.get("fecha_alta_desde", "")
    fecha_hasta_raw = request.GET.get("fecha_alta_hasta", "")
    fecha_mes = request.GET.get("fecha_alta_mes", "")
    fecha_rango = request.GET.get("fecha_alta_rango", "")

    if search_query:
        items = items.filter(
            Q(codigo_inventario__icontains=search_query)
            | Q(numero_serie__icontains=search_query)
            | Q(marca__icontains=search_query)
            | Q(modelo__icontains=search_query)
        )
    if selected_categoria:
        items = items.filter(categoria_id=selected_categoria)
    if selected_estado:
        items = items.filter(estado_equipo=selected_estado)
    if selected_activo == "true":
        items = items.filter(activo=True)
    elif selected_activo == "false":
        items = items.filter(activo=False)
    if selected_ubicacion:
        items = items.filter(ubicacion_id=selected_ubicacion)

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
    items = _apply_date_filters(items, "fecha_alta", fecha_desde, fecha_hasta)

    ubicaciones = Ubicacion.objects.select_related("edificio", "zona").order_by(
        "edificio__nombre_edificio",
        "zona__nombre_zona",
        "referencia",
    )
    context = {
        "items": items,
        "categoria_choices": CategoriaEquipo.objects.order_by(
            "nombre_categoria"
        ).values_list("id", "nombre_categoria"),
        "estado_choices": EstadoEquipo.choices,
        "ubicacion_choices": [(ubicacion.pk, str(ubicacion)) for ubicacion in ubicaciones],
        "search_query": search_query,
        "selected_categoria": selected_categoria,
        "selected_estado": selected_estado,
        "selected_activo": selected_activo,
        "selected_ubicacion": selected_ubicacion,
        "fecha_alta_desde": fecha_desde_raw,
        "fecha_alta_hasta": fecha_hasta_raw,
        "fecha_alta_mes": fecha_mes,
        "fecha_alta_rango": fecha_rango,
    }
    return render(request, "equipo/list.html", context)


def equipo_create(request):
    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES)
        if form.is_valid():
            equipo = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.EQUIPO,
                titulo=f"Equipo dado de alta: {equipo.codigo_inventario}",
                objeto=equipo,
                enlace_nombre="equipo_update",
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
            return redirect("equipo_list")
    else:
        form = EquipoForm()
    return render(request, "equipo/form.html", {"form": form})


def equipo_update(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    ubicacion_anterior = equipo.ubicacion
    estado_anterior = equipo.estado_equipo
    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES, instance=equipo)
        if form.is_valid():
            equipo = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.EQUIPO,
                titulo=f"Equipo actualizado: {equipo.codigo_inventario}",
                objeto=equipo,
                form=form,
                enlace_nombre="equipo_update",
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
            return redirect("equipo_list")
    else:
        form = EquipoForm(instance=equipo)
    return render(request, "equipo/form.html", {"form": form, "object": equipo})


def equipo_delete(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    if request.method == "POST":
        etiqueta = equipo.codigo_inventario
        _crear_movimiento(
            equipo,
            TipoMovimiento.DADA_DE_BAJA,
            origen=equipo.ubicacion,
            destino=None,
            responsable=_get_equipo_responsable(equipo),
            request=request,
        )
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.EQUIPO,
            titulo=f"Equipo dado de baja: {etiqueta}",
            objeto=equipo,
            metadata={"codigo_inventario": etiqueta},
            nivel=NivelHistorial.CRITICO,
        )
        equipo.delete()
        messages.success(request, "Equipo eliminado correctamente.")
        return redirect("equipo_list")
    return render(request, "equipo/confirm_delete.html", {"object": equipo})

# ============  MovimientoEquipo views ==============
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
    items = MovimientoEquipo.objects.select_related("equipo", "responsable").order_by("-fecha_movimiento")
    return render(request, "movimientoequipo/registros.html", {"items": items})


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
                enlace_nombre="movimientoequipo_update",
                metadata={"tipo_movimiento": movimiento.tipo_movimiento},
            )
            messages.success(request, "Movimiento creado correctamente.")
            return redirect("movimientoequipo_list")
    else:
        form = MovimientoEquipoForm()
    return render(request, "movimientoequipo/form.html", {"form": form})


def movimientoequipo_update(request, pk):
    movimiento = get_object_or_404(MovimientoEquipo, pk=pk)
    if request.method == "POST":
        form = MovimientoEquipoForm(request.POST, instance=movimiento)
        if form.is_valid():
            movimiento = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.MOVIMIENTO_EQUIPO,
                titulo=f"Movimiento actualizado: {movimiento.equipo}",
                objeto=movimiento,
                form=form,
                enlace_nombre="movimientoequipo_update",
            )
            messages.success(request, "Movimiento actualizado correctamente.")
            return redirect("movimientoequipo_list")
    else:
        form = MovimientoEquipoForm(instance=movimiento)
    return render(request, "movimientoequipo/form.html", {"form": form, "object": movimiento})


def movimientoequipo_delete(request, pk):
    movimiento = get_object_or_404(MovimientoEquipo, pk=pk)
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.MOVIMIENTO_EQUIPO,
            titulo=f"Movimiento eliminado: {movimiento.equipo}",
            objeto=movimiento,
        )
        movimiento.delete()
        messages.success(request, "Movimiento eliminado correctamente.")
        return redirect("movimientoequipo_list")
    return render(request, "movimientoequipo/confirm_delete.html", {"object": movimiento})

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
    if request.method == "POST":
        form = AsignacionEquipoForm(request.POST)
        if form.is_valid():
            equipo = form.cleaned_data.get("equipo")
            personal = form.cleaned_data.get("personal")
            existente_activo = False
            if equipo:
                existente_activo = AsignacionEquipo.objects.filter(
                    equipo=equipo,
                    estado_asignacion=EstadoAsignacion.ACTIVA,
                ).exists()
            asignacion = form.save()
            historial.registrar_historial(
                request=request,
                modulo=ModuloHistorial.ASIGNACION,
                accion=historial.AccionHistorial.ASIGNACION,
                titulo=f"Asignacion de {equipo} a {personal}",
                objeto=asignacion,
                entidad_relacionada=equipo,
                enlace_nombre="asignacionequipo_update",
            )
            if equipo:
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
            return redirect("asignacionequipo_list")
    else:
        form = AsignacionEquipoForm()
    return render(request, "asignacionequipo/form.html", {"form": form})


def asignacionequipo_update(request, pk):
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    equipo_anterior_id = asignacion.equipo_id
    personal_anterior_id = asignacion.personal_id
    if request.method == "POST":
        form = AsignacionEquipoForm(request.POST, instance=asignacion)
        if form.is_valid():
            asignacion = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.ASIGNACION,
                titulo=f"Asignacion actualizada: {asignacion.equipo} / {asignacion.personal}",
                objeto=asignacion,
                form=form,
                entidad_relacionada=asignacion.equipo,
                enlace_nombre="asignacionequipo_update",
            )
            if (
                asignacion.equipo_id != equipo_anterior_id
                or asignacion.personal_id != personal_anterior_id
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
            return redirect("asignacionequipo_list")
    else:
        form = AsignacionEquipoForm(instance=asignacion)
    return render(request, "asignacionequipo/form.html", {"form": form, "object": asignacion})


def asignacionequipo_delete(request, pk):
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.ASIGNACION,
            titulo=f"Asignacion eliminada: {asignacion.equipo} / {asignacion.personal}",
            objeto=asignacion,
        )
        asignacion.delete()
        messages.success(request, "Asignacion eliminada correctamente.")
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
            "estado_mantenimiento",
            "fecha_programada",
            "tecnico_responsable",
            "costo_mantenimiento",
            "descripcion_falla",
        ]
        labels = {
            "equipo": "Equipo",
            "tipo_mantenimiento": "Tipo de mantenimiento",
            "estado_mantenimiento": "Estado del mantenimiento",
            "fecha_programada": "Fecha programada",
            "tecnico_responsable": "Técnico responsable",
            "proveedor_responsable": "Proveedor responsable",
            "costo_mantenimiento": "Costo del mantenimiento",
            "descripcion_falla": "Descripción de la falla o razón",
        }
        help_texts = {
            "descripcion_falla": "Describe la falla o razón del mantenimiento.",
            "costo_mantenimiento": "Costo estimado o real del mantenimiento (si aplica es que aplica).",
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
            "estado_mantenimiento",
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

def mantenimiento_list(request):
    items = Mantenimiento.objects.select_related("equipo", "cierre").all()
    return render(request, "mantenimiento/list.html", {"items": items})


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
                enlace_nombre="mantenimiento_update",
            )
            messages.success(request, "Mantenimiento creado correctamente.")
            return redirect("mantenimiento_list")
    else:
        form = MantenimientoForm()
    return render(request, "mantenimiento/form.html", {"form": form})


def mantenimiento_update(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
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
                enlace_nombre="mantenimiento_update",
            )
            messages.success(request, "Mantenimiento actualizado correctamente.")
            return redirect("mantenimiento_list")
    else:
        form = MantenimientoForm(instance=mantenimiento)
    return render(request, "mantenimiento/form.html", {"form": form, "object": mantenimiento})


def mantenimiento_delete(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method == "POST":
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
            "mantenimiento": "Seleccione el mantenimiento.",
            "acciones_realizadas": "Describa las acciones realizadas durante el mantenimiento.",
            "observaciones": "Opcional. Puede agregar observaciones adicionales.",
        }
        widgets = {
            "fecha_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "fecha_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
            "proxima_fecha_mantenimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["acciones_realizadas"].required = True
        self.fields["fecha_fin"].required = True
        qs = Mantenimiento.objects.select_related("equipo").order_by("fecha_programada")
        if self.instance and self.instance.pk:
            qs = Mantenimiento.objects.filter(pk=self.instance.mantenimiento_id) | qs.filter(
                cierre__isnull=True
            )
            self.fields["mantenimiento"].disabled = True
        else:
            qs = qs.filter(cierre__isnull=True)
        self.fields["mantenimiento"].queryset = qs.distinct()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            mantenimiento = instance.mantenimiento
            if mantenimiento.estado_mantenimiento != EstadoMantenimiento.COMPLETADO:
                mantenimiento.estado_mantenimiento = EstadoMantenimiento.COMPLETADO
                mantenimiento.save(update_fields=["estado_mantenimiento"])
        return instance

def agendamantenimiento_list(request):
    items = AgendaMantenimiento.objects.select_related("mantenimiento").all()
    return render(request, "agendamantenimiento/list.html", {"items": items})


def agendamantenimiento_create(request):
    if request.method == "POST":
        form = AgendaMantenimientoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Agenda creada correctamente.")
            return redirect("agendamantenimiento_list")
    else:
        form = AgendaMantenimientoForm()
    return render(request, "agendamantenimiento/form.html", {"form": form})


def agendamantenimiento_update(request, pk):
    agenda = get_object_or_404(AgendaMantenimiento, pk=pk)
    if request.method == "POST":
        form = AgendaMantenimientoForm(request.POST, instance=agenda)
        if form.is_valid():
            form.save()
            messages.success(request, "Agenda actualizada correctamente.")
            return redirect("agendamantenimiento_list")
    else:
        form = AgendaMantenimientoForm(instance=agenda)
    return render(request, "agendamantenimiento/form.html", {"form": form, "object": agenda})


def agendamantenimiento_delete(request, pk):
    agenda = get_object_or_404(AgendaMantenimiento, pk=pk)
    if request.method == "POST":
        agenda.delete()
        messages.success(request, "Agenda eliminada correctamente.")
        return redirect("agendamantenimiento_list")
    return render(request, "agendamantenimiento/confirm_delete.html", {"object": agenda})


# ============ TicketIT views ==============
# Formulario de ticket



def ticketit_list(request):
    items = TicketIT.objects.all()
    selected_tipo = request.GET.get("tipo_ticket", "")
    selected_prioridad = request.GET.get("prioridad", "")
    selected_status = request.GET.get("status", "")

    if selected_tipo:
        items = items.filter(tipo_ticket=selected_tipo)
    if selected_prioridad:
        items = items.filter(prioridad=selected_prioridad)
    if selected_status:
        items = items.filter(status=selected_status)

    context = {
        "items": items,
        "tipo_choices": TipoTicketSupport.choices,
        "prioridad_choices": PrioridadSupport.choices,
        "status_choices": EstadoSupport.choices,
        "selected_tipo": selected_tipo,
        "selected_prioridad": selected_prioridad,
        "selected_status": selected_status,
    }
    return render(request, "ticketit/list.html", context)


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
                enlace_nombre="ticketit_update",
                metadata={"estado": ticket.status, "prioridad": ticket.prioridad},
            )
            messages.success(request, "Support creado correctamente.")
            return redirect("ticketit_list")
    else:
        form = TicketITForm(request_user=request.user)
    return render(request, "ticketit/form.html", {"form": form})


def ticketit_update(request, pk):
    ticket = get_object_or_404(TicketIT, pk=pk)
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
                enlace_nombre="ticketit_update",
            )
            messages.success(request, "Support actualizado correctamente.")
            return redirect("ticketit_list")
    else:
        form = TicketITForm(instance=ticket, request_user=request.user)
    return render(request, "ticketit/form.html", {"form": form, "object": ticket})


def ticketit_delete(request, pk):
    ticket = get_object_or_404(TicketIT, pk=pk)
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
    return render(request, "ticketit/confirm_delete.html", {"object": ticket})


def ticketit_subtipo_choices(request):
    tipo_ticket = request.GET.get("tipo_ticket")
    choices = get_subtipo_ticket_choices(tipo_ticket)
    data = [{"value": value, "label": label} for value, label in choices]
    return JsonResponse({"choices": data})

# ============ SeguimientoTicket views ==============



def seguimientoticket_list(request):
    items = SeguimientoTicket.objects.all()
    return render(request, "seguimientoticket/list.html", {"items": items})


def seguimientoticket_create(request):
    if request.method == "POST":
        form = SeguimientoTicketForm(request.POST)
        if form.is_valid():
            seguimiento = form.save()
            historial.registrar_creacion(
                request,
                modulo=ModuloHistorial.SEGUIMIENTO,
                titulo=f"Seguimiento en {seguimiento.folio_check or seguimiento.ticket}",
                objeto=seguimiento,
                entidad_relacionada=seguimiento.ticket,
                enlace_nombre="seguimientoticket_update",
                metadata={"ticket_id": seguimiento.ticket_id},
            )
            messages.success(request, "Check creado correctamente.")
            return redirect("seguimientoticket_list")
    else:
        form = SeguimientoTicketForm()
    return render(request, "seguimientoticket/form.html", {"form": form})


def seguimientoticket_update(request, pk):
    seguimiento = get_object_or_404(SeguimientoTicket, pk=pk)
    if request.method == "POST":
        form = SeguimientoTicketForm(request.POST, instance=seguimiento)
        if form.is_valid():
            seguimiento = form.save()
            historial.registrar_actualizacion(
                request,
                modulo=ModuloHistorial.SEGUIMIENTO,
                titulo=f"Seguimiento actualizado: {seguimiento.folio_check or seguimiento.pk}",
                objeto=seguimiento,
                form=form,
                entidad_relacionada=seguimiento.ticket,
                enlace_nombre="seguimientoticket_update",
            )
            messages.success(request, "Check actualizado correctamente.")
            return redirect("seguimientoticket_list")
    else:
        form = SeguimientoTicketForm(instance=seguimiento)
    return render(request, "seguimientoticket/form.html", {"form": form, "object": seguimiento})


def seguimientoticket_delete(request, pk):
    seguimiento = get_object_or_404(SeguimientoTicket, pk=pk)
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.SEGUIMIENTO,
            titulo=f"Seguimiento eliminado: {seguimiento.folio_check or seguimiento.pk}",
            objeto=seguimiento,
        )
        seguimiento.delete()
        messages.success(request, "Check eliminado correctamente.")
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
            "contacto": p.contacto or "",
            "telefono": p.telefono or "",
            "email": p.correo or "",
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
    items = OrdenCompra.objects.select_related("proveedor", "elaborado_por").all()
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
    if request.method == "POST":
        historial.registrar_eliminacion(
            request,
            modulo=ModuloHistorial.ORDEN_COMPRA,
            titulo=f"Orden de compra eliminada: {orden.folio_orden}",
            objeto=orden,
        )
        orden.delete()
        messages.success(request, "Orden de compra eliminada correctamente.")
        return redirect("ordencompra_list")
    return render(request, "ordencompra/confirm_delete.html", {"object": orden})


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
):
    event = {
        "title": title,
        "start": start.isoformat(),
        "allDay": all_day,
        "backgroundColor": color,
        "borderColor": color,
        "textColor": "#ffffff",
        "extendedProps": {
            "details": details,
            "caseType": case_type,
            "caseTypeLabel": case_type_label,
            "caseLabel": case_label,
            "actionUrl": action_url,
            "actionText": action_text,
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
    return value.date()


def _build_home_calendar_events():
    today = timezone.localdate()
    events = []

    for ticket in TicketIT.objects.select_related("area", "puesto", "solicitado_por").order_by("-fecha_support")[:80]:
        ticket_date = _calendar_day(ticket.fecha_support)
        events.append(
            _calendar_event(
                f"Ticket {ticket.folio_ticket}",
                ticket_date,
                color={
                    EstadoSupport.CERRADO: "#0f766e",
                    EstadoSupport.EN_PROCESO: "#1d4ed8",
                    EstadoSupport.EN_REVISION: "#7c3aed",
                    EstadoSupport.ABIERTO: "#f59e0b",
                }.get(ticket.status, "#475569"),
                details=[
                    {"label": "Estado", "value": _calendar_label(ticket.status)},
                    {"label": "Prioridad", "value": _calendar_label(ticket.prioridad)},
                    {"label": "Area", "value": _calendar_label(getattr(ticket.area, 'nombre_area', None))},
                    {"label": "Puesto", "value": _calendar_label(getattr(ticket.puesto, 'nombre_puesto', None))},
                    {"label": "Solicitado por", "value": _calendar_label(getattr(ticket.solicitado_por, 'username', None))},
                    {"label": "Requerimiento", "value": _calendar_label(ticket.requerimiento)},
                ],
                case_type="ticket",
                case_type_label="Ticket de soporte",
                case_label=ticket.folio_ticket,
                action_url=reverse("ticketit_update", args=[ticket.pk]),
                action_text="Abrir ticket",
            )
        )

    for movimiento in MovimientoEquipo.objects.select_related("equipo", "responsable").order_by("-fecha_movimiento")[:80]:
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
                    {"label": "Equipo", "value": _calendar_label(getattr(movimiento.equipo, 'codigo_inventario', None))},
                    {"label": "Origen", "value": _calendar_label(movimiento.origen)},
                    {"label": "Destino", "value": _calendar_label(movimiento.destino)},
                    {"label": "Responsable", "value": _calendar_label(str(movimiento.responsable) if movimiento.responsable else None)},
                    {"label": "Observaciones", "value": _calendar_label(movimiento.observaciones)},
                ],
                case_type="movimiento",
                case_type_label="Movimiento de equipo",
                case_label=_calendar_label(movimiento.tipo_movimiento),
                action_url=reverse("movimientoequipo_update", args=[movimiento.pk]),
                action_text="Abrir movimiento",
            )
        )

    for mantenimiento in Mantenimiento.objects.select_related("equipo").order_by("-fecha_programada")[:80]:
        color = "#1d4ed8"
        if mantenimiento.estado_mantenimiento == EstadoMantenimiento.COMPLETADO:
            color = "#0f766e"
        elif mantenimiento.estado_mantenimiento == EstadoMantenimiento.CANCELADO:
            color = "#b42318"
        elif mantenimiento.fecha_programada < today:
            color = "#dc2626"

        events.append(
            _calendar_event(
                f"Mantenimiento {mantenimiento.folio_mantenimiento()}",
                mantenimiento.fecha_programada,
                color=color,
                details=[
                    {"label": "Estado", "value": _calendar_label(mantenimiento.estado_mantenimiento)},
                    {"label": "Tipo", "value": _calendar_label(mantenimiento.tipo_mantenimiento)},
                    {"label": "Equipo", "value": _calendar_label(getattr(mantenimiento.equipo, 'codigo_inventario', None))},
                    {"label": "Responsable", "value": _calendar_label(mantenimiento.tecnico_responsable)},
                    {"label": "Costo", "value": _calendar_label(mantenimiento.costo_mantenimiento)},
                    *(
                        [{"label": "Proximo mantenimiento", "value": mantenimiento.cierre.proxima_fecha_mantenimiento.strftime('%Y-%m-%d')}]
                        if getattr(mantenimiento, "cierre", None) and mantenimiento.cierre.proxima_fecha_mantenimiento
                        else []
                    ),
                ],
                case_type="mantenimiento",
                case_type_label="Mantenimiento",
                case_label=mantenimiento.folio_mantenimiento(),
                action_url=reverse("mantenimiento_update", args=[mantenimiento.pk]),
                action_text="Abrir mantenimiento",
            )
        )

    for agenda in AgendaMantenimiento.objects.select_related("mantenimiento", "mantenimiento__equipo").order_by("-proxima_fecha_mantenimiento")[:80]:
        if not agenda.proxima_fecha_mantenimiento:
            continue
        events.append(
            _calendar_event(
                f"Seguimiento {agenda.mantenimiento.folio_mantenimiento()}",
                agenda.proxima_fecha_mantenimiento,
                color="#7c3aed",
                details=[
                    {"label": "Mantenimiento", "value": agenda.mantenimiento.folio_mantenimiento()},
                    {"label": "Equipo", "value": _calendar_label(getattr(agenda.mantenimiento.equipo, 'codigo_inventario', None))},
                    {"label": "Inicio", "value": agenda.fecha_inicio.strftime('%Y-%m-%d %H:%M') if agenda.fecha_inicio else 'Sin inicio'},
                    {"label": "Fin", "value": agenda.fecha_fin.strftime('%Y-%m-%d %H:%M') if agenda.fecha_fin else 'Sin fin'},
                    {"label": "Acciones", "value": _calendar_label(agenda.acciones_realizadas)},
                    {"label": "Observaciones", "value": _calendar_label(agenda.observaciones)},
                    {"label": "Proximo mantenimiento", "value": agenda.proxima_fecha_mantenimiento.strftime('%Y-%m-%d')},
                ],
                case_type="seguimiento",
                case_type_label="Seguimiento",
                case_label=agenda.mantenimiento.folio_mantenimiento(),
                action_url=reverse("agendamantenimiento_update", args=[agenda.pk]),
                action_text="Abrir seguimiento",
            )
        )

    for seguimiento in SeguimientoTicket.objects.select_related("ticket", "usuario").order_by("-fecha_check")[:80]:
        event_date = seguimiento.fecha_proximo_seguimiento or _calendar_day(seguimiento.fecha_check)
        events.append(
            _calendar_event(
                f"Check {seguimiento.folio_check or seguimiento.ticket.folio_ticket}",
                event_date,
                color="#7c3aed" if not seguimiento.ya_terminado else "#0f766e",
                details=[
                    {"label": "Ticket", "value": _calendar_label(getattr(seguimiento.ticket, 'folio_ticket', None))},
                    {"label": "Estado", "value": "Terminado" if seguimiento.ya_terminado else "Pendiente"},
                    {"label": "Avance", "value": _calendar_label(seguimiento.avance_realizado)},
                    {"label": "Pendiente", "value": _calendar_label(seguimiento.pendiente)},
                    {"label": "Proximo paso", "value": _calendar_label(seguimiento.proximo_paso)},
                    {"label": "Usuario", "value": _calendar_label(str(seguimiento.usuario) if seguimiento.usuario else None)},
                    {"label": "Observacion", "value": _calendar_label(seguimiento.observacion)},
                ],
                case_type="seguimiento_ticket",
                case_type_label="Check",
                case_label=seguimiento.folio_check or seguimiento.ticket.folio_ticket,
                action_url=reverse("seguimientoticket_update", args=[seguimiento.pk]),
                action_text="Abrir check",
            )
        )

    events.sort(key=lambda event: event["start"])
    return events


def home(request):
    today = timezone.localdate()
    tickets_abiertos_qs = TicketIT.objects.exclude(status=EstadoSupport.CERRADO)
    mantenimientos_proximos_qs = Mantenimiento.objects.select_related("equipo").filter(
        fecha_programada__gte=today,
        fecha_programada__lte=today + timedelta(days=30),
    ).order_by("fecha_programada")

    quick_links = [
        {"label": "Tickets", "url_name": "ticketit_list", "hint": "Soporte activo"},
        {"label": "Ordenes", "url_name": "ordencompra_list", "hint": "Compras"},
        {"label": "Calendario", "url_name": "home", "hint": "Agenda", "anchor": "#calendario"},
    ]
    if is_admin_user(request.user):
        quick_links = [
            {"label": "Tickets", "url_name": "ticketit_list", "hint": "Soporte activo"},
            {"label": "Equipos", "url_name": "equipo_list", "hint": "Inventario"},
            {"label": "Historial", "url_name": "movimientoequipo_list", "hint": "Actividad"},
            {"label": "Mantenimientos", "url_name": "mantenimiento_list", "hint": "Proximos"},
        ]

    context = {
        "calendar_events": _build_home_calendar_events(),
        "dashboard_counts": {
            "tickets": TicketIT.objects.count(),
            "tickets_abiertos": tickets_abiertos_qs.count(),
            "equipos_activos": Equipo.objects.filter(activo=True).count() if is_admin_user(request.user) else None,
            "mantenimientos_proximos": mantenimientos_proximos_qs.count(),
            "agendas_proximas": AgendaMantenimiento.objects.filter(
                proxima_fecha_mantenimiento__gte=today,
                proxima_fecha_mantenimiento__lte=today + timedelta(days=30),
            ).count(),
            "historial_hoy": HistorialActividad.objects.filter(
                fecha__date=today,
                archivado=False,
            ).count() if is_admin_user(request.user) else None,
        },
        "quick_links": quick_links,
        "recent_tickets": tickets_abiertos_qs.select_related(
            "area", "solicitado_por", "tipo_equipo"
        ).order_by("-fecha_support")[:6],
        "upcoming_mantenimientos": list(mantenimientos_proximos_qs[:6]),
        "recent_historial": list(
            HistorialActividad.objects.select_related("usuario")
            .filter(archivado=False)
            .order_by("-fecha")[:8]
        ) if is_admin_user(request.user) else [],
        "is_admin_dashboard": is_admin_user(request.user),
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





















































