"""Breadcrumbs automaticos a partir del nombre de URL."""

from django.urls import NoReverseMatch, reverse

# (seccion_label, seccion_url_name|None, pagina_label, list_url_name|None)
# list_url_name se usa como padre clicable en create/update/detail.
_MODULE = {
    "home": ("General", None, "Inicio", None),
    "mis_equipos": ("General", None, "Mis equipos", None),
    # Soporte
    "ticketit_list": ("Soporte", None, "Tickets", None),
    "ticketit_dashboard": ("Soporte", None, "Panel tickets", "ticketit_list"),
    "ticketit_create": ("Soporte", None, "Nuevo ticket", "ticketit_list"),
    "ticketit_detail": ("Soporte", None, "Detalle", "ticketit_list"),
    "ticketit_update": ("Soporte", None, "Editar", "ticketit_list"),
    "ticketit_delete": ("Soporte", None, "Eliminar", "ticketit_list"),
    "seguimientoticket_list": ("Soporte", None, "Checks", None),
    "seguimientoticket_create": ("Soporte", None, "Nuevo check", "seguimientoticket_list"),
    "seguimientoticket_update": ("Soporte", None, "Editar check", "seguimientoticket_list"),
    "seguimientoticket_delete": ("Soporte", None, "Eliminar check", "seguimientoticket_list"),
    "bitacora_list": ("Soporte", None, "Bitacora", None),
    "bitacora_create": ("Soporte", None, "Nueva bitacora", "bitacora_list"),
    "bitacora_detail": ("Soporte", None, "Detalle", "bitacora_list"),
    "bitacora_update": ("Soporte", None, "Editar bitacora", "bitacora_list"),
    "bitacora_delete": ("Soporte", None, "Eliminar bitacora", "bitacora_list"),
    "answer_list": ("Soporte", None, "Respuestas", None),
    "answer_create": ("Soporte", None, "Nueva respuesta", "answer_list"),
    "answer_update": ("Soporte", None, "Editar respuesta", "answer_list"),
    "answer_delete": ("Soporte", None, "Eliminar respuesta", "answer_list"),
    "cobertura_list": ("Soporte", None, "Cobertura de tickets", None),
    "cobertura_create": ("Soporte", None, "Nueva cobertura", "cobertura_list"),
    "cobertura_update": ("Soporte", None, "Editar cobertura", "cobertura_list"),
    "cobertura_delete": ("Soporte", None, "Eliminar cobertura", "cobertura_list"),
    # Compras
    "ordencompra_list": ("Compras", None, "Ordenes", None),
    "ordencompra_choose": ("Compras", None, "Nueva orden", "ordencompra_list"),
    "ordencompra_create": ("Compras", None, "Crear orden", "ordencompra_list"),
    "ordencompra_upload": ("Compras", None, "Subir orden", "ordencompra_list"),
    "ordencompra_update": ("Compras", None, "Editar orden", "ordencompra_list"),
    "ordencompra_terminar": ("Compras", None, "Terminar orden", "ordencompra_list"),
    "ordencompra_delete": ("Compras", None, "Eliminar orden", "ordencompra_list"),
    "plantilla_list": ("Compras", None, "Plantillas", None),
    "plantilla_create": ("Compras", None, "Nueva plantilla", "plantilla_list"),
    "plantilla_update": ("Compras", None, "Editar plantilla", "plantilla_list"),
    "plantilla_delete": ("Compras", None, "Eliminar plantilla", "plantilla_list"),
    # Inventario
    "equipo_list": ("Inventario", None, "Equipos", None),
    "periferico_list": ("Inventario", None, "Perifericos", None),
    "herramienta_list": ("Inventario", None, "Herramientas", None),
    "producto_consumible_list": ("Inventario", None, "Consumibles", None),
    "consumible_dashboard": ("Inventario", None, "Dashboard consumibles", "producto_consumible_list"),
    "movimiento_stock_list": ("Inventario", None, "Kardex consumibles", "producto_consumible_list"),
    "producto_consumible_create": ("Inventario", None, "Nuevo consumible", "producto_consumible_list"),
    "producto_consumible_detail": ("Inventario", None, "Detalle consumible", "producto_consumible_list"),
    "producto_consumible_update": ("Inventario", None, "Editar consumible", "producto_consumible_list"),
    "producto_consumible_delete": ("Inventario", None, "Eliminar consumible", "producto_consumible_list"),
    "producto_consumible_movimiento": ("Inventario", None, "Movimiento stock", "producto_consumible_list"),
    "producto_consumible_movimiento_libre": ("Inventario", None, "Movimiento stock", "producto_consumible_list"),
    "equipo_dashboard": ("Inventario", None, "Panel inventario", "equipo_list"),
    "equipo_create": ("Inventario", None, "Nuevo equipo", "equipo_list"),
    "periferico_create": ("Inventario", None, "Nuevo periferico", "periferico_list"),
    "herramienta_create": ("Inventario", None, "Nueva herramienta", "herramienta_list"),
    "equipo_detail": ("Inventario", None, "Detalle", "equipo_list"),
    "equipo_update": ("Inventario", None, "Editar", "equipo_list"),
    "equipo_delete": ("Inventario", None, "Eliminar", "equipo_list"),
    "equipo_dar_baja": ("Inventario", None, "Dar de baja", "equipo_list"),
    "equipo_reactivar": ("Inventario", None, "Reactivar", "equipo_list"),
    "equipo_asignar": ("Inventario", None, "Asignar", "equipo_list"),
    "equipo_devolver": ("Inventario", None, "Devolver", "equipo_list"),
    "equipo_cambiar_ubicacion": ("Inventario", None, "Cambiar espacio fisico", "equipo_list"),
    "equipo_vincular_periferico": ("Inventario", None, "Vincular periferico", "equipo_list"),
    "periferico_vincular_equipo": ("Inventario", None, "Vincular a equipo", "periferico_list"),
    "periferico_desvincular": ("Inventario", None, "Desvincular", "periferico_list"),
    "periferico_reemplazar": ("Inventario", None, "Reemplazar periferico", "periferico_list"),
    "categoriaequipo_list": ("Inventario", None, "Categorias", None),
    "categoriaequipo_create": ("Inventario", None, "Nueva categoria", "categoriaequipo_list"),
    "categoriaequipo_update": ("Inventario", None, "Editar categoria", "categoriaequipo_list"),
    "categoriaequipo_toggle_activo": ("Inventario", None, "Activar/desactivar", "categoriaequipo_list"),
    "categoriaequipo_delete": ("Inventario", None, "Eliminar categoria", "categoriaequipo_list"),
    "proveedor_list": ("Inventario", None, "Proveedores", None),
    "proveedor_create": ("Inventario", None, "Nuevo proveedor", "proveedor_list"),
    "proveedor_update": ("Inventario", None, "Editar proveedor", "proveedor_list"),
    "proveedor_delete": ("Inventario", None, "Eliminar proveedor", "proveedor_list"),
    "movimientoequipo_registros": ("Inventario", None, "Movimientos de equipo", None),
    "movimientoequipo_create": ("Inventario", None, "Nuevo movimiento", "movimientoequipo_registros"),
    "movimientoequipo_detail": ("Inventario", None, "Detalle movimiento", "movimientoequipo_registros"),
    "movimientoequipo_update": ("Inventario", None, "Editar movimiento", "movimientoequipo_registros"),
    "movimientoequipo_delete": ("Inventario", None, "Eliminar movimiento", "movimientoequipo_registros"),
    # Operaciones
    "movimientoequipo_list": ("Operaciones", None, "Historial de actividad", None),
    "historial_actividad_detail": ("Operaciones", None, "Detalle", "movimientoequipo_list"),
    "asignacionequipo_list": ("Operaciones", None, "Asignaciones", None),
    "asignacion_kit_migracion": ("Operaciones", None, "Migrar kit", "asignacionequipo_list"),
    "asignacionequipo_create": ("Operaciones", None, "Nueva asignacion", "asignacionequipo_list"),
    "asignacionequipo_update": ("Operaciones", None, "Editar asignacion", "asignacionequipo_list"),
    "asignacionequipo_delete": ("Operaciones", None, "Eliminar asignacion", "asignacionequipo_list"),
    "mantenimiento_list": ("Operaciones", None, "Mantenimientos", None),
    "mantenimiento_dashboard": ("Operaciones", None, "Panel mantenimientos", "mantenimiento_list"),
    "mantenimiento_create": ("Operaciones", None, "Nuevo mantenimiento", "mantenimiento_list"),
    "mantenimiento_detail": ("Operaciones", None, "Detalle", "mantenimiento_list"),
    "mantenimiento_update": ("Operaciones", None, "Editar", "mantenimiento_list"),
    "mantenimiento_delete": ("Operaciones", None, "Eliminar", "mantenimiento_list"),
    "agendamantenimiento_list": ("Operaciones", None, "Cierres de mantenimiento", None),
    "agendamantenimiento_create": ("Operaciones", None, "Nuevo cierre", "agendamantenimiento_list"),
    "agendamantenimiento_update": ("Operaciones", None, "Editar cierre", "agendamantenimiento_list"),
    "agendamantenimiento_delete": ("Operaciones", None, "Eliminar cierre", "agendamantenimiento_list"),
    # Organizacion
    "area_list": ("Organizacion", None, "Departamentos", None),
    "area_create": ("Organizacion", None, "Nuevo departamento", "area_list"),
    "area_update": ("Organizacion", None, "Editar departamento", "area_list"),
    "area_delete": ("Organizacion", None, "Eliminar departamento", "area_list"),
    "puesto_list": ("Organizacion", None, "Puestos", None),
    "puesto_create": ("Organizacion", None, "Nuevo puesto", "puesto_list"),
    "puesto_update": ("Organizacion", None, "Editar puesto", "puesto_list"),
    "puesto_delete": ("Organizacion", None, "Eliminar puesto", "puesto_list"),
    "personal_list": ("Organizacion", None, "Personal", None),
    "personal_detail": ("Organizacion", None, "Detalle", "personal_list"),
    "personal_create": ("Organizacion", None, "Nuevo personal", "personal_list"),
    "personal_update": ("Organizacion", None, "Editar personal", "personal_list"),
    "personal_delete": ("Organizacion", None, "Eliminar personal", "personal_list"),
    "personal_admin_requests": ("Organizacion", None, "Solicitudes admin", "personal_list"),
    "mapa_sedes": ("Espacios fisicos", None, "Mapa de sedes", None),
    "edificio_list": ("Espacios fisicos", None, "Mapa de sedes", "mapa_sedes"),
    "edificio_create": ("Espacios fisicos", None, "Nuevo edificio", "mapa_sedes"),
    "edificio_update": ("Espacios fisicos", None, "Editar edificio", "mapa_sedes"),
    "edificio_toggle_activo": ("Espacios fisicos", None, "Activar/desactivar", "mapa_sedes"),
    "edificio_delete": ("Espacios fisicos", None, "Eliminar edificio", "mapa_sedes"),
    "zonaedificio_list": ("Espacios fisicos", None, "Mapa de sedes", "mapa_sedes"),
    "zonaedificio_create": ("Espacios fisicos", None, "Nuevo sector", "mapa_sedes"),
    "zonaedificio_update": ("Espacios fisicos", None, "Editar sector", "mapa_sedes"),
    "zonaedificio_toggle_activo": ("Espacios fisicos", None, "Activar/desactivar", "mapa_sedes"),
    "zonaedificio_delete": ("Espacios fisicos", None, "Eliminar sector", "mapa_sedes"),
    "ubicacion_list": ("Espacios fisicos", None, "Mapa de sedes", "mapa_sedes"),
    "ubicacion_create": ("Espacios fisicos", None, "Nuevo espacio fisico", "mapa_sedes"),
    "ubicacion_update": ("Espacios fisicos", None, "Editar espacio fisico", "mapa_sedes"),
    "ubicacion_delete": ("Espacios fisicos", None, "Eliminar espacio fisico", "mapa_sedes"),
    # Admin
    "personal_admin_remove": ("Admin", None, "Quitar roles", None),
    "historial_retencion_admin": ("Admin", None, "Archivar historial", None),
    "permisos_matriz": ("Admin", None, "Matriz de permisos", None),
    # Solicitudes de equipo (menu General)
    "solicitud_equipo_list": ("General", None, "Solicitudes de equipo", None),
    "solicitud_equipo_create": ("General", None, "Nueva solicitud", "solicitud_equipo_list"),
    "solicitud_equipo_detail": ("General", None, "Detalle", "solicitud_equipo_list"),
    "solicitud_equipo_cancelar": ("General", None, "Cancelar", "solicitud_equipo_list"),
    "solicitud_equipo_revisar": ("General", None, "Revisar", "solicitud_equipo_list"),
    "seguimiento_solicitud_update": ("General", None, "Decision solicitud", "solicitud_equipo_list"),
    "seguimiento_solicitud_delete": ("General", None, "Decision solicitud", "solicitud_equipo_list"),
}

