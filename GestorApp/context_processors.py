from .roles import get_user_role, is_administrador, is_operativo, is_tecnico
from .breadcrumbs import build_breadcrumbs
from .nav_badges import build_nav_badges


def roles(request):
    user = getattr(request, "user", None)
    return {
        "user_role": get_user_role(user) if user and user.is_authenticated else None,
        "is_admin_role": is_administrador(user) if user else False,
        "is_tecnico_role": is_tecnico(user) if user else False,
        "is_operativo_role": is_operativo(user) if user else False,
    }


def breadcrumbs(request):
    return {"breadcrumb_items": build_breadcrumbs(request)}


def nav_badges(request):
    user = getattr(request, "user", None)
    return {"nav_badges": build_nav_badges(user) if user else {}}

