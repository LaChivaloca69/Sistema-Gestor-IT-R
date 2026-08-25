# Sistema Gestor IT

Aplicación web Django para gestionar el área de TI de una fábrica: inventario de equipos, tickets de soporte, mantenimiento, órdenes de compra, personal y gobierno de roles.

Una sola app de negocio (`GestorApp`) dentro del proyecto Django (`GestorIT`). Los “módulos” de la documentación son dominios funcionales, no apps Django separadas.

**Última revisión:** agosto 2026 (código actual del repositorio).

---

## Qué cubre el sistema

| Módulo | Qué hace |
|--------|----------|
| **Inventario** | Gestion de Equipos unitarios: alta, asignación, devolución, ubicación, baja lógica, movimientos |
| **Soporte** | Tickets con SLA, seguimientos, bitácora operativa |
| **Mantenimiento** | Órdenes preventivo/correctivo/predictivo, cierres y próximo ciclo |
| **Compras** | Órdenes de compra (crear o subir), plantillas DOCX/XLSX/PDF, PDF generado |
| **Organización** | Áreas, puestos, personal ligado a `User` |
| **Ubicaciones** | Edificio → zona → ubicación |
| **Gobierno** | Roles (Groups), coberturas de tickets, solicitudes de equipo, matriz de permisos |
| **Auditoría** | Historial de actividad con retención (archivar → purgar) |

Los avisos (SLA, checks, mantenimientos, solicitudes) se ven en **Inicio**, la **campana** del topbar y los **dashboards**.

---

## Stack

| Pieza | Detalle |
|-------|---------|
| Python / Django | Django **6.0.7** |
| Base de datos | **PostgreSQL** (`psycopg2-binary`) |
| UI | `django-bootstrap5`, CSS/JS en `static/GestorApp/` |
| Jobs | `django-q2` (broker ORM en Postgres, sin Redis) |
| Documentos | `docxtpl`, `python-docx`, `openpyxl`, `pypdf`, `Pillow` |
| Auth | `django.contrib.auth.User` (sin `AUTH_USER_MODEL` propio) |

Dependencias: [requirements.txt](requirements.txt).

---

## Roles

Tres grupos de Django (un usuario tiene un solo rol de negocio):

| Grupo | Quién | Alcance típico |
|-------|-------|----------------|
| `Usuario` | Empleado final | Tickets propios, mis equipos, solicitudes, órdenes propias |
| `Tecnico IT` | Operación diaria | Inventario, tickets globales, mantenimiento, coberturas |
| `Administrador` | Gobierno | Personal, borrados, plantillas, retención, matriz |

El registro (`/signup/`) crea `User` + `Personal` con rol **Usuario**. El Administrador eleva roles desde Personal.

Detalle: [ROLES.md](documentacion/Docs1/ROLES.md).

---

## Instalación (desarrollo)

Requisitos: Python 3, PostgreSQL, Git.

```powershell
git clone https://github.com/LaChivaloca69/Sistema-Gestor-IT-R.git
cd Sistema-Gestor-IT-R

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

1. Crear en PostgreSQL la base `GestorIT` y un usuario con permiso sobre ella.
2. Ajustar `DATABASES` en `GestorIT/settings.py` (host, usuario, contraseña). Los valores del repo son de desarrollo, no de producción.
3. Migrar y arrancar:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Opcional (jobs de retención y recordatorios):

```powershell
python manage.py setup_background_jobs
python manage.py qcluster
```

El worker debe quedar como proceso aparte en el servidor. Sin él, las tareas pueden ejecutarse en el mismo request (fallback) o quedar en cola.

Tests de humo:

```powershell
python manage.py test GestorApp.tests
```
Comandos github 
``` powershell
# Ver estado de cambios
git status

# Iniciar git en tu proyecto
git init

# Actualizar tu copia local
git pull origin main

# Agregar todos los cambios locales
git add .

# Hacer commit de cambios
git commit -m "Descripción clara de los cambios"

# Subir cambios al repositorio
git push origin main

# subir archivos 
git branch -M main
git push -u origin main

# Muestra el historial de cambios
git log --oneline
```



---

## Estructura del repositorio

```
Sistema-Gestor-IT-R/
├── GestorIT/                 # Proyecto Django (settings, urls, wsgi/asgi)
├── GestorApp/                # App de negocio
│   ├── models.py
│   ├── views/                # Vistas por dominio
│   ├── forms/                # Formularios por dominio
│   ├── Templates/            # HTML por entidad
│   ├── gobierno_views.py
│   └── management/commands/
├── static/GestorApp/         # CSS / JS
├── media/                    # Uploads (equipos, tickets, OC, plantillas)
├── documentacion/Docs1/      # Documentación técnica
├── manage.py
└── requirements.txt
```

---

## Documentación técnica

| Documento | Contenido |
|-----------|-----------|
| [MODELS.md](documentacion/Docs1/MODELS.md) | Modelos Django, choices, relaciones y métodos |
| [DocModels.md](documentacion/Docs1/DocModels.md) | Diccionario de datos (tablas / campos) |
| [DocTemplates.md](documentacion/Docs1/DocTemplates.md) | Templates, layout y partials |
| [Reestructuracion_Views.md](documentacion/Docs1/Reestructuracion_Views.md) | Split de `views/` y `forms/` |
| [TICKETS.md](documentacion/Docs1/TICKETS.md) | Flujo, SLA y seguimientos |
| [MANTENIMIENTO.md](documentacion/Docs1/MANTENIMIENTO.md) | Órdenes, cierres y próximo ciclo |
| [INVENTARIO.md](documentacion/Docs1/INVENTARIO.md) | Equipos, OC, asignaciones, movimientos |
| [ROLES.md](documentacion/Docs1/ROLES.md) | Roles, decoradores, matriz de acceso |
| [MODULOS.md](documentacion/Docs1/MODULOS.md) | Arquitectura funcional y mapa de archivos |
| [CASOS_DE_USO.md](documentacion/Docs1/CASOS_DE_USO.md) | Qué puede hacer cada actor |
| [MEJORAS_CALIDAD_Y_GOBIERNO.md](documentacion/Docs1/MEJORAS_CALIDAD_Y_GOBIERNO.md) | Cache, jobs, auditoría, media, gobierno |

---

## Rutas de entrada

| Ruta | Uso |
|------|-----|
| `/` | Inicio (KPIs + calendario) |
| `/login/` `/logout/` `/signup/` | Auth |
| `/Ticketit/` | Tickets |
| `/Equipos/` `/Equipos/mis/` | Inventario / mis equipos |
| `/MantenimientoEquipos/` | Mantenimientos |
| `/OrdenesCompra/` | Órdenes de compra |
| `/SolicitudesEquipo/` | Solicitudes de equipo |
| `/Gobierno/permisos/` | Matriz (solo Admin) |
| `/admin/` | Django Admin (`is_staff`; modelos de negocio **no** están registrados) |

---

## Notas de operación

- Zona horaria: `America/Tijuana`.
- Uploads: imagen 5 MB, PDF 10 MB, plantilla 15 MB (`MEDIA_UPLOAD` en settings).
- Historial: activo 180 días → archivo 365 días → purga; eventos **críticos** no se archivan (`HISTORIAL_RETENCION`).
- No hay API REST pública; solo endpoints AJAX (subtipos de ticket, zonas, preview OC, etc.).
- `DEBUG = True` y `SECRET_KEY` del repo son de desarrollo. No usarlos en fábrica.
