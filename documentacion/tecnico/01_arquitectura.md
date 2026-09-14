# 1. Arquitectura

---

## 1.1 Tipo de sistema

Aplicacion web **monolitica** en Django. Todo el negocio vive en una sola app (`GestorApp`). El paquete `GestorIT` es el proyecto (configuracion, URLs raiz, WSGI).

No hay microservicios ni apps Django separadas por dominio. Los “modulos” de la documentacion son **dominios funcionales**.

---

## 1.2 Stack

| Pieza | Tecnologia |
|-------|------------|
| Lenguaje / framework | Python, Django 6.0.x |
| Base de datos | PostgreSQL (`psycopg2-binary`) |
| UI | Templates Django, django-bootstrap5, CSS/JS en `static/GestorApp/` |
| Auth | `django.contrib.auth.User` (sin `AUTH_USER_MODEL` propio) |
| Roles | Groups de Django (`Usuario`, `Tecnico IT`, `Administrador`) |
| Jobs | django-q2 con broker ORM sobre PostgreSQL |
| Documentos | docxtpl, python-docx, openpyxl, pypdf, Pillow |
| Dependencias | `requirements.txt` |

---

## 1.3 Capas logicas

| Capa | Ubicacion | Responsabilidad |
|------|-----------|-----------------|
| Entrada HTTP | `GestorIT/urls.py` | Rutas y decoradores de acceso |
| Presentacion | `GestorApp/Templates/`, `static/` | HTML, CSS, JS |
| Control | `GestorApp/views/`, `gobierno_views.py` | Orquestacion de pantallas |
| Formularios | `GestorApp/forms/` | Validacion de entrada |
| Dominio / datos | `GestorApp/models.py` | Persistencia y reglas de modelo |
| Servicios | `historial.py`, `cobertura.py`, `document_engine.py`, etc. | Logica reutilizable |
| Trabajos | `tasks.py`, `schedules.py`, `job_queue.py` | Procesos en segundo plano |

---

## 1.4 Flujo de una peticion

1. El navegador llama una URL definida en `GestorIT/urls.py`.
2. Un decorador (`login_required`, `operativo_required` o `admin_required`) valida sesion y rol.
3. La vista carga modelos, aplica filtros por rol y usa forms si hay POST.
4. Se registran eventos relevantes via `historial.registrar_*` cuando aplica.
5. Se renderiza un template o se responde con redirect / JSON / archivo.

---

## 1.5 Procesos en ejecucion

| Proceso | Comando / pieza | Funcion |
|---------|-----------------|---------|
| Aplicacion web | WSGI (`GestorIT.wsgi`) o `runserver` en desarrollo | Atiende HTTP |
| Worker de cola | `python manage.py qcluster` | Ejecuta jobs de django-q2 |
| Base de datos | PostgreSQL | Datos y cola ORM de Q |

Sin `qcluster`, la web funciona, pero retencion y recordatorios automaticos no corren segun lo previsto (salvo modo sync de respaldo).

---

## 1.6 Configuracion relevante (`GestorIT/settings.py`)

| Clave | Uso |
|-------|-----|
| `DATABASES` | Conexion PostgreSQL |
| `TIME_ZONE` | `America/Tijuana` |
| `SIGNUP_ENABLED` | Alta publica (por defecto `False`) |
| `CACHES` / `METRICS_CACHE_TTL` | Cache LocMem de KPIs y badges (~45 s) |
| `Q_CLUSTER` | Workers y broker ORM |
| `HISTORIAL_RETENCION` | Politica de archivo y purga |
| `MEDIA_*` / `MEDIA_UPLOAD` | Archivos subidos y limites |
| `BACKGROUND_JOBS_ENABLED` / `BACKGROUND_JOBS_SYNC` | Cola async vs sync |

Los valores de `DEBUG`, `SECRET_KEY` y credenciales del repositorio son de desarrollo; no deben usarse tal cual en un entorno expuesto.
