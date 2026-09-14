# Sistema Web para la gestion de inventario y Mesa de ayuda TI

Aplicación web Django para gestionar el área de TI: inventario de equipos, consumibles, tickets de soporte, mantenimiento, órdenes de compra, personal y gobierno de roles.

Una sola app de negocio (`GestorApp`) dentro del proyecto Django (`GestorIT`).

**Documentacion:** ver [documentacion/README.md](documentacion/README.md). El manual de negocio esta en [documentacion/negocio/](documentacion/negocio/).

**Última revisión:** septiembre 2026.

---

## Qué necesidades cubre el sistema

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
``` powershell
# Dependencias necesarias para Sistema Gestor IT.
# --- Nucleo Django ---
Django==6.0.7
asgiref==3.12.1
sqlparse==0.5.5
tzdata==2026.3
typing_extensions==4.16.0

# --- UI ---
django-bootstrap5==26.2

# --- Base de datos ---
psycopg2-binary==2.9.12

# --- Jobs en background ---
django-q2==1.10.0
django-picklefield==3.4.0

# --- Imagenes (ImageField) ---
Pillow==12.3.0

# --- Documentos ---
docxtpl==0.20.2
python-docx==1.2.0
openpyxl==3.1.5
et_xmlfile==2.0.0
lxml==6.1.1
Jinja2==3.1.6
MarkupSafe==3.0.3
pypdf==6.14.2

```
    
---

## Roles

Tres grupos o roles de Django (Solamente un rol por usuario):

| Grupo | Quién | Alcance típico |
|-------|-------|----------------|
| `Usuario` | Empleado final | Tickets propios, mis equipos, solicitudes |
| `Tecnico IT` | Operación diaria | Inventario, tickets globales, mantenimiento, coberturas |
| `Administrador` | Gobierno | Personal, borrados, plantillas, retención, matriz |

El registro publico (`/signup/`) esta desactivado por defecto. El Administrador da de alta Personal y asigna roles.

Detalle de negocio: [documentacion/negocio/04_roles_y_permisos.md](documentacion/negocio/04_roles_y_permisos.md).

---

## Instalación (desarrollo)
Hardware (Minimo Recomendado):

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 8 GB (SO + Postgres + app + qcluster) | 16 GB |
| Disco | 40–60 GB libres en SSD | 100 GB+ |


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
├── documentacion/
│   ├── README.md             # Indice de documentacion
│   ├── negocio/              # Manual de negocio (vigente)
│   └── tecnico/              # Manual tecnico (pendiente)
├── manage.py
└── requirements.txt
```

---

## Documentacion

| Documento | Contenido |
|-----------|-----------|
| [documentacion/README.md](documentacion/README.md) | Indice general |
| [documentacion/negocio/](documentacion/negocio/) | Manual de negocio y uso (17 capitulos) |
| [documentacion/tecnico/](documentacion/tecnico/) | Manual tecnico del codigo (nivel A, vigente) |

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
