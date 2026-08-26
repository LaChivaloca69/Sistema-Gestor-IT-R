from .roles import get_user_role, is_administrador, is_operativo, is_tecnico
from .breadcrumbs import build_breadcrumbs
from .nav_badges import build_nav_badges, build_nav_notifications


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
    if not user:
        return {
            "nav_badges": {},
            "nav_notifications": [],
            "nav_notifications_total": 0,
        }
    badges = build_nav_badges(user)
    notifications, total = build_nav_notifications(user, badges=badges)
    return {
        "nav_badges": badges,
        "nav_notifications": notifications,
        "nav_notifications_total": total,
    }


def inventario_nav(request):
    """Resalta Equipos/Perifericos/Herramientas segun el tipo de la pantalla actual."""
    return {
        "inventario_list_url_name": getattr(request, "inventario_list_url_name", None),
    }

