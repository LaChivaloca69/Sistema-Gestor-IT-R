"""Roles de la aplicacion: Usuario, Tecnico IT y Administrador."""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q
from django.shortcuts import redirect

ROLE_USUARIO = "Usuario"
ROLE_TECNICO = "Tecnico IT"
ROLE_ADMIN = "Administrador"

ROLE_CHOICES = (
    (ROLE_USUARIO, "Usuario"),
    (ROLE_TECNICO, "Tecnico IT"),
    (ROLE_ADMIN, "Administrador"),
)

ROLE_PRIORITY = (ROLE_ADMIN, ROLE_TECNICO, ROLE_USUARIO)


def ensure_role_groups():
    """Crea los grupos de rol si no existen."""
    for name in (ROLE_USUARIO, ROLE_TECNICO, ROLE_ADMIN):
        Group.objects.get_or_create(name=name)


def _group_names(user):
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    if hasattr(user, "_role_group_names_cache"):
        return user._role_group_names_cache
    names = set(user.groups.values_list("name", flat=True))
    user._role_group_names_cache = names
    return names


def get_user_role(user):
    """Devuelve el rol efectivo del usuario (Admin > Tecnico > Usuario)."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return ROLE_ADMIN
    names = _group_names(user)
    for role in ROLE_PRIORITY:
        if role in names:
            return role
    # Compatibilidad temporal con cuentas antiguas solo-is_staff.
    if getattr(user, "is_staff", False):
        return ROLE_ADMIN
    return ROLE_USUARIO


def is_administrador(user):
    return get_user_role(user) == ROLE_ADMIN


def is_tecnico(user):
    return get_user_role(user) == ROLE_TECNICO


def is_operativo(user):
    """Tecnico IT o Administrador (operacion diaria)."""
    return get_user_role(user) in {ROLE_TECNICO, ROLE_ADMIN}


def is_admin_user(user):
    """Alias: privilegios de Administrador (no incluye Tecnico IT)."""
    return is_administrador(user)


def set_user_role(user, role, *, clear_cache=True):
    """Asigna exactamente un rol de negocio y sincroniza is_staff."""
    if role not in {ROLE_USUARIO, ROLE_TECNICO, ROLE_ADMIN}:
        raise ValueError(f"Rol no valido: {role}")
    if not user or not getattr(user, "pk", None):
        raise ValueError("Usuario invalido para asignar rol.")

    ensure_role_groups()
    groups = {
        g.name: g
        for g in Group.objects.filter(name__in=[ROLE_USUARIO, ROLE_TECNICO, ROLE_ADMIN])
    }
    role_groups = list(groups.values())
    if role_groups:
        user.groups.remove(*role_groups)
    user.groups.add(groups[role])

    # Solo Administrador (y superuser) conservan is_staff para /admin/ de Django.
    desired_staff = bool(user.is_superuser or role == ROLE_ADMIN)
    if user.is_staff != desired_staff:
        user.is_staff = desired_staff
        user.save(update_fields=["is_staff"])

    if clear_cache and hasattr(user, "_role_group_names_cache"):
        delattr(user, "_role_group_names_cache")
    return role


def operativo_users_queryset(user_model=None):
    """Usuarios que pueden atender tickets / operacion IT."""
    from django.contrib.auth import get_user_model

    user_model = user_model or get_user_model()
    qs = user_model.objects.filter(
        Q(is_superuser=True)
        | Q(groups__name__in=[ROLE_TECNICO, ROLE_ADMIN])
        | Q(is_staff=True)
    )
    if any(field.name == "is_active" for field in user_model._meta.fields):
        qs = qs.filter(is_active=True)
    return qs.distinct().order_by(user_model.USERNAME_FIELD)


def _deny(request, message="No tienes permisos para acceder a esta seccion."):
    messages.error(request, message)
    return redirect("home")


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not is_administrador(request.user):
            return _deny(request)
        return view_func(request, *args, **kwargs)

    return _wrapped


def operativo_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not is_operativo(request.user):
            return _deny(request)
        return view_func(request, *args, **kwargs)

    return _wrapped