_SKIP = {"login", "logout", "signup", "home"}

# url_name -> (Model, attr_or_callable)
_DETAIL_RESOLVERS = {
    "bitacora_detail": ("GestorApp.models.Bitacora", "folio_bitacora"),
    "bitacora_update": ("GestorApp.models.Bitacora", "folio_bitacora"),
    "bitacora_delete": ("GestorApp.models.Bitacora", "folio_bitacora"),
    "answer_update": ("GestorApp.models.Answer", "__str__"),
    "answer_delete": ("GestorApp.models.Answer", "__str__"),
    "ticketit_update": ("GestorApp.models.TicketIT", "folio_ticket"),
    "ticketit_delete": ("GestorApp.models.TicketIT", "folio_ticket"),
    "equipo_detail": ("GestorApp.models.Equipo", "codigo_inventario"),
    "equipo_update": ("GestorApp.models.Equipo", "codigo_inventario"),
    "equipo_delete": ("GestorApp.models.Equipo", "codigo_inventario"),
    "equipo_dar_baja": ("GestorApp.models.Equipo", "codigo_inventario"),
    "equipo_reactivar": ("GestorApp.models.Equipo", "codigo_inventario"),
    "equipo_asignar": ("GestorApp.models.Equipo", "codigo_inventario"),
    "equipo_devolver": ("GestorApp.models.Equipo", "codigo_inventario"),
    "equipo_cambiar_ubicacion": ("GestorApp.models.Equipo", "codigo_inventario"),
    "mantenimiento_detail": ("GestorApp.models.Mantenimiento", "folio_mantenimiento"),
    "mantenimiento_update": ("GestorApp.models.Mantenimiento", "folio_mantenimiento"),
    "mantenimiento_delete": ("GestorApp.models.Mantenimiento", "folio_mantenimiento"),
    "personal_detail": ("GestorApp.models.Personal", "__str__"),
    "personal_update": ("GestorApp.models.Personal", "__str__"),
    "personal_delete": ("GestorApp.models.Personal", "__str__"),
    "movimientoequipo_detail": ("GestorApp.models.MovimientoEquipo", "__str__"),
    "ordencompra_update": ("GestorApp.models.OrdenCompra", "folio_orden"),
    "ordencompra_terminar": ("GestorApp.models.OrdenCompra", "folio_orden"),
    "ordencompra_delete": ("GestorApp.models.OrdenCompra", "folio_orden"),
    "solicitud_equipo_detail": ("GestorApp.models.SolicitudEquipo", "folio"),
    "solicitud_equipo_cancelar": ("GestorApp.models.SolicitudEquipo", "folio"),
    "solicitud_equipo_revisar": ("GestorApp.models.SolicitudEquipo", "folio"),
    "seguimiento_solicitud_update": ("GestorApp.models.SeguimientoSolicitudEquipo", "__str__"),
    "seguimiento_solicitud_delete": ("GestorApp.models.SeguimientoSolicitudEquipo", "__str__"),
    "cobertura_update": ("GestorApp.models.CoberturaTickets", "__str__"),
    "historial_actividad_detail": ("GestorApp.models.HistorialActividad", "titulo"),
}


