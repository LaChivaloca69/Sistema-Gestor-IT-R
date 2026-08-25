# Reestructuración de views y forms

**Estado: hecho.** El monolito `GestorApp/views.py` ya no existe; el código vive en `GestorApp/views/` y `GestorApp/forms/`. Este documento explica el split para mantenimiento futuro.

**Última revisión:** agosto 2026.

---

Documento de la partición del monolito `GestorApp/views.py` (~6 090 líneas) en el paquete `GestorApp/views/`, y de la extracción posterior de formularios al paquete `GestorApp/forms/`.

---

## Resumen

| Fase | Antes | Después |
|------|-------|---------|
| **1. Views** | Un solo `views.py` (~6 090 líneas) | Paquete `views/` por dominio + `helpers.py` |
| **2. Forms** | Forms mezclados en `forms.py` y dentro de cada `views/*.py` | Paquete `forms/` por dominio; vistas solo orquestan request/response |

**Compatibilidad:**

- `from GestorApp import views` y `views.area_list` / `views.admin_required` siguen igual.
- `from GestorApp.forms import TicketITForm` (y el resto) sigue igual vía `forms/__init__.py`.
- `gobierno_forms.py` quedó como **shim** que reexporta desde `forms.gobierno` (no hay que tocar `gobierno_views.py`).

No se modificaron rutas en `GestorIT/urls.py`, templates, modelos ni migraciones.

---

## Motivación

### Views

`views.py` era el principal cuello de botella de mantenimiento: helpers, ModelForms, CRUD, dashboards y exports en un solo archivo. Partir por dominio reduce el tamaño de cada cambio y facilita PRs.

### Forms

Tras el split de views, los `*Form` seguían viviendo **dentro** de los módulos de vistas (más un `forms.py` suelto). Eso:

- mezclaba validación/UI de formulario con lógica HTTP;
- obligaba a abrir un archivo de CRUD para tocar un form;
- mantenía dos estilos (`forms.py` vs forms embebidos).

El paquete `forms/` unifica todo en un solo lugar, alineado con el patrón que ya tenía gobierno (`gobierno_forms`).

---

## Fase 1 — Paquete `views/`

### Estructura

```
GestorApp/
├── views.py                    # ELIMINADO
├── views/
│   ├── __init__.py             # Fachada + reexport de helpers con _
│   ├── helpers.py              # Permisos, fechas, movimientos
│   ├── organizacion.py
│   ├── ubicaciones.py
│   ├── equipo.py
│   ├── movimiento.py
│   ├── asignacion.py
│   ├── mantenimiento.py
│   ├── tickets.py
│   ├── compras.py
│   └── home.py
└── gobierno_views.py           # Ya separado; sin cambios de lógica
```

### Contenido por módulo (vistas)

| Archivo | Rol |
|---------|-----|
| `helpers.py` | Permisos tickets/OC, filtros de fecha, `_crear_movimiento`, reconciliación de estado |
| `organizacion.py` | Áreas, puestos, personal, proveedores, retención historial |
| `ubicaciones.py` | Edificios, zonas, ubicaciones, categorías |
| `equipo.py` | Inventario, dashboard, baja/asignar/ubicación, export CSV |
| `movimiento.py` | Movimientos + detalle de historial |
| `asignacion.py` | Asignaciones equipo ↔ personal |
| `mantenimiento.py` | Mantenimientos, agenda, alertas |
| `tickets.py` | Tickets, seguimientos, bitácora, answers |
| `compras.py` | Plantillas y órdenes de compra |
| `home.py` | Home, calendario KPI, signup |

### Fachada `views/__init__.py`

1. Reexporta vistas públicas (`from .organizacion import *`, etc.) para `urls.py`.
2. Reexporta **explícitamente** helpers con `_` (`_tickets_abiertos_qs`, etc.), porque `import *` no incluye nombres privados. Los usan `nav_badges`, `tasks` y `gobierno_views`.
3. Reexporta `admin_required` / `operativo_required` (urls usa `views.admin_required(...)`).

### Imports relativos en views

Al pasar de módulo a paquete:

| Antes | Después |
|-------|---------|
| `from .metrics_cache import ...` | `from ..metrics_cache import ...` |
| `from .media_security import ...` | `from ..media_security import ...` |
| `from .job_queue import ...` | `from ..job_queue import ...` |

---

## Fase 2 — Paquete `forms/`

### Estructura

```
GestorApp/
├── forms.py                    # ELIMINADO (reemplazado por el paquete)
├── forms/
│   ├── __init__.py             # Fachada: reexporta todos los forms públicos
│   ├── common.py               # get_subtipo_ticket_choices, helpers de personal
│   ├── auth.py                 # UserRegisterForm
│   ├── organizacion.py         # Area, Puesto, Personal, Proveedor
│   ├── ubicaciones.py          # Edificio, Zona, Ubicacion, CategoriaEquipo
│   ├── equipo.py               # EquipoForm + baja/asignar/ubicación
│   ├── movimiento.py           # MovimientoEquipoForm
│   ├── asignacion.py           # AsignacionEquipoForm
│   ├── mantenimiento.py        # Mantenimiento + Agenda
│   ├── tickets.py              # TicketIT, Seguimiento, Bitacora, Answer
│   ├── compras.py              # Plantilla, OC, FormSets, helpers IVA/PDF
│   └── gobierno.py             # Cobertura + Solicitud equipo
└── gobierno_forms.py           # Shim → forms.gobierno
```

