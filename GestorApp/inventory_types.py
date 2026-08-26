"""Metadatos de UI para tipos de inventario unitario (Fase 1)."""

from .models import TipoCategoriaInventario

# Tipos con listado unitario en Inventario (Consumibles = fase posterior).
INVENTARIO_UNITARIO_TIPOS = (
    TipoCategoriaInventario.EQUIPO,
    TipoCategoriaInventario.PERIFERICO,
    TipoCategoriaInventario.HERRAMIENTA,
)

_INVENTARIO_UI = {
    TipoCategoriaInventario.EQUIPO: {
        "tipo": TipoCategoriaInventario.EQUIPO,
        "singular": "equipo",
        "singular_title": "Equipo",
        "plural": "Equipos",
        "list_url": "equipo_list",
        "create_url": "equipo_create",
        "nuevo_label": "Nuevo equipo",
        "editar_label": "Editar equipo",
        "empty_title": "Sin equipos",
        "empty_description": "Registra el primer equipo o ajusta los filtros.",
        "icon": "bi-pc-display",
        "csv_filename": "inventario_equipos.csv",
        "permite_asignacion": True,
        "description": "Maquinas principales: laptops, PCs, impresoras, etc.",
    },
    TipoCategoriaInventario.PERIFERICO: {
        "tipo": TipoCategoriaInventario.PERIFERICO,
        "singular": "periferico",
        "singular_title": "Periferico",
        "plural": "Perifericos",
        "list_url": "periferico_list",
        "create_url": "periferico_create",
        "nuevo_label": "Nuevo periferico",
        "editar_label": "Editar periferico",
        "empty_title": "Sin perifericos",
        "empty_description": "Registra el primer periferico o ajusta los filtros.",
        "icon": "bi-keyboard",
        "csv_filename": "inventario_perifericos.csv",
        "permite_asignacion": False,
        "description": "Mouse, teclado, monitor, RAM, SSD y componentes vinculados a un equipo.",
    },
    TipoCategoriaInventario.HERRAMIENTA: {
        "tipo": TipoCategoriaInventario.HERRAMIENTA,
        "singular": "herramienta",
        "singular_title": "Herramienta",
        "plural": "Herramientas",
        "list_url": "herramienta_list",
        "create_url": "herramienta_create",
        "nuevo_label": "Nueva herramienta",
        "editar_label": "Editar herramienta",
        "empty_title": "Sin herramientas",
        "empty_description": "Registra la primera herramienta del taller IT.",
        "icon": "bi-tools",
        "csv_filename": "inventario_herramientas.csv",
        "permite_asignacion": False,
        "description": "Herramientas del personal IT para mantenimiento (solo inventario).",
    },
}


def get_inventario_ui(tipo):
    """Devuelve dict de UI para un tipo unitario; default Equipo."""
    return _INVENTARIO_UI.get(tipo) or _INVENTARIO_UI[TipoCategoriaInventario.EQUIPO]


def resolve_inventario_tipo(value):
    """Normaliza valor de URL/kwargs a TipoCategoriaInventario."""
    if not value:
        return TipoCategoriaInventario.EQUIPO
    allowed = {c.value for c in TipoCategoriaInventario}
    if value in allowed:
        return value
    return TipoCategoriaInventario.EQUIPO


def inventario_ui_for_equipo(equipo):
    return get_inventario_ui(getattr(equipo, "tipo_inventario", None))


def infer_tipo_categoria_from_nombre(nombre):
    """Heuristica para reclasificar categorias existentes."""
    text = (nombre or "").strip().lower()
    if not text:
        return TipoCategoriaInventario.EQUIPO

    periferico_keys = (
        "monitor",
        "pantalla",
        "teclado",
        "mouse",
        "raton",
        "cable",
        "patch",
        "ram",
        "memoria",
        "ssd",
        "hdd",
        "disco",
        "almacenamiento",
        "headset",
        "audifono",
        "auricular",
        "webcam",
        "camara web",
        "dock",
        "periferic",
        "accesorio",
        "gpu",
        "fuente",
        "adaptador",
    )
    herramienta_keys = (
        "herramienta",
        "tester",
        "crimp",
        "taladro",
        "destornill",
        "pinza",
        "multimetro",
        "maletin",
    )
    consumible_keys = (
        "consumible",
        "alcohol",
        "isopropil",
        "toalla",
        "toner",
        "tinta",
        "terminal rj",
        "limpia",
        "quimico",
    )
    equipo_keys = (
        "laptop",
        "notebook",
        "desktop",
        "pc",
        "computadora",
        "impresora",
        "multifuncional",
        "router",
        "switch",
        "accesspoint",
        "access point",
        "ap ",
        "ups",
        "gabinete",
        "servidor",
        "server",
        "tablet",
        "escaner",
        "scanner",
        "plotter",
        "telefono",
        "celular",
    )

    if any(k in text for k in consumible_keys):
        return TipoCategoriaInventario.CONSUMIBLE
    if any(k in text for k in herramienta_keys):
        return TipoCategoriaInventario.HERRAMIENTA
    if any(k in text for k in periferico_keys):
        return TipoCategoriaInventario.PERIFERICO
    if any(k in text for k in equipo_keys):
        return TipoCategoriaInventario.EQUIPO
    return TipoCategoriaInventario.EQUIPO
