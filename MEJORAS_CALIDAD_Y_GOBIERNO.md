# Mejoras de calidad, rendimiento y gobierno

Documento de las funciones anadidas al Gestor IT en la oleada de endurecimiento tecnico (puntos 11–15) y gobierno de roles (16–18).

---

## Resumen

| # | Funcion | Para que sirve |
|---|---------|----------------|
| 11 | Cache de KPIs y badges | Menos consultas SQL en cada pagina; menu y home mas rapidos |
| 12 | Jobs en background (django-q2) | Retencion de historial y recordatorios sin colgar el navegador |
| 13 | Tests de humo | Verificar el camino critico antes de desplegar |
| 14 | Auditoria filtrable | Consultar quien hizo que, por modulo/usuario/fecha |
| 15 | Hardening de media | Subidas seguras (tamano, tipo real, nombres opacos) |
| 16 | Matriz de permisos | Documentar quien puede que (solo Admin) |
| 17 | Coberturas de tickets | Suplente atiende tickets del tecnico ausente |
| 18 | Solicitud de equipo | Usuario pide equipo → IT revisa / asigna |

Los archivos siguen en disco (`media/`); en la base de datos solo se guarda la ruta.

---

## 11. Cache de KPIs y badges

### Comportamiento
En casi cada pagina el sidebar y la campana calculan conteos (SLA, mantenimientos, solicitudes, etc.). Esos resultados se cachean **45 segundos** por usuario.

Tambien se cachean los KPIs numericos del **home**.

### Configuracion
En `GestorIT/settings.py`:

```python
METRICS_CACHE_TTL = 45  # segundos
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "gestor-it-metrics",
        ...
    }
}
```

### Codigo clave
- `GestorApp/metrics_cache.py` — get/set e invalidacion por version
- `GestorApp/nav_badges.py` — badges cacheados
- `GestorApp/views.py` → `home()` — KPIs cacheados

### Nota operativa
Los badges pueden ir hasta ~45 s “atrasados”. Es aceptable para avisos de operacion. En un servidor con varios workers, `LocMemCache` es por proceso; si hace falta cache compartida, se puede cambiar a Redis o `DatabaseCache`.

---

## 12. Jobs en background (django-q2)

### Comportamiento
Tareas pesadas o periodicas se encolan en PostgreSQL (sin Redis) y las ejecuta un **worker** aparte.

| Job | Frecuencia | Que hace |
|-----|------------|----------|
| Retencion de historial | Diario ~02:00 (y desde Admin → Archivar) | Archiva / purga segun `HISTORIAL_RETENCION` |
| Recordatorios operativos | Cada 15 min | Si cambia el panorama de SLA/mant., deja un evento en el historial |

### Arranque del worker (obligatorio en el servidor)

```bash
python manage.py qcluster
```

Dejarlo como servicio de Windows o proceso siempre activo. Sin worker, las tareas hacen **fallback sincrono** en el mismo request (o se quedan en cola si se encolaron bien).

### Comandos utiles

```bash
python manage.py setup_background_jobs
python manage.py setup_background_jobs --run-retencion
python manage.py setup_background_jobs --run-recordatorios
python manage.py limpiar_historial --dry-run
python manage.py limpiar_historial --async
```

### Configuracion
En `GestorIT/settings.py`:

- `BACKGROUND_JOBS_ENABLED` — activar cola
- `BACKGROUND_JOBS_SYNC = True` — forzar ejecucion en el request (util en desarrollo sin worker)
- `Q_CLUSTER` — workers, timeout, broker ORM
- `HISTORIAL_RETENCION` — dias activo / archivo / proteger criticos

### Codigo clave
- `GestorApp/tasks.py` — tareas
- `GestorApp/job_queue.py` — encolar con fallback
- `GestorApp/schedules.py` — schedules diarios / 15 min
- Panel Admin: **Archivar** (`historial_retencion_admin`)

---

## 13. Tests de humo

### Comportamiento
Pruebas automaticas del camino critico:

1. Login  
2. Home  
3. Lista de tickets  
4. Detalle de ticket  
5. Formulario / alta de equipo  

Tambien hay tests de login/signup y de auditoria / media.

### Como ejecutarlos

```bash
python manage.py test GestorApp.tests.SmokeFlowTests
python manage.py test GestorApp.tests
```

### Codigo clave
- `GestorApp/tests.py` — `SmokeFlowTests`, `AuthFlowTests`, `AuditoriaHistorialTests`, `MediaHardeningTests`

Usarlos antes de desplegar en el servidor de fabrica para detectar roturas obvias (URL, migracion, permisos).

---

## 14. Auditoria filtrable