### De dónde salió cada form

| Destino | Origen |
|---------|--------|
| `forms/common.py`, `auth.py`, `tickets.py` (TicketIT/Seguimiento), `ubicaciones.py` (UbicacionForm) | Antiguo `forms.py` |
| `forms/organizacion.py`, `equipo.py`, etc. | Clases `*Form` que vivían en `views/*.py` |
| `forms/gobierno.py` | Antiguo cuerpo de `gobierno_forms.py` |
| `forms/compras.py` | También `_validar_pdf_upload` y `_sync_iva_porcentaje` (helpers solo usados por forms de OC) |

### Qué quedó en las vistas

Las vistas **importan** el form del submódulo correspondiente y solo manejan GET/POST, mensajes e historial:

```python
# views/equipo.py
from ..forms.equipo import EquipoForm, EquipoBajaForm, ...

# views/tickets.py
from ..forms.tickets import TicketITForm, SeguimientoTicketForm, AnswerForm, BitacoraForm
from ..forms.common import get_subtipo_ticket_choices
```

### Fachada `forms/__init__.py`

Permite seguir usando:

```python
from GestorApp.forms import EquipoForm, TicketITForm, CoberturaTicketsForm
```

En código nuevo se prefiere el submódulo:

```python
from GestorApp.forms.equipo import EquipoForm
from GestorApp.forms.gobierno import CoberturaTicketsForm
```

### Circularidad views ↔ forms

`MovimientoEquipoForm` necesita `_get_equipo_asignacion_activa` de `views.helpers`. Para no circularizar el import del paquete, esa dependencia es **diferida** (dentro de `__init__` / `save` del form), no a nivel de módulo.

### Shim `gobierno_forms.py`

```python
from .forms.gobierno import (
    CoberturaTicketsForm,
    SolicitudEquipoForm,
    SolicitudEquipoRevisionForm,
)
```

`gobierno_views.py` puede seguir con `from .gobierno_forms import ...`.

### Nota de calidad en el traslado

Al mover `TicketITForm`, se corrigió un bug previo: `clean_imagen` mezclaba código muerto de parseo de fecha y faltaba `_parse_client_datetime`. Quedó separado: validación de imagen + método de parseo de fecha cliente.

---

## Cómo importar (guía)

```python
# URLs / legacy
from GestorApp import views
views.equipo_list

# Vistas nuevas
from GestorApp.views.equipo import equipo_list
from GestorApp.views.helpers import user_can_view_ticket

# Forms (fachada o submódulo)
from GestorApp.forms import EquipoForm
from GestorApp.forms.equipo import EquipoForm
from GestorApp.forms.tickets import TicketITForm

# Gobierno
from GestorApp import gobierno_views
from GestorApp.gobierno_forms import CoberturaTicketsForm  # shim
# o:
from GestorApp.forms.gobierno import CoberturaTicketsForm
```

---

## Scripts de apoyo

| Script | Uso |
|--------|-----|
| `scripts/split_views.py` | Corte inicial del monolito de vistas. **No reejecutar.** |
| `scripts/split_forms.py` | Extracción de forms hacia el paquete. **No reejecutar** sobre el árbol actual. |

---

## Verificación

- Import de `GestorApp.views`, `GestorApp.forms` y `gobierno_forms`.
- Resolución de URLs (~123 callbacks).
- `python manage.py test GestorApp.tests` — 9 tests de humo OK tras ambas fases.

---

## Próximos pasos sugeridos

1. **Mover rutas a `GestorApp/urls.py`** e incluirlo desde el proyecto (achicar `GestorIT/urls.py`).
2. **Tests por dominio** importando desde `views.equipo` / `forms.equipo`, etc.
3. Opcional: eliminar el shim `gobierno_forms.py` cuando todos los imports apunten a `forms.gobierno`.

`MODULOS.md` ya describe los paquetes `views/` y `forms/`.

---

## Criterio al añadir código nuevo

**Vistas**

- Poner la vista en el módulo de dominio correcto (`views/equipo.py`, etc.).
- No definir `*Form` dentro del archivo de vistas.

**Forms**

- Crear/editar el form en `forms/<dominio>.py`.
- Si hace falta un helper de vista, importarlo de forma diferida o mover el helper a un módulo neutro si se usa mucho.

**Helpers compartidos de permisos/estado**

- Siguen en `views/helpers.py` (o extraer a un `services/` / `policies/` más adelante si crece).
- Reexportar en `views/__init__.py` solo si algo externo hace `from GestorApp.views import _algo`.
