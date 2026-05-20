from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

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
    CompraMaterial,
    DetalleCompraMaterial,
    DetallePresupuesto,
    Edificio,
    Equipo,
    EstadoSupport,
    Mantenimiento,
    MovimientoEquipo,
    Personal,
    Presupuesto,
    PrioridadSupport,
    Proveedor,
    Puesto,
    SeguimientoTicket,
    TicketIT,
    TipoTicketSupport,
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

# =========== Area views ==============
class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = "__all__"

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
class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = "__all__"

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
        label="Accion de usuario",
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
                self.add_error("password1", "Captura la contrasena.")
            elif password1 != password2:
                self.add_error("password2", "Las contrasenas no coinciden.")
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
    items = Personal.objects.select_related("user").all()
    return render(request, "personal/list.html", {"items": items})


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
        else:
            if personal.admin_requested:
                personal.admin_requested = False
                personal.save(update_fields=["admin_requested"])
            messages.success(request, "Solicitud rechazada.")
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
        return redirect("personal_admin_remove")
    items = (
        Personal.objects.select_related("user")
        .filter(user__is_staff=True)
        .exclude(user__is_superuser=True)
    )
    return render(request, "personal/admin_remove.html", {"items": items})


def personal_create(request):
    if request.method == "POST":
        form = PersonalForm(request.POST, request_user=request.user)
        if form.is_valid():
            form.save()
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
            form.save()
            messages.success(request, "Personal actualizado correctamente.")
            return redirect("personal_list")
    else:
        form = PersonalForm(instance=personal, request_user=request.user)
    return render(request, "personal/form.html", {"form": form, "object": personal})


def personal_delete(request, pk):
    personal = get_object_or_404(Personal, pk=pk)
    if request.method == "POST":
        personal.delete()
        messages.success(request, "Personal eliminado correctamente.")
        return redirect("personal_list")
    return render(request, "personal/confirm_delete.html", {"object": personal})

# ============  Proveedor views ==============
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = "__all__"

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
class EdificioForm(forms.ModelForm):
    class Meta:
        model = Edificio
        fields = "__all__"

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
class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = "__all__"

def ubicacion_list(request):
    items = Ubicacion.objects.all()
    return render(request, "ubicacion/list.html", {"items": items})


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
class CategoriaEquipoForm(forms.ModelForm):
    class Meta:
        model = CategoriaEquipo
        fields = "__all__"

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
    items = Equipo.objects.all()
    return render(request, "equipo/list.html", {"items": items})


def equipo_create(request):
    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Equipo creado correctamente.")
            return redirect("equipo_list")
    else:
        form = EquipoForm()
    return render(request, "equipo/form.html", {"form": form})


