# 2. Mapa de carpetas

---

## 2.1 Raiz del repositorio

| Ruta | Contenido |
|------|-----------|
| `manage.py` | CLI Django |
| `requirements.txt` | Dependencias |
| `GestorIT/` | Proyecto Django |
| `GestorApp/` | App de negocio |
| `static/` | Estaticos del proyecto (`STATICFILES_DIRS`) |
| `media/` | Uploads en tiempo de ejecucion |
| `Templates/` | Directorio extra de templates (settings) |
| `documentacion/` | Manuales de negocio y tecnico |
| `BD/` | Referencias SQL (no sustituye migraciones) |

---

## 2.2 Paquete `GestorIT`

| Archivo | Rol |
|---------|-----|
| `settings.py` | Configuracion |
| `urls.py` | Todas las rutas HTTP de la aplicacion |
| `wsgi.py` / `asgi.py` | Entrada de servidor |

---

## 2.3 Paquete `GestorApp` (nucleo)

| Ruta | Rol |
|------|-----|
| `models.py` | Todos los modelos de negocio |
| `admin.py` | Registro en Django Admin |
| `apps.py` | Config de app (senales / schedules al migrar) |
| `tests.py` | Suite de pruebas |
| `roles.py` | Roles y decoradores |
| `historial.py` | Auditoria y retencion |
| `cobertura.py` | Delegacion de tickets |
| `gobierno_views.py` | Vistas de gobierno (fuera de `views/`) |
| `permissions_matrix.py` | Matriz documentada de permisos |
| `nav_badges.py` | Conteos de menu y campana |
| `metrics_cache.py` | Cache de metricas por usuario |
| `schedules.py` / `tasks.py` / `job_queue.py` | Jobs |
| `inventory_types.py` | Metadatos UI inventario unitario |
| `inventory_import.py` | Logica de importacion Excel |
| `document_engine.py` | Generacion de PDF de OC |
| `ticket_catalog.py` | Catalogo guiado de problemas |
| `sla_guide.py` | Contenido de la guia SLA |
| `media_security.py` | Validacion de archivos subidos |
| `breadcrumbs.py` | Migas de pan |
| `context_processors.py` | Variables globales de template |

---

## 2.4 `GestorApp/views/`

| Archivo | Dominio |
|---------|---------|
| `__init__.py` | Reexporta vistas y helpers para `urls.py` |
| `helpers.py` | Permisos y sincronizacion compartida |
| `home.py` | Inicio, calendario, signup |
| `organizacion.py` | Area, Puesto, Personal, Proveedor, retencion UI |
| `ubicaciones.py` | Edificio, Zona, Ubicacion, Categoria, mapa |
| `equipo.py` | Inventario unitario |
| `inventory_import.py` | Asistente de importacion |
| `movimiento.py` | Movimientos de equipo + listado de historial |
| `asignacion.py` | Asignaciones y migracion de kit |
| `mantenimiento.py` | Mantenimiento y agenda/cierre |
| `tickets.py` | Tickets, checks, bitacora, comentarios |
| `compras.py` | OC y plantillas; mis equipos |
| `consumibles.py` | Stock por cantidad |

---

## 2.5 `GestorApp/forms/`

Paralelo a vistas: `auth`, `common`, `organizacion`, `ubicaciones`, `equipo`, `movimiento`, `asignacion`, `mantenimiento`, `tickets`, `compras`, `gobierno`, `consumibles`.

---

## 2.6 Templates y management

| Ruta | Rol |
|------|-----|
| `GestorApp/Templates/` | HTML por dominio (`ticketit/`, `equipo/`, `historial/`, etc.) |
| `GestorApp/management/commands/limpiar_historial.py` | Retencion manual / dry-run |
| `GestorApp/management/commands/setup_background_jobs.py` | Asegura schedules |
| `GestorApp/migrations/` | Esquema de base de datos |

---

## 2.7 Convencion de nombres URL

Las rutas se definen en `GestorIT/urls.py` con `name=` estable (`ticketit_list`, `equipo_detail`, `historial_actividad_list`, etc.). Los breadcrumbs y el historial guardan esos nombres para resolver enlaces.