def _safe_reverse(name):
    if not name:
        return None
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def _resolve_detail_label(url_name, kwargs):
    spec = _DETAIL_RESOLVERS.get(url_name)
    pk = kwargs.get("pk") if kwargs else None
    if not spec or pk is None:
        return None
    model_path, attr = spec
    try:
        module_name, class_name = model_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        model = getattr(module, class_name)
        obj = model.objects.filter(pk=pk).first()
        if not obj:
            return None
        if attr == "__str__":
            return str(obj)
        value = getattr(obj, attr, None)
        if callable(value):
            value = value()
        return str(value) if value else None
    except Exception:
        return None


def build_breadcrumbs(request):
    match = getattr(request, "resolver_match", None)
    if not match or not getattr(request, "user", None) or not request.user.is_authenticated:
        return []

    url_name = match.url_name
    if not url_name or url_name in _SKIP:
        return []

    meta = _MODULE.get(url_name)
    if not meta:
        return [
            {"label": "Inicio", "url": _safe_reverse("home")},
            {"label": url_name.replace("_", " ").title(), "url": None},
        ]

    section, _section_url, page_label, list_url = meta
    items = [{"label": "Inicio", "url": _safe_reverse("home")}]

    if section and section != "General":
        items.append({"label": section, "url": None})

    detail_label = _resolve_detail_label(url_name, match.kwargs)

    if list_url:
        list_meta = _MODULE.get(list_url)
        list_label = list_meta[2] if list_meta else "Lista"
        items.append({"label": list_label, "url": _safe_reverse(list_url)})
        items.append({"label": detail_label or page_label, "url": None})
    else:
        # Lista o pagina raiz del modulo
        if detail_label:
            items.append({"label": page_label, "url": None})
        else:
            items.append({"label": page_label, "url": None})

    # Evitar duplicados consecutivos
    cleaned = []
    for item in items:
        if cleaned and cleaned[-1]["label"] == item["label"] and cleaned[-1]["url"] == item["url"]:
            continue
        cleaned.append(item)
    return cleaned