def equipo_update(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    if request.method == "POST":
        form = EquipoForm(request.POST, request.FILES, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, "Equipo actualizado correctamente.")
            return redirect("equipo_list")
    else:
        form = EquipoForm(instance=equipo)
    return render(request, "equipo/form.html", {"form": form, "object": equipo})


def equipo_delete(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    if request.method == "POST":
        equipo.delete()
        messages.success(request, "Equipo eliminado correctamente.")
        return redirect("equipo_list")
    return render(request, "equipo/confirm_delete.html", {"object": equipo})

# ============  MovimientoEquipo views ==============
class MovimientoEquipoForm(forms.ModelForm):
    class Meta:
        model = MovimientoEquipo
        fields = "__all__"

def movimientoequipo_list(request):
    items = MovimientoEquipo.objects.all()
    return render(request, "movimientoequipo/list.html", {"items": items})


def movimientoequipo_create(request):
    if request.method == "POST":
        form = MovimientoEquipoForm(request.POST)
        if form.is_valid():
            form.save()
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
            form.save()
            messages.success(request, "Movimiento actualizado correctamente.")
            return redirect("movimientoequipo_list")
    else:
        form = MovimientoEquipoForm(instance=movimiento)
    return render(request, "movimientoequipo/form.html", {"form": form, "object": movimiento})


def movimientoequipo_delete(request, pk):
    movimiento = get_object_or_404(MovimientoEquipo, pk=pk)
    if request.method == "POST":
        movimiento.delete()
        messages.success(request, "Movimiento eliminado correctamente.")
        return redirect("movimientoequipo_list")
    return render(request, "movimientoequipo/confirm_delete.html", {"object": movimiento})

# ============  AsignacionEquipo views ==============
class AsignacionEquipoForm(forms.ModelForm):
    class Meta:
        model = AsignacionEquipo
        fields = "__all__"

def asignacionequipo_list(request):
    items = AsignacionEquipo.objects.all()
    return render(request, "asignacionequipo/list.html", {"items": items})


def asignacionequipo_create(request):
    if request.method == "POST":
        form = AsignacionEquipoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Asignacion creada correctamente.")
            return redirect("asignacionequipo_list")
    else:
        form = AsignacionEquipoForm()
    return render(request, "asignacionequipo/form.html", {"form": form})


def asignacionequipo_update(request, pk):
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    if request.method == "POST":
        form = AsignacionEquipoForm(request.POST, instance=asignacion)
        if form.is_valid():
            form.save()
            messages.success(request, "Asignacion actualizada correctamente.")
            return redirect("asignacionequipo_list")
    else:
        form = AsignacionEquipoForm(instance=asignacion)
    return render(request, "asignacionequipo/form.html", {"form": form, "object": asignacion})


def asignacionequipo_delete(request, pk):
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    if request.method == "POST":
        asignacion.delete()
        messages.success(request, "Asignacion eliminada correctamente.")
        return redirect("asignacionequipo_list")
    return render(request, "asignacionequipo/confirm_delete.html", {"object": asignacion})


# ============= Mantenimiento views ==============
class MantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "equipo" in self.fields:
            self.fields["equipo"].label_from_instance = (
                lambda obj: f"{obj.codigo_inventario} - {obj.categoria}"
            )

def mantenimiento_list(request):
    items = Mantenimiento.objects.all()
    return render(request, "mantenimiento/list.html", {"items": items})


def mantenimiento_create(request):
    if request.method == "POST":
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            form.save()
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
            form.save()
            messages.success(request, "Mantenimiento actualizado correctamente.")
            return redirect("mantenimiento_list")
    else:
        form = MantenimientoForm(instance=mantenimiento)
    return render(request, "mantenimiento/form.html", {"form": form, "object": mantenimiento})


def mantenimiento_delete(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    if request.method == "POST":
        mantenimiento.delete()
        messages.success(request, "Mantenimiento eliminado correctamente.")
        return redirect("mantenimiento_list")
    return render(request, "mantenimiento/confirm_delete.html", {"object": mantenimiento})


# ============ AgendaMantenimiento views ==============
class AgendaMantenimientoForm(forms.ModelForm):
    class Meta:
        model = AgendaMantenimiento
        fields = "__all__"

def agendamantenimiento_list(request):
    items = AgendaMantenimiento.objects.all()
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
            form.save()
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
            form.save()
            messages.success(request, "Support actualizado correctamente.")
            return redirect("ticketit_list")
    else:
        form = TicketITForm(instance=ticket, request_user=request.user)
    return render(request, "ticketit/form.html", {"form": form, "object": ticket})


def ticketit_delete(request, pk):
    ticket = get_object_or_404(TicketIT, pk=pk)
    if request.method == "POST":
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
            form.save()
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
            form.save()
            messages.success(request, "Check actualizado correctamente.")
            return redirect("seguimientoticket_list")
    else:
        form = SeguimientoTicketForm(instance=seguimiento)
    return render(request, "seguimientoticket/form.html", {"form": form, "object": seguimiento})


def seguimientoticket_delete(request, pk):
    seguimiento = get_object_or_404(SeguimientoTicket, pk=pk)
    if request.method == "POST":
        seguimiento.delete()
        messages.success(request, "Check eliminado correctamente.")
        return redirect("seguimientoticket_list")
    return render(request, "seguimientoticket/confirm_delete.html", {"object": seguimiento})



# =========== Bitacora views =============
class BitacoraForm(forms.ModelForm):
    class Meta:
        model = Bitacora
        fields = "__all__"

def bitacora_list(request):
    items = Bitacora.objects.all()
    return render(request, "bitacora/list.html", {"items": items})


def bitacora_create(request):
    if request.method == "POST":
        form = BitacoraForm(request.POST)
        if form.is_valid():
            form.save()
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
            form.save()
            messages.success(request, "Bitacora actualizada correctamente.")
            return redirect("bitacora_list")
    else:
        form = BitacoraForm(instance=bitacora)
    return render(request, "bitacora/form.html", {"form": form, "object": bitacora})


def bitacora_delete(request, pk):
    bitacora = get_object_or_404(Bitacora, pk=pk)
    if request.method == "POST":
        bitacora.delete()
        messages.success(request, "Bitacora eliminada correctamente.")
        return redirect("bitacora_list")
    return render(request, "bitacora/confirm_delete.html", {"object": bitacora})


# =========== Answer views =============
class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = "__all__"

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


# =========== Presupuesto views =============
class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = [
            "folio_presupuesto",
            "cliente_o_area",
            "elaborado_por",
            "numero_pedimiento",
            "numero_importacion",
            "fecha_compra",
            "archivo_pdf",
            "estado_presupuesto",
            "notas",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("estado_presupuesto")
        if field and self.instance and self.instance.pk:
            current = self.instance.estado_presupuesto
            if current and current not in dict(field.choices):
                field.choices = list(field.choices) + [(current, current)]

    def clean_archivo_pdf(self):
        archivo = self.cleaned_data.get("archivo_pdf")
        if not archivo:
            return archivo

        max_size = 50 * 1024 * 1024
        if archivo.size > max_size:
            raise forms.ValidationError("El archivo debe pesar menos de 50 MB.")

        allowed_types = {"application/pdf"}
        content_type = getattr(archivo, "content_type", None)
        if content_type and content_type not in allowed_types:
            raise forms.ValidationError("Formato no permitido. Solo PDF.")

        if not archivo.name.lower().endswith(".pdf"):
            raise forms.ValidationError("El archivo debe tener extension .pdf.")

        return archivo

def presupuesto_list(request):
    items = Presupuesto.objects.all()
    return render(request, "presupuesto/list.html", {"items": items})

def presupuesto_create(request):
    if request.method == "POST":
        form = PresupuestoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Presupuesto creado correctamente.")
            return redirect("presupuesto_list")
    else:
        form = PresupuestoForm()
    return render(request, "presupuesto/form.html", {"form": form})

def presupuesto_update(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    if request.method == "POST":
        form = PresupuestoForm(request.POST, request.FILES, instance=presupuesto)
        if form.is_valid():
            form.save()
            messages.success(request, "Presupuesto actualizado correctamente.")
            return redirect("presupuesto_list")
    else:
        form = PresupuestoForm(instance=presupuesto)
    return render(request, "presupuesto/form.html", {"form": form, "object": presupuesto})

def presupuesto_delete(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    if request.method == "POST":
        presupuesto.delete()
        messages.success(request, "Presupuesto eliminado correctamente.")
        return redirect("presupuesto_list")
    return render(request, "presupuesto/confirm_delete.html", {"object": presupuesto})


# =========== DetallePresupuesto views =============
class DetallePresupuestoForm(forms.ModelForm):
    class Meta:
        model = DetallePresupuesto
        fields = "__all__"

def Detallepresupuesto_list(request):
    items = DetallePresupuesto.objects.all()
    return render(request, "detallepresupuesto/list.html", {"items": items})

def Detallepresupuesto_create(request):
    if request.method == "POST":
        form = DetallePresupuestoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Detalle creado correctamente.")
            return redirect("detallepresupuesto_list")
    else:
        form = DetallePresupuestoForm()
    return render(request, "detallepresupuesto/form.html", {"form": form})

def Detallepresupuesto_update(request, pk):
    detalle = get_object_or_404(DetallePresupuesto, pk=pk)
    if request.method == "POST":
        form = DetallePresupuestoForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            messages.success(request, "Detalle actualizado correctamente.")
            return redirect("detallepresupuesto_list")
    else:
        form = DetallePresupuestoForm(instance=detalle)
    return render(request, "detallepresupuesto/form.html", {"form": form, "object": detalle})

def Detallepresupuesto_delete(request, pk):
    detalle = get_object_or_404(DetallePresupuesto, pk=pk)
    if request.method == "POST":
        detalle.delete()
        messages.success(request, "Detalle eliminado correctamente.")
        return redirect("detallepresupuesto_list")
    return render(request, "detallepresupuesto/confirm_delete.html", {"object": detalle})


# =============== CompraMaterial views =================
class CompraMaterialForm(forms.ModelForm):
    class Meta:
        model = CompraMaterial
        fields = [
            "folio_compra",
            "fecha_compra",
            "archivo_pdf",
            "proveedor",
            "solicitado_por",
            "estado_compra",
            "observaciones",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("estado_compra")
        if field and self.instance and self.instance.pk:
            current = self.instance.estado_compra
            if current and current not in dict(field.choices):
                field.choices = list(field.choices) + [(current, current)]

    def clean_archivo_pdf(self):
        archivo = self.cleaned_data.get("archivo_pdf")
        if not archivo:
            return archivo

        max_size = 50 * 1024 * 1024
        if archivo.size > max_size:
            raise forms.ValidationError("El archivo debe pesar menos de 50 MB.")

        allowed_types = {"application/pdf"}
        content_type = getattr(archivo, "content_type", None)
        if content_type and content_type not in allowed_types:
            raise forms.ValidationError("Formato no permitido. Solo PDF.")

        if not archivo.name.lower().endswith(".pdf"):
            raise forms.ValidationError("El archivo debe tener extension .pdf.")

        return archivo

def compramaterial_list(request):
    items = CompraMaterial.objects.all()
    return render(request, "compramaterial/list.html", {"items": items})


def compramaterial_create(request):
    if request.method == "POST":
        form = CompraMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Compra creada correctamente.")
            return redirect("compramaterial_list")
    else:
        form = CompraMaterialForm()
    return render(request, "compramaterial/form.html", {"form": form})


def compramaterial_update(request, pk):
    compra = get_object_or_404(CompraMaterial, pk=pk)
    if request.method == "POST":
        form = CompraMaterialForm(request.POST, request.FILES, instance=compra)
        if form.is_valid():
            form.save()
            messages.success(request, "Compra actualizada correctamente.")
            return redirect("compramaterial_list")
    else:
        form = CompraMaterialForm(instance=compra)
    return render(request, "compramaterial/form.html", {"form": form, "object": compra})


def compramaterial_delete(request, pk):
    compra = get_object_or_404(CompraMaterial, pk=pk)
    if request.method == "POST":
        compra.delete()
        messages.success(request, "Compra eliminada correctamente.")
        return redirect("compramaterial_list")
    return render(request, "compramaterial/confirm_delete.html", {"object": compra})


# ============== DetalleCompraMaterial views =================
class DetalleCompraMaterialForm(forms.ModelForm):
    class Meta:
        model = DetalleCompraMaterial
        fields = "__all__"

def detallecompramaterial_list(request):
    items = DetalleCompraMaterial.objects.all()
    return render(request, "detallecompramaterial/list.html", {"items": items})


def detallecompramaterial_create(request):
    if request.method == "POST":
        form = DetalleCompraMaterialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Detalle creado correctamente.")
            return redirect("detallecompramaterial_list")
    else:
        form = DetalleCompraMaterialForm()
    return render(request, "detallecompramaterial/form.html", {"form": form})


def detallecompramaterial_update(request, pk):
    detalle = get_object_or_404(DetalleCompraMaterial, pk=pk)
    if request.method == "POST":
        form = DetalleCompraMaterialForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            messages.success(request, "Detalle actualizado correctamente.")
            return redirect("detallecompramaterial_list")
    else:
        form = DetalleCompraMaterialForm(instance=detalle)
    return render(request, "detallecompramaterial/form.html", {"form": form, "object": detalle})


def detallecompramaterial_delete(request, pk):
    detalle = get_object_or_404(DetalleCompraMaterial, pk=pk)
    if request.method == "POST":
        detalle.delete()
        messages.success(request, "Detalle eliminado correctamente.")
        return redirect("detallecompramaterial_list")
    return render(request, "detallecompramaterial/confirm_delete.html", {"object": detalle})



def home(request):
    return render(request, "home.html")


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





















