### Comportamiento
La lista de historial (menu **Operaciones → Auditoria**) es la “caja negra” del sistema.

Filtros:

- Texto (titulo, descripcion, usuario, referencia)
- Modulo (ticket, equipo, solicitud, sistema, …)
- **Usuario** (o “Sistema”)
- Accion, nivel, origen (manual / automatico)
- Estado (activos / archivados / todos)
- Rango de fechas

Cada fila abre un **detalle** con metadata completa: `/Auditoria/<id>/`.

### Codigo clave
- Vista lista: `movimientoequipo_list` (plantilla `movimientoequipo/list.html`)
- Detalle: `historial_actividad_detail` → `historial/auditoria_detail.html`
- Modelo: `HistorialActividad`

### Ejemplo de uso
“¿Quien aprobo la solicitud SOL-000012?” → filtrar modulo *Solicitudes de equipo* + rango de fechas + buscar el folio.

---

## 15. Hardening de PDFs e imagenes

### Comportamiento
Las subidas (imagen de equipo/ticket, PDF de orden, plantillas) pasan por validacion central:

| Control | Detalle |
|---------|---------|
| Tamano maximo | Imagen 5 MB, PDF 10 MB, plantilla 15 MB |
| Extension | Whitelist por tipo |
| MIME | Debe coincidir (con tolerancia a `octet-stream` en plantillas) |
| Magic bytes | El contenido real debe ser PNG/JPEG/PDF/etc. (bloquea `.exe` renombrado) |
| Nombre en disco | `uuid.ext` bajo `media/equipos`, `media/support`, `media/ordenes_compra`, `media/plantillas_orden_compra` |

Los archivos **siguen en carpetas**; la BD solo guarda la ruta relativa.

### Configuracion
En `GestorIT/settings.py` → `MEDIA_UPLOAD` y limites globales `DATA_UPLOAD_MAX_*` alineados al tope de plantilla (15 MB).

### Codigo clave
- `GestorApp/media_security.py` — validadores + `SafeUploadTo`
- Forms: `TicketITForm`, `EquipoForm`, `OrdenCompraSubirForm`, `PlantillaDocumentoForm`
- Migracion: `0038_media_upload_safe_paths`

---

## 16. Matriz de permisos

### Comportamiento
Pagina solo **Administrador**: documenta quien puede que segun Usuario / Tecnico IT / Admin.

Ruta: `/Gobierno/permisos/`  
Menu: **Admin → Matriz permisos**

No cambia permisos; solo documenta el comportamiento actual (`permissions_matrix.py`).

---

## 17. Coberturas de tickets

### Comportamiento
Un tecnico **suplente** puede ver y atender tickets asignados a un colega **ausente** durante un periodo.

- Menu: **Soporte → Coberturas**
- En tickets, filtro *Asignados a mi* incluye los del ausente cubierto
- Aviso en la lista de tickets si hoy estas cubriendo a alguien

Modelo: `CoberturaTickets`  
Logica: `GestorApp/cobertura.py`

---

## 18. Solicitud de equipo

### Comportamiento
Flujo usuario → IT:

1. Usuario crea solicitud (General → **Solicitudes**)
2. IT revisa: en revision / aprobar / rechazar / completar
3. Al completar (o aprobar con equipo), se intenta **asignar** el equipo al personal destino

Badges y campana muestran solicitudes pendientes para rol operativo.

Modelo: `SolicitudEquipo`  
Vistas: `GestorApp/gobierno_views.py`  
Migracion: `0037_gobierno_cobertura_solicitud_equipo`

---

## Checklist de despliegue en fabrica

1. Aplicar migraciones: `python manage.py migrate`
2. Instalar dependencia: `django-q2` (ya en `requirements.txt`)
3. Arrancar app web (IIS / waitress / etc.)
4. Arrancar worker: `python manage.py qcluster`
5. Una vez: `python manage.py setup_background_jobs`
6. Verificar `media/` con permisos de escritura para la cuenta del servicio
7. Opcional: `python manage.py test GestorApp.tests` antes de liberar

---

## Archivos nuevos / relevantes

```
GestorApp/metrics_cache.py
GestorApp/tasks.py
GestorApp/job_queue.py
GestorApp/schedules.py
GestorApp/media_security.py
GestorApp/permissions_matrix.py
GestorApp/cobertura.py
GestorApp/gobierno_forms.py
GestorApp/gobierno_views.py
GestorApp/management/commands/setup_background_jobs.py
GestorApp/Templates/gobierno/…
GestorApp/Templates/historial/auditoria_detail.html
GestorApp/migrations/0037_gobierno_cobertura_solicitud_equipo.py
GestorApp/migrations/0038_media_upload_safe_paths.py
```
