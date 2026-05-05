# Documentación de Models.py - Sistema Gestor IT

## Descripción General

Este documento explica la estructura completa del archivo `models.py` del proyecto **Sistema Gestor IT**, que implementa un sistema integral de gestión de inventario de activos de tecnología, mantenimiento y tickets de soporte.

El esquema está basado en el archivo SQL `it_inventoryDB.sql` y adaptado a Django ORM con las mejores prácticas.

---

## Tabla de Contenidos

1. [Estructura General](#estructura-general)
2. [Secciones de Modelos](#secciones-de-modelos)
3. [Relaciones y Dependencias](#relaciones-y-dependencias)
4. [Enums (Choices)](#enums-choices)
5. [Validaciones](#validaciones)
6. [Índices y Optimizaciones](#índices-y-optimizaciones)
7. [Ejemplos de Uso](#ejemplos-de-uso)

---

## Estructura General

El archivo `models.py` está organizado en **10 secciones principales**, cada una manejando un aspecto diferente del sistema:

```
1. USUARIOS                  → AppUser
2. UBICACIONES              → Site, Building, Zone
3. EMPLEADOS                → Employee
4. CATÁLOGO DE ACTIVOS      → AssetCategory, Manufacturer, AssetModel
5. PROVEEDORES              → Vendor
6. INVENTARIO               → Asset, AssetSpecification
7. ASIGNACIONES             → AssetAssignment
8. MANTENIMIENTO            → MaintenancePlan, MaintenanceWorkOrder
9. TICKETS IT               → TicketCategory, Ticket, TicketComment
10. HISTORIAL DE ACTIVOS    → AssetEvent
```

---

## Secciones de Modelos

### 1. USUARIOS - AppUser

```python
class AppUser(models.Model):
```

**Propósito:** Almacenar información de usuarios del sistema.

**Campos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `username` | CharField(150) | Nombre único de usuario |
| `email` | EmailField(254) | Correo electrónico único |
| `password_hash` | CharField(128) | Hash de contraseña |
| `is_active` | Boolean | Usuario activo en el sistema |
| `is_staff` | Boolean | Acceso al panel administrativo |
| `is_superuser` | Boolean | Permisos de administrador |
| `created_at` | DateTimeField | Fecha de creación automática |
| `updated_at` | DateTimeField | Fecha de última actualización |

**Características:**
- Campos `created_at` y `updated_at` se actualizan automáticamente
- Los tres campos booleanos definen permisos del usuario
- Es la base para autenticación del sistema

---

### 2. UBICACIONES - Site, Building, Zone

Estos modelos crean una **jerarquía de ubicaciones** de 3 niveles:

#### Site (Sitio)
```python
class Site(models.Model):
```
Nivel superior: Oficina central, sucursal, etc.

**Campos:**
- `code`: Código único (ej: "FCA01" para Fabrica 01)
- `name`: Nombre descriptivo
- `address`: Dirección física

#### Building (Edificio)
```python
class Building(models.Model):
```
Nivel intermedio: Edificios dentro de un sitio.

**Campos:**
- `site`: ForeignKey a Site
- `code`: Código único por sitio (ej: "EDIF_A", "EDIF_B")
- `name`: Nombre del edificio
- **Unique:** Combinación de `(site, code)` es única

#### Zone (Zona)
```python
class Zone(models.Model):
```
Nivel detallado: Áreas/departamentos dentro de edificios.

**Campos:**
- `building`: ForeignKey a Building
- `code`: Código único por edificio (ej: "PISO_3", "DEPTO_IT")
- `name`: Nombre descriptivo
- `floor`: Número de piso
- `description`: Descripción adicional
- **Unique:** Combinación de `(building, code)` es única

**Ejemplo de Jerarquía:**
```
Site: "FAB01" (Fábrica 01)
  └─ Building: "EDIF_A" (Edificio A)
      └─ Zone: "PISO_3" (Piso 3)
```

---

### 3. EMPLEADOS - Employee

```python
class Employee(models.Model):
```

**Propósito:** Registrar información detallada de empleados.

**Campos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user` | OneToOneField | Referencia única a AppUser |
| `employee_code` | CharField(50) | Código de empleado (cédula, etc.) |
| `first_name` | CharField(120) | Nombre |
| `last_name` | CharField(120) | Apellido |
| `phone` | CharField(50) | Teléfono |
| `department` | CharField(120) | Departamento |
| `job_title` | CharField(120) | Cargo/puesto |
| `base_site` | FK a Site | Sitio base |
| `base_building` | FK a Building | Edificio base |
| `base_zone` | FK a Zone | Zona base |
| `is_active` | Boolean | Empleado activo |

**Validaciones (method `clean()`):**
- Si `base_zone` está set → `base_building` debe estar set
- Si `base_building` está set → `base_site` debe estar set

**Relaciones:**
- 1 AppUser → 1 Employee (OneToOne)
- Tiene ubicación jerárquica: Site → Building → Zone

---

### 4. CATÁLOGO DE ACTIVOS

Estos modelos definen el **catálogo reutilizable** de tipos de activos.

#### AssetCategory (Categoría)
```python
class AssetCategory(models.Model):
```

**Campos:**
- `name`: Nombre único (ej: "Computadora", "Impresora")
- `assignable`: ¿Se puede asignar a empleados? (default=True)
- `requires_serial`: ¿Requiere número de serie?

#### Manufacturer (Fabricante)
```python
class Manufacturer(models.Model):
```

**Campos:**
- `name`: Nombre único (ej: "Dell", "HP", "Lenovo")

#### AssetModel (Modelo)
```python
class AssetModel(models.Model):
```

**Campos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `category` | FK | Categoría a la que pertenece |
| `manufacturer` | FK | Fabricante |
| `model_name` | CharField(120) | Nombre del modelo (ej: "OptiPlex 7090") |
| `default_maintenance_interval_days` | Integer | Intervalo estándar de mantenimiento |
| `notes` | TextField | Notas adicionales |

- **Unique:** Combinación de `(category, manufacturer, model_name)` es única

**Ejemplo:**
```
AssetCategory: "Computadora"
  └─ AssetModel:
      ├─ Manufacturer: "Dell"
      ├─ model_name: "OptiPlex 7090"
      └─ default_maintenance_interval_days: 90
```

---

### 5. PROVEEDORES - Vendor

```python
class Vendor(models.Model):
```

**Propósito:** Gestionar información de proveedores para reparaciones, mantenimiento y equipos rentados.

**Campos:**
- `name`: Nombre único del proveedor
- `contact_name`: Nombre del contacto
- `email`: Correo electrónico
- `phone`: Teléfono
- `notes`: Notas adicionales

---

### 6. INVENTARIO - Asset

```python
class Asset(models.Model):
```

**Propósito:** Representar CADA UNIDAD FÍSICA de activo en el inventario.

**Estados de Activo (ASSET_STATUS_CHOICES):**
| Estado | Descripción |
|--------|-------------|
| `IN_STOCK` | En almacén, sin asignar |
| `ASSIGNED` | Asignado a un empleado |
| `IN_REPAIR` | En reparación |
| `RETIRED` | Retirado del servicio |
| `LOST` | Perdido |

**Tipos de Propiedad (OWNERSHIP_CHOICES):**
| Tipo | Descripción |
|------|-------------|
| `OWNED` | Propiedad de la empresa |
| `RENTED` | Equipo rentado |
| `VENDOR_OWNED` | Propiedad del proveedor |

**Campos Principales:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `category` | FK | Categoría del activo |
| `model` | FK | Modelo específico |
| `asset_tag` | CharField(60) | Etiqueta física única |
| `serial_number` | CharField(120) | Número de serie único |
| `status` | CharField | Estado actual |
| `ownership` | CharField | Tipo de propiedad |
| `vendor` | FK | Proveedor (si no es OWNED) |
| `purchase_date` | Date | Fecha de compra |
| `warranty_end` | Date | Fin de garantía |
| `current_site` | FK | Ubicación: Sitio |
| `current_building` | FK | Ubicación: Edificio |
| `current_zone` | FK | Ubicación: Zona |
| `notes` | TextField | Notas adicionales |

**Validaciones (method `clean()`):**
- Jerarquía de ubicación: Zone → Building → Site
- Si `ownership != 'OWNED'` → debe haber `vendor`
- Si categoría es `assignable=True` → `asset_tag` es obligatorio

**Índices:**
```python
models.Index(fields=['status'])      # Para filtrar por estado
models.Index(fields=['model'])       # Para búsquedas por modelo
```

---

### 6.1 ESPECIFICACIONES DE ACTIVOS - AssetSpecification

```python
class AssetSpecification(models.Model):
```

**Propósito:** Almacenar especificaciones flexibles por activo (RAM, CPU, IP, etc.).

**Campos:**
- `asset`: FK a Asset (CASCADE al eliminar activo)
- `spec_key`: Clave (ej: "RAM", "CPU", "IP_ADDRESS")
- `spec_value`: Valor (ej: "16GB", "Intel i7", "192.168.1.50")
- **Unique:** `(asset, spec_key)` es única

**Ejemplo:**
```
Asset: "COMP001" (Computadora Dell OptiPlex)
  ├─ AssetSpecification: ("RAM", "16GB")
  ├─ AssetSpecification: ("CPU", "Intel i7-10700")
  ├─ AssetSpecification: ("SSD", "512GB")
  └─ AssetSpecification: ("IP_ADDRESS", "192.168.1.50")
```

---

### 7. ASIGNACIONES - AssetAssignment

```python
class AssetAssignment(models.Model):
```

**Propósito:** Registrar la asignación de activos a empleados, incluyendo fechas y condiciones.

**Campos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `asset` | FK | Activo asignado |
| `employee` | FK | Empleado receptor |
| `assigned_at` | DateTime | Fecha de asignación (auto) |
| `returned_at` | DateTime | Fecha de devolución |
| `assigned_by_user` | FK a AppUser | Quién hizo la asignación |
| `condition_out` | TextField | Condición al salir (notas) |
| `condition_in` | TextField | Condición al retornar (notas) |

**Índices:**
```python
models.Index(fields=['employee'])  # Para ver asignaciones de un empleado
```

**Estados:**
- **Activa:** `returned_at IS NULL` (1 única por activo)
- **Completada:** `returned_at IS NOT NULL`

---

### 8. MANTENIMIENTO

#### MaintenancePlan (Plan de Mantenimiento)

```python
class MaintenancePlan(models.Model):
```

**Propósito:** Definir plantillas de planes de mantenimiento reutilizables.

**Campos:**
- `name`: Nombre del plan
- `interval_days`: Intervalo en días entre mantenimientos
- `applies_to_category`: Aplica a una categoría completa (FK opcional)
- `applies_to_model`: Aplica a un modelo específico (FK opcional)
- `active`: Plan activo o inactivo

**Validación:**
- Al menos `applies_to_category` O `applies_to_model` debe estar definido

**Ejemplo:**
```
MaintenancePlan: "Mantenimiento Preventivo PCs"
  ├─ interval_days: 90
  ├─ applies_to_category: "Computadora"
  └─ active: True
```

#### MaintenanceWorkOrder (Orden de Trabajo)

```python
class MaintenanceWorkOrder(models.Model):
```

**Propósito:** Registrar cada actividad de mantenimiento realizada.

**Tipos de Mantenimiento:**
- `PREVENTIVE`: Mantenimiento programado
- `CORRECTIVE`: Reparación por falla

**Estados:**
| Estado | Descripción |
|--------|-------------|
| `OPEN` | Abierta, pendiente de inicio |
| `IN_PROGRESS` | En proceso |
| `DONE` | Completada |
| `CANCELED` | Cancelada |

**Campos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `asset` | FK | Activo a mantener |
| `plan` | FK | Plan asociado (opcional) |
| `vendor` | FK | Proveedor que hace el trabajo |
| `m_type` | CharField | Tipo: PREVENTIVE o CORRECTIVE |
| `status` | CharField | Estado actual |
| `opened_at` | DateTime | Fecha apertura (auto) |
| `completed_at` | DateTime | Fecha conclusión |
| `next_due_at` | DateTime | Próximo vencimiento |
| `findings` | TextField | Hallazgos/diagnóstico |
| `actions_taken` | TextField | Acciones realizadas |
| `cost` | Decimal(12,2) | Costo de la orden |

**Índices:**
```python
models.Index(fields=['asset', 'status'])  # Filtrar por activo y estado
```

---

### 9. TICKETS IT

#### TicketCategory (Categoría de Ticket)

```python
class TicketCategory(models.Model):
```

**Campos:**
- `name`: Nombre único (ej: "Hardware Issue", "Software Support")

#### Ticket (Ticket de Soporte)

```python
class Ticket(models.Model):
```

**Prioridades:**
| Nivel | Descripción |
|-------|-------------|
| `LOW` | Baja |
| `MEDIUM` | Media (default) |
| `HIGH` | Alta |
| `URGENT` | Urgente |

**Estados:**
| Estado | Descripción |
|--------|-------------|
| `OPEN` | Abierto, sin asignar |
| `IN_PROGRESS` | En proceso |
| `WAITING_VENDOR` | Esperando respuesta de proveedor |
| `RESOLVED` | Resuelto |
| `CLOSED` | Cerrado |

**Campos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `requester_employee` | FK | Empleado que reporta |
| `assigned_to_employee` | FK | Técnico asignado |
| `site` | FK | Ubicación: Sitio |
| `building` | FK | Ubicación: Edificio |
| `zone` | FK | Ubicación: Zona |
| `asset` | FK | Activo relacionado |
| `category` | FK | Categoría del ticket |
| `priority` | CharField | Prioridad |
| `status` | CharField | Estado |
| `subject` | CharField(200) | Asunto/título |
| `description` | TextField | Descripción del problema |
| `created_at` | DateTime | Fecha creación |
| `updated_at` | DateTime | Última actualización |
| `resolved_at` | DateTime | Fecha de resolución |

**Índices:**
```python
models.Index(fields=['status', 'priority'])      # Filtros comunes
models.Index(fields=['requester_employee'])      # Tickets de un empleado
models.Index(fields=['asset'])                   # Tickets de un activo
```

#### TicketComment (Comentario en Ticket)

```python
class TicketComment(models.Model):
```

**Campos:**
- `ticket`: FK a Ticket (CASCADE al eliminar ticket)
- `author_employee`: FK a Employee
- `body`: TextField con el comentario
- `created_at`: DateTime automático

**Ejemplo:**
```
Ticket: TKT#1001 - "Monitor no enciende"
  ├─ TicketComment: "He revisado la fuente..." (Author: Juan)
  └─ TicketComment: "Se reemplazó cable HDMI..." (Author: María)
```

---

### 10. HISTORIAL DE ACTIVOS - AssetEvent

```python
class AssetEvent(models.Model):
```

**Propósito:** Registrar TODAS las acciones/movimientos de un activo para auditoría completa.

**Tipos de Evento:**
| Tipo | Descripción |
|------|-------------|
| `ASSIGNED` | Activo asignado a empleado |
| `RETURNED` | Activo devuelto |
| `MOVED_LOCATION` | Activo movido a nueva ubicación |
| `MAINTENANCE_CREATED` | Se creó orden de mantenimiento |
| `MAINTENANCE_DONE` | Se completó mantenimiento |
| `STATUS_CHANGED` | Cambio de estado |
| `OTHER` | Otro evento |

**Campos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `asset` | FK | Activo afectado |
| `event_type` | CharField | Tipo de evento |
| `from_employee` | FK | Empleado origen (ej: devuelve) |
| `to_employee` | FK | Empleado destino (ej: recibe) |
| `from_zone` | FK | Ubicación origen |
| `to_zone` | FK | Ubicación destino |
| `related_assignment` | FK | Asignación relacionada |
| `related_mwo` | FK | Orden de mantenimiento relacionada |
| `occurred_at` | DateTime | Fecha del evento |
| `notes` | TextField | Notas adicionales |
| `created_by_user` | FK | Usuario que registró el evento |

**Índices:**
```python
models.Index(fields=['asset', 'occurred_at'])  # Timeline de activo
```

**Ejemplo de Auditoría:**
```
Asset: "COMP001"
  ├─ Event: ASSIGNED (2026-01-15)
  │  └─ from_employee: None → to_employee: Juan García
  ├─ Event: MOVED_LOCATION (2026-02-01)
  │  └─ from_zone: Piso 3 → to_zone: Piso 2
  ├─ Event: MAINTENANCE_CREATED (2026-03-01)
  │  └─ related_mwo: MWO#105
  └─ Event: RETURNED (2026-04-10)
     └─ from_employee: Juan García → to_employee: None
```

---

## Relaciones y Dependencias

### Diagrama de Relaciones Principales

```
AppUser (1)
  ├─ Employee (1)
  ├─ AssetAssignment (many) ← assigned_by_user
  └─ AssetEvent (many) ← created_by_user

Site (1)
  ├─ Building (many)
  ├─ Employee (many) ← base_site
  ├─ Asset (many) ← current_site
  └─ Ticket (many)

Building (1)
  ├─ Zone (many)
  ├─ Employee (many) ← base_building
  ├─ Asset (many) ← current_building
  └─ Ticket (many)

Zone (1)
  ├─ Employee (many) ← base_zone
  ├─ Asset (many) ← current_zone
  ├─ Ticket (many)
  ├─ AssetEvent (many) ← from_zone/to_zone
  └─ TicketComment (implicit)

AssetCategory (1)
  ├─ AssetModel (many)
  ├─ Asset (many)
  └─ MaintenancePlan (many) ← applies_to_category

Manufacturer (1)
  └─ AssetModel (many)

AssetModel (1)
  ├─ Asset (many)
  └─ MaintenancePlan (many) ← applies_to_model

Vendor (1)
  ├─ Asset (many)
  └─ MaintenanceWorkOrder (many)

Asset (1)
  ├─ AssetSpecification (many) [CASCADE]
  ├─ AssetAssignment (many)
  ├─ MaintenanceWorkOrder (many)
  ├─ Ticket (many)
  └─ AssetEvent (many)

Employee (1)
  ├─ AssetAssignment (many)
  ├─ TicketComment (many)
  ├─ Ticket (many) ← requester_employee
  ├─ Ticket (many) ← assigned_to_employee
  └─ AssetEvent (many) ← from/to_employee

TicketCategory (1)
  └─ Ticket (many)

Ticket (1)
  └─ TicketComment (many) [CASCADE]

MaintenancePlan (1)
  └─ MaintenanceWorkOrder (many)

MaintenanceWorkOrder (1)
  └─ AssetEvent (many) ← related_mwo [SET_NULL]

AssetAssignment (1)
  └─ AssetEvent (many) ← related_assignment [SET_NULL]
```

---

## Enums (Choices)

Django utiliza tuplas de `choices` en lugar de tipos ENUM declarados en SQL:

### Asset Status
```python
('IN_STOCK', 'In Stock')
('ASSIGNED', 'Assigned')
('IN_REPAIR', 'In Repair')
('RETIRED', 'Retired')
('LOST', 'Lost')
```

### Ownership Type
```python
('OWNED', 'Owned')
('RENTED', 'Rented')
('VENDOR_OWNED', 'Vendor Owned')
```

### Maintenance Status
```python
('OPEN', 'Open')
('IN_PROGRESS', 'In Progress')
('DONE', 'Done')
('CANCELED', 'Canceled')
```

### Maintenance Type
```python
('PREVENTIVE', 'Preventive')
('CORRECTIVE', 'Corrective')
```

### Ticket Priority
```python
('LOW', 'Low')
('MEDIUM', 'Medium')
('HIGH', 'High')
('URGENT', 'Urgent')
```

### Ticket Status
```python
('OPEN', 'Open')
('IN_PROGRESS', 'In Progress')
('WAITING_VENDOR', 'Waiting Vendor')
('RESOLVED', 'Resolved')
('CLOSED', 'Closed')
```

### Asset Event Type
```python
('ASSIGNED', 'Assigned')
('RETURNED', 'Returned')
('MOVED_LOCATION', 'Moved Location')
('MAINTENANCE_CREATED', 'Maintenance Created')
('MAINTENANCE_DONE', 'Maintenance Done')
('STATUS_CHANGED', 'Status Changed')
('OTHER', 'Other')
```

---

## Validaciones

Cada modelo incluye validaciones en el método `clean()` para garantizar integridad de datos:

### Employee - Validación Jerárquica
```python
def clean(self):
    if self.base_zone and not self.base_building:
        raise ValidationError("base_building must be set if base_zone is set.")
    if self.base_building and not self.base_site:
        raise ValidationError("base_site must be set if base_building is set.")
```

### Asset - Validaciones Múltiples
```python
def clean(self):
    # Jerarquía de ubicación
    if self.current_building and not self.current_site:
        raise ValidationError("current_site must be set if current_building is set.")
    if self.current_zone and not self.current_building:
        raise ValidationError("current_building must be set if current_zone is set.")
    
    # Vendor requerido si no es propiedad propia
    if self.ownership != 'OWNED' and not self.vendor:
        raise ValidationError(f"Vendor is required for ownership type '{self.ownership}'.")
    
    # Asset tag obligatorio para categorías asignables
    if self.category.assignable and not self.asset_tag:
        raise ValidationError(f"asset_tag is required for assignable category '{self.category.name}'.")
```

### MaintenancePlan - Validación de Alcance
```python
def clean(self):
    if not self.applies_to_category and not self.applies_to_model:
        raise ValidationError("At least applies_to_category or applies_to_model must be defined.")
```

---

## Índices y Optimizaciones

Los índices mejoran la velocidad de consultas frecuentes:

### Asset
```python
models.Index(fields=['status'])      # Filtrar por estado
models.Index(fields=['model'])       # Búsquedas por modelo
```

### AssetAssignment
```python
models.Index(fields=['employee'])    # Ver todos los activos de un empleado
```

### MaintenanceWorkOrder
```python
models.Index(fields=['asset', 'status'])  # Filtrar por activo y estado
```

### Ticket
```python
models.Index(fields=['status', 'priority'])        # Dashboard de tickets
models.Index(fields=['requester_employee'])        # Tickets de un usuario
models.Index(fields=['asset'])                     # Tickets de un activo
```

### AssetEvent
```python
models.Index(fields=['asset', 'occurred_at'])  # Timeline de auditoría
```

---

## Ejemplos de Uso

### Crear un Activo Completo

```python
# 1. Crear categoría y fabricante
categoria = AssetCategory.objects.create(
    name="Computadora",
    assignable=True,
    requires_serial=True
)

fabricante = Manufacturer.objects.create(name="Dell")

# 2. Crear modelo
modelo = AssetModel.objects.create(
    category=categoria,
    manufacturer=fabricante,
    model_name="OptiPlex 7090",
    default_maintenance_interval_days=90
)

# 3. Crear ubicación
sitio = Site.objects.create(code="FAB01", name="Fábrica 01", address="Calle Principal 123")
edificio = Building.objects.create(site=sitio, code="EDIF_A", name="Edificio A")
zona = Zone.objects.create(building=edificio, code="PISO_3", name="Piso 3")

# 4. Crear activo
activo = Asset.objects.create(
    category=categoria,
    model=modelo,
    asset_tag="COMP001",
    serial_number="SN123456789",
    status="IN_STOCK",
    ownership="OWNED",
    purchase_date="2025-01-15",
    warranty_end="2027-01-15",
    current_site=sitio,
    current_building=edificio,
    current_zone=zona,
    notes="Computadora de oficina"
)

# 5. Agregar especificaciones
AssetSpecification.objects.create(asset=activo, spec_key="RAM", spec_value="16GB")
AssetSpecification.objects.create(asset=activo, spec_key="CPU", spec_value="Intel i7-10700")
AssetSpecification.objects.create(asset=activo, spec_key="SSD", spec_value="512GB")

activo.clean()  # Validar
activo.save()
```

### Asignar Activo a Empleado

```python
# Crear empleado
usuario = AppUser.objects.create_user(
    username="jgarcia",
    email="jgarcia@company.com"
)

empleado = Employee.objects.create(
    user=usuario,
    first_name="Juan",
    last_name="García",
    department="IT",
    base_site=sitio,
    base_building=edificio,
    base_zone=zona
)

# Asignar activo
asignacion = AssetAssignment.objects.create(
    asset=activo,
    employee=empleado,
    assigned_by_user=usuario,
    condition_out="Buena condición"
)

# Actualizar estado del activo
activo.status = "ASSIGNED"
activo.save()

# Registrar evento
AssetEvent.objects.create(
    asset=activo,
    event_type="ASSIGNED",
    to_employee=empleado,
    created_by_user=usuario,
    notes="Asignación inicial"
)
```

### Crear Ticket

```python
ticket = Ticket.objects.create(
    requester_employee=empleado,
    asset=activo,
    category=TicketCategory.objects.first(),
    priority="HIGH",
    status="OPEN",
    subject="Monitor no enciende",
    description="El monitor de mi computadora no está encendiendo. Revisé los cables."
)

# Agregar comentario
TicketComment.objects.create(
    ticket=ticket,
    author_employee=empleado,
    body="He revisado la configuración y está correcta."
)
```

### Crear Orden de Mantenimiento

```python
orden = MaintenanceWorkOrder.objects.create(
    asset=activo,
    plan=MaintenancePlan.objects.first(),
    vendor=Vendor.objects.first(),
    m_type="PREVENTIVE",
    status="IN_PROGRESS",
    findings="Limpieza de ventilador",
    actions_taken="Limpieza de disipadores de calor",
    cost=50.00
)

# Completar orden
from django.utils import timezone
orden.status = "DONE"
orden.completed_at = timezone.now()
orden.save()

# Registrar evento
AssetEvent.objects.create(
    asset=activo,
    event_type="MAINTENANCE_DONE",
    related_mwo=orden,
    created_by_user=usuario
)
```

### Devolver Activo

```python
# Completar asignación
asignacion.returned_at = timezone.now()
asignacion.condition_in = "Pequeños rayaduras en la carcasa"
asignacion.save()

# Actualizar estado
activo.status = "IN_STOCK"
activo.save()

# Registrar evento
AssetEvent.objects.create(
    asset=activo,
    event_type="RETURNED",
    from_employee=empleado,
    related_assignment=asignacion,
    created_by_user=usuario,
    notes="Devolución sin problemas"
)
```

---

## Comandos Django Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Ver SQL generado
python manage.py sqlmigrate GestorITapps 0001

# Crear usuario superuser
python manage.py createsuperuser

# Shell interactivo
python manage.py shell

# Exportar datos
python manage.py dumpdata > backup.json

# Importar datos
python manage.py loaddata backup.json
```

---

## Notas Importantes

1. **Validaciones:** Siempre llamar a `modelo.clean()` antes de guardar para activar las validaciones personalizadas.

2. **ON_DELETE:** 
   - `PROTECT`: Previene eliminación si hay referencias
   - `CASCADE`: Elimina registros relacionados
   - `SET_NULL`: Pone NULL la referencia

3. **Jerarquía de Ubicaciones:** Debe respetarse siempre (Zone → Building → Site)

4. **Activo Tags:** Obligatorio solo para categorías con `assignable=True`

5. **Historial:** AssetEvent proporciona auditoría completa de cada activo

6. **Índices:** Crean tablas adicionales en BD para acelerar consultas, usar según necesidad

---

## Resumen

Este esquema proporciona una base sólida y escalable para gestionar:
- Inventario completo de activos de TI
- Asignaciones y devoluciones
- Mantenimiento preventivo y correctivo
- Tickets de soporte y comentarios
- Auditoría completa de movimientos
- Jerarquía de ubicaciones flexible
- Especificaciones personalizadas por activo

**Versión:** 1.0  
**Última actualización:** Abril 2026
