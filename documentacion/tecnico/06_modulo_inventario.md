# 6. Modulo inventario (unitario)

---

## 6.1 Proposito

Gestionar activos de TI pieza por pieza: alta, ubicacion, asignacion, kit, baja, movimientos e importacion.

---

## 6.2 Conceptos

| Concepto | Modelo / pieza |
|----------|----------------|
| Activo | `Equipo` |
| Estados | `EstadoEquipo` (En Stock, Asignado, En Mantenimiento, Baja) |
| Origen alta | `OrigenAltaEquipo` (legado, compra, etc.) |
| Movimiento | `MovimientoEquipo` + `TipoMovimiento` |
| Asignacion | `AsignacionEquipo` + `EstadoAsignacion` |
| Kit | `Equipo.equipo_padre` / perifericos |
| UI por tipo | `inventory_types.py` |

Constraint: `uniq_asignacion_activa_por_equipo` (solo una Activa por equipo).

---

## 6.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Vistas equipo | `views/equipo.py` |
| Importacion | `views/inventory_import.py`, `inventory_import.py` |
| Asignaciones | `views/asignacion.py`, `forms/asignacion.py` |
| Movimientos | `views/movimiento.py` (registros), `forms/movimiento.py` |
| Forms equipo | `forms/equipo.py` |
| Templates | `equipo/`, `asignacionequipo/`, `movimientoequipo/` |
| URLs | `equipo_*`, `periferico_*`, `herramienta_*`, `mis_equipos`, `asignacionequipo_*`, `movimientoequipo_*`, `inventario_importar*` |
| Helpers | `_crear_asignacion_activa`, `_reconciliar_estado_equipo`, `_crear_movimiento`, `user_can_view_equipo` |

---

## 6.4 Flujos principales

### Alta

Formulario tipado (equipo/periferico/herramienta). Si origen compra, bloquea cupo de `DetalleOrdenCompra` con `select_for_update`.

### Asignar / devolver

`_crear_asignacion_activa` con candado; cierra activas previas; sincroniza estado del equipo y movimiento.

### Detalle para Usuario

URL `equipo_detail` con `login_required`; `user_can_view_equipo` permite asignados/kit/solicitud; template oculta acciones si no es operativo.

### Importacion

Wizard parsea Excel, valida y ejecuta altas.

---

## 6.5 Reglas

- Una asignacion Activa por equipo.  
- Solo personal `activo=True` en forms de asignacion.  
- Baja/reactivacion/eliminacion fisica: Administrador.  
- No iniciar mantenimiento si equipo en Baja.  
- `fecha_alta` usa `timezone.localdate`.

---

## 6.6 Permisos

| Accion | Quien |
|--------|-------|
| CRUD inventario / movimientos | Operativo |
| Baja / eliminar equipo | Admin |
| Mis equipos / detalle propio | Usuario autenticado con derecho |

---

## 6.7 Integraciones

OC, mantenimiento, tickets (FK equipo), solicitudes, historial, mapa de sedes.

---

## 6.8 Puntos delicados

- Reconciliacion de estado tras asignar/devolver/kit.  
- Migracion de kit: solo perifericos con padre Activo para el mismo personal.  
- Dashboard “Disponibles” filtra `En Stock`.

---

## 6.9 Como probar

Clases: `EquipoFormCriticosTests`, `UserFailureHardeningTests` (asignacion unica, personal inactivo), `MisEquiposViewTests`, `InventarioImportTests`, `PropagarCustodiaPersonalTests`.
