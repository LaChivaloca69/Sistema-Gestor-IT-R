# Templates — Sistema Gestor IT

Diseño de templates. **Última revisión:** agosto 2026.

No hay CRUD genérico por `model_slug`. Cada dominio tiene sus plantillas (`list` / `form` / `detail` / `confirm_delete` según aplique).

---

## Ubicación

Las plantillas viven en la app:

```
GestorApp/Templates/
```

Django las encuentra con `APP_DIRS = True`. En `GestorIT/settings.py` también está `DIRS: [BASE_DIR / 'Templates']` (carpeta de proyecto; no es la fuente actual).

Estáticos:

```
static/GestorApp/css/app.css
static/GestorApp/css/theme-dark.css
static/GestorApp/js/app.js
```

UI: Bootstrap 5 (`django-bootstrap5`), Bootstrap Icons, fuente Montserrat.

---

## Layout

### `base.html`

Esqueleto de toda la app autenticada:

- Topbar: marca, atajos (Nuevo ticket / Nuevo equipo), campana de avisos, chip de usuario · rol, tema claro/oscuro
- Sidebar: secciones General, Soporte, Compras, Organización, Ubicaciones, Inventario, Operaciones, Admin (visibles según rol)
- Búsqueda del menú (Ctrl+K), favoritos y recientes (JS)
- Bloques: `title`, `content`, `extra_css`, `extra_js`
- Mensajes Django (`messages`)

Context processors:

| Processor | Variables |
|-----------|-----------|
| `roles` | `user_role`, `is_admin_role`, `is_tecnico_role`, `is_operativo_role` |
| `breadcrumbs` | `breadcrumb_items` |
| `nav_badges` | `nav_badges`, `nav_notifications`, `nav_notifications_total` |

### Auth y home

| Template | Vista | Uso |
|----------|-------|-----|
| `login.html` | `LoginView` | Inicio de sesión |
| `signup.html` | `signup` | Alta User + Personal (rol Usuario) |
| `logout.html` | (opcional) | Confirmación |
| `home.html` | `home` | KPIs, avisos, calendario |
| `index.html` | — | No forma parte del flujo actual |

---

## Partials (`Templates/partials/`)

| Archivo | Uso |
|---------|-----|
| `breadcrumbs.html` | Migas de pan |
| `page_header_open.html` / `page_header_close.html` | Título + acciones de página |
| `form_fieldset.html` | Agrupa campos de formulario |
| `empty_state.html` | Lista vacía |
| `info_hint.html` / `info_hint_open.html` / `info_hint_close.html` | Notas de ayuda |
| `row_actions.html` | Botones Ver / Editar / Eliminar en tablas |

Las listas y formularios reutilizan este patrón en lugar de un único `crud/*.html`.

---

## Plantillas por dominio

Patrón habitual: `list.html`, `form.html`, `confirm_delete.html`. Detalle o pantallas extra donde el flujo lo pide.

| Carpeta | Dominio | Extra |
|---------|---------|-------|
| `area/`, `puesto/` | Catálogos org | |
| `personal/` | Personal | `detail.html`, `admin_requests.html`, `admin_remove.html` |
| `proveedor/` | Proveedores | |
| `edificio/`, `zonaedificio/`, `ubicacion/` | Ubicaciones | |
| `categoriaequipo/` | Categorías | |
| `equipo/` | Inventario | `detail`, `dashboard`, `mis_equipos`, `baja`, `asignar`, `ubicacion` |
| `movimientoequipo/` | Movimientos + lista de auditoría | `registros.html`, `detail.html` (la lista es historial de actividad) |
| `asignacionequipo/` | Asignaciones | |
| `mantenimiento/` | Órdenes de mant. | `detail`, `dashboard` |
| `agendamantenimiento/` | Cierres (UI: Cierres) | |
| `ticketit/` | Tickets | `detail`, `dashboard` |
| `seguimientoticket/` | Checks | |
| `bitacora/` | Bitácora | `detail` |
| `answer/` | Respuestas | |
| `plantilladocumento/` | Plantillas OC | Solo Admin |
| `ordencompra/` | Órdenes | `choose`, `form_crear`, `form_subir`, `terminar` |
| `gobierno/` | Permisos, coberturas, solicitudes | `permisos_matriz`, `solicitud_*`, `cobertura_*`, `seguimiento_solicitud_*` |
| `historial/` | Auditoría / retención | `auditoria_detail.html`, `retencion.html` |

---

## Cómo se conectan con las vistas

Las vistas son **funciones** en `GestorApp/views/` (y `gobierno_views.py`). Cada una hace `render(request, '…/….html', context)`.

Rutas: `GestorIT/urls.py`. Ejemplo:

| URL | Template |
|-----|----------|
| `/` | `home.html` |
| `/Ticketit/` | `ticketit/list.html` |
| `/Ticketit/<id>/` | `ticketit/detail.html` |
| `/Equipos/` | `equipo/list.html` |
| `/Equipos/mis/` | `equipo/mis_equipos.html` |
| `/MantenimientoEquipos/<id>/` | `mantenimiento/detail.html` |
| `/OrdenesCompra/nueva/` | `ordencompra/choose.html` |
| `/Gobierno/permisos/` | `gobierno/permisos_matriz.html` |
| `/Auditoria/<id>/` | `historial/auditoria_detail.html` |

No hay `MODEL_REGISTRY` ni `ModelListView` genérico.

---

## Flujo de renderizado

1. URL en `GestorIT/urls.py` (con `login_required` / `operativo_required` / `admin_required`).
2. Vista de dominio prepara queryset, formularios y flags de permiso.
3. `render` del template de esa entidad.
4. El hijo extiende `base.html` y llena `content`.
5. Partials + Bootstrap pintan listados y forms.

---

## Convenciones de UI

- Formularios POST con CSRF; campos vía django-bootstrap5 (`field-required`, `field-error`).
- Enlaces con `{% url 'nombre_ruta' %}`.
- Menú condicionado por `is_operativo_role` / `is_admin_role`.
- Tema oscuro: clase `theme-dark` en `<html>` + `theme-dark.css`.
- Badges del sidebar cacheados ~45 s (`nav_badges`).

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `GestorApp/Templates/base.html` | Shell |
| `GestorApp/breadcrumbs.py` | Mapa url_name → migas |
| `GestorApp/context_processors.py` | Roles, breadcrumbs, badges |
| `GestorApp/nav_badges.py` | Conteos del menú y campana |
| `static/GestorApp/js/app.js` | Sidebar, tema, búsqueda, calendario |

---

## Documentación relacionada

`MODULOS.md` (mapa de archivos), `ROLES.md` (quién ve cada sección), `Reestructuracion_Views.md` (vistas/forms por dominio).
