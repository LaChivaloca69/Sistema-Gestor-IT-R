"""Catalogo de problemas guiados para creacion de tickets por usuarios."""

from .models import PrioridadSupport, TipoTicketSupport

CATALOGO_PROBLEMAS = [
    {
        "id": "contrasenas",
        "titulo": "Contraseñas y accesos",
        "icono": "bi-shield-lock",
        "descripcion": "Usuario bloqueado, olvido de contraseña, problemas para iniciar sesión.",
        "tipo_ticket": TipoTicketSupport.HELPDESK,
        "sub_tipo_ticket": "Problemas de Password",
        "prioridad_sugerida": PrioridadSupport.MEDIA,
        "prioridad_badge": "prio-media",
        "requiere_equipo": False,
    },
    {
        "id": "computadora",
        "titulo": "Mi computadora o laptop",
        "icono": "bi-laptop",
        "descripcion": "No enciende, pantalla azul, equipo lento, teclado o mouse con falla.",
        "tipo_ticket": TipoTicketSupport.HARDWARE,
        "sub_tipo_ticket": "Laptop",
        "prioridad_sugerida": PrioridadSupport.MEDIA,
        "prioridad_badge": "prio-media",
        "requiere_equipo": True,
    },
    {
        "id": "impresora",
        "titulo": "Impresora o escáner",
        "icono": "bi-printer",
        "descripcion": "No imprime, atasco de papel, tóner agotado, escáner desconectado.",
        "tipo_ticket": TipoTicketSupport.HELPDESK,
        "sub_tipo_ticket": "Impresora",
        "prioridad_sugerida": PrioridadSupport.BAJA,
        "prioridad_badge": "prio-baja",
        "requiere_equipo": False,
    },
    {
        "id": "correo_office",
        "titulo": "Correo, Teams y Office",
        "icono": "bi-envelope-at",
        "descripcion": "Outlook no abre, Teams no conecta, error en Word, Excel o Microsoft 365.",
        "tipo_ticket": TipoTicketSupport.SOFTWARE,
        "sub_tipo_ticket": "Microsoft Outlook",
        "prioridad_sugerida": PrioridadSupport.MEDIA,
        "prioridad_badge": "prio-media",
        "requiere_equipo": False,
    },
    {
        "id": "internet_red",
        "titulo": "Internet y Red",
        "icono": "bi-wifi",
        "descripcion": "Sin conexión a internet, falla de cable de red, problemas con VPN.",
        "tipo_ticket": TipoTicketSupport.HELPDESK,
        "sub_tipo_ticket": "Internet",
        "prioridad_sugerida": PrioridadSupport.MEDIA,
        "prioridad_badge": "prio-media",
        "requiere_equipo": False,
    },
    {
        "id": "sistemas_planta",
        "titulo": "Sistemas de planta (SAP / BPCS)",
        "icono": "bi-database-gear",
        "descripcion": "Error en órdenes, bloqueo en BPCS o SAP, fallas en sistemas de producción.",
        "tipo_ticket": TipoTicketSupport.BPCS,
        "sub_tipo_ticket": "BPCS PROBLEMAS CON ORDENES",
        "prioridad_sugerida": PrioridadSupport.ALTA,
        "prioridad_badge": "prio-alta",
        "requiere_equipo": False,
    },
    {
        "id": "telefonia",
        "titulo": "Teléfono o conmutador",
        "icono": "bi-telephone",
        "descripcion": "Sin tono, extensión telefónica, celular de empresa o conmutador.",
        "tipo_ticket": TipoTicketSupport.TELEFONIA,
        "sub_tipo_ticket": "Problemas con llamadas",
        "prioridad_sugerida": PrioridadSupport.MEDIA,
        "prioridad_badge": "prio-media",
        "requiere_equipo": False,
    },
    {
        "id": "mantenimiento",
        "titulo": "Mantenimiento preventivo",
        "icono": "bi-tools",
        "descripcion": "Limpieza física, mantenimiento programado o revisión general de equipo.",
        "tipo_ticket": TipoTicketSupport.MANTENIMIENTO,
        "sub_tipo_ticket": "Preventivo",
        "prioridad_sugerida": PrioridadSupport.BAJA,
        "prioridad_badge": "prio-baja",
        "requiere_equipo": True,
    },
    {
        "id": "otro",
        "titulo": "Otro problema o duda",
        "icono": "bi-question-circle",
        "descripcion": "Si tu situación no encaja en las opciones anteriores, descríbela en el siguiente paso.",
        "tipo_ticket": TipoTicketSupport.HELPDESK,
        "sub_tipo_ticket": "Otro",
        "prioridad_sugerida": PrioridadSupport.MEDIA,
        "prioridad_badge": "prio-media",
        "requiere_equipo": False,
    },
]

PROBLEMAS_POR_ID = {p["id"]: p for p in CATALOGO_PROBLEMAS}


def get_problema_by_id(problema_id):
    """Devuelve la definicion del problema o None si no existe."""
    if not problema_id:
        return None
    return PROBLEMAS_POR_ID.get(str(problema_id).strip().lower())
