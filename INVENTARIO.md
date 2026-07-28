# Inventario de equipos — Guía de funcionamiento

Documento de los cambios implementados en **Equipos**, **Movimientos**, **Asignaciones** y avisos de inventario, y de cómo opera el módulo actualmente.

---

## 1. Resumen

Se pasó el inventario de un CRUD básico a una operación con ficha de equipo, estados coherentes, baja lógica, dashboard, avisos en home (sin email) y movimientos como bitácora de auditoría.

| Bloque | Área | Qué se hizo |
|--------|------|-------------|
| 1 | Detalle + lista | Ficha del equipo, filtros/paginación, sync estado ↔ asignación |
| 2 | Ciclo de vida | Baja lógica, reactivar, asignar/devolver/ubicación desde el detalle |
| 3 | Operación | Dashboard + avisos home (sin ubicación, mant. largo, asignaciones antiguas) |
| 4 | Auditoría | Movimientos solo-lectura, export CSV, separación Historial vs Movimientos |

**Importante:** las notificaciones son solo avisos en **home**, **lista** y **dashboard**. No se envía correo.

---

## 2. Conceptos

### Equipo (`Equipo`)
Activo unitario de TI (código de inventario y serie únicos). Estados:

| Estado | Significado |
|--------|-------------|
| Disponible | Sin asignación activa |
| Asignado | Tiene asignación **Activa** |
| En Mantenimiento | Hay mantenimiento en curso (o se marcó así) |
| Baja | Baja lógica; inactivo; se conserva historial |

### Asignación (`AsignacionEquipo`)
Quién tiene el equipo. Estados: **Activa**, **Devuelta**, **Extraviada**. Solo puede haber **una Activa** por equipo.

### Movimiento (`MovimientoEquipo`)
Bitácora de auditoría (alta, baja, asignación, ubicación, mantenimiento). **Solo lectura** tras crearse: no se edita ni elimina.

### Historial de actividad (`HistorialActividad`)
Registro unificado de cambios del sistema (tickets, personal, equipos, compras, etc.). Es distinto de los movimientos de equipo.

### Roles
Hoy inventario, movimientos y asignaciones son **solo staff** (`admin_required`).

---

## 3. Sync estado ↔ asignación

```
Asignar (Activa) ──────────────► Equipo: Asignado
Devolver / Extraviada ────────► Equipo: Disponible
Baja / En Mantenimiento ──────► Prevalecen sobre la asignación
```

### Reglas
- **Disponible / Asignado** se reconcilian con la asignación activa al guardar equipo o asignación.
- No se puede asignar si el equipo está en **Baja** o **En Mantenimiento**.
- Al crear una asignación Activa se cierran otras activas del mismo equipo.
- Helpers en el modelo: `asignacion_activa`, `puede_asignarse`, `puede_devolver`, `puede_dar_de_baja`, `puede_reactivar`, `puede_cambiar_ubicacion`, `puede_eliminar_fisico`.

---

## 4. Vista detalle del equipo

Ruta: `/Equipos/<id>/`

- Datos, imagen, ubicación, estado y pedimiento.
- Asignación activa (si hay).
- Movimientos recientes (enlace a bitácora filtrada).
- Mantenimientos y tickets ligados.
- Historial de asignaciones.

### Acciones desde el detalle
| Acción | Efecto |
|--------|--------|
| **Asignar** | Crea asignación Activa + movimiento + estado Asignado |
| **Devolver** | Cierra asignación + movimiento + estado Disponible |
| **Ubicacion** | Cambia ubicación + movimiento |
| **Dar de baja** | Baja lógica (fecha/motivo), cierra asignaciones, inactivo + movimiento |
| **Reactivar** | Sale de Baja (vuelve a Disponible/Asignado según asignación) |
| **Programar mant.** | Prefill de mantenimiento |
| **Editar** | Formulario completo (con cuidado en estado) |

Tras crear/editar → redirige al detalle.

---

## 5. Baja lógica vs eliminación física

### Dar de baja (recomendado)
- Estado → **Baja**, `activo=False`, `fecha_baja` + `motivo_baja`.
- Cierra asignaciones activas.
- Genera movimiento `Dada de baja`.
- **No borra** el registro ni el historial.

### Eliminar físico
Solo si `puede_eliminar_fisico`:
- Sin asignaciones, mantenimientos ni tickets.
- Movimientos únicamente de tipo alta (o ninguno relevante de historial operativo).

Si no cumple → error y se pide usar **Dar de baja**.

---

## 6. Lista de equipos

Ruta: `/Equipos/`

- Búsqueda: código, serie, marca, modelo, pedimiento, descripción.
- Filtros: aviso, estado, categoría, ubicación, sin ubicación, activo, fechas de alta.
- Paginación (20).
- Abrir → detalle.
- **Exportar CSV** (respeta los filtros actuales).
- Enlace a **Dashboard**.

### Filtros de aviso (`?alerta=`)
| Valor | Criterio |
|-------|----------|
| `sin_ubicacion` | Activo, no Baja, sin ubicación |
| `mant_largo` | En Mantenimiento &gt; 14 días (o sin movimiento de mant.) |
| `asignacion_antigua` | Asignación Activa ≥ 180 días |
| `baja` | Estado Baja |

---

## 7. Avisos en home (sin email)

Solo staff.

| Aviso | Criterio |
|-------|----------|
| **Sin ubicación** | Activo, no Baja, `ubicacion` nula |
| **Mant. prolongado** | En Mantenimiento más de **14 días** |
| **Asignaciones antiguas** | Activa desde hace más de **180 días** |

Aparecen en:
- KPI “Inventario por atender”
- Banners de alerta
- Tabla “Inventario por atender”
- Acceso rápido a **Dashboard de inventario**

---

## 8. Dashboard de inventario

Ruta: `/Equipos/dashboard/`

También desde lista, home y sidebar.

### Contenido
- KPI: Disponibles, Asignados, En mantenimiento, Baja.
- Focos: sin ubicación, mant. prolongado, asignaciones antiguas, total.
- Por estado, categoría y ubicación (con enlaces filtrados).
- Tablas de sin ubicación, mant. largo y asignaciones antiguas.

---

## 9. Movimientos (auditoría)

Ruta lista: `/MovimientoEquipos/registros/`  
Detalle: `/MovimientoEquipos/<id>/`

### Comportamiento
- Se crean **automáticamente** desde acciones del equipo (alta, baja, asignar, devolver, ubicación, mantenimiento).
- Tras crear: **no se editan ni eliminan** (URLs de update/delete redirigen al detalle con aviso).
- Alta manual sigue disponible como excepción (“Registrar movimiento”), también append-only.
- Filtros: búsqueda, tipo, equipo, fechas + paginación.
- **Exportar CSV** (respeta filtros).
- Enlaces a ficha del equipo, mantenimientos y tickets del equipo.

### Tipos de movimiento
- Dada de alta / Dada de baja  
- Asignacion de equipo / Cambio de asignacion  
- En mantenimiento / Cambio de ubicacion  

---

## 10. Historial general vs Movimientos

| Pantalla | Ruta | Qué es |
|----------|------|--------|
| **Historial** | `/MovimientoEquipos/` | Actividad unificada del sistema (`HistorialActividad`) |
| **Movimientos** | `/MovimientoEquipos/registros/` | Bitácora física de equipos (`MovimientoEquipo`) |

En el menú:
- **Inventario → Movimientos**
- **Operaciones → Historial**

---

## 11. Export CSV

| Origen | Parámetro | Archivo típico |
|--------|-----------|----------------|
| Lista de equipos | `?export=csv` | `inventario_equipos.csv` |
| Movimientos | `?export=csv` | `movimientos_equipo.csv` |

Incluyen BOM UTF-8 para Excel. Columnas principales:

- **Equipos:** código, serie, marca, modelo, categoría, estado, activo, ubicación, proveedor, pedimiento, fechas y motivo de baja.
- **Movimientos:** fecha, equipo, tipo, origen, destino, responsable, observaciones.

---

## 12. Rutas principales

| Ruta | Nombre | Quién |
|------|--------|--------|
| `/Equipos/` | `equipo_list` | Staff |
| `/Equipos/dashboard/` | `equipo_dashboard` | Staff |
| `/Equipos/create/` | `equipo_create` | Staff |
| `/Equipos/<id>/` | `equipo_detail` | Staff |
| `/Equipos/update/<id>/` | `equipo_update` | Staff |
| `/Equipos/delete/<id>/` | `equipo_delete` | Staff |
| `/Equipos/<id>/baja/` | `equipo_dar_baja` | Staff |
| `/Equipos/<id>/reactivar/` | `equipo_reactivar` | Staff |
| `/Equipos/<id>/asignar/` | `equipo_asignar` | Staff |
| `/Equipos/<id>/devolver/` | `equipo_devolver` | Staff |
| `/Equipos/<id>/ubicacion/` | `equipo_cambiar_ubicacion` | Staff |
| `/MovimientoEquipos/` | `movimientoequipo_list` | Staff (Historial general) |
| `/MovimientoEquipos/registros/` | `movimientoequipo_registros` | Staff (Movimientos) |
| `/MovimientoEquipos/<id>/` | `movimientoequipo_detail` | Staff |
| `/MovimientoEquipos/create/` | `movimientoequipo_create` | Staff |
| `/AsignacionEquipos/` | `asignacionequipo_list` | Staff |

Filtros útiles:
- Equipos: `/Equipos/?alerta=sin_ubicacion`
- Movimientos de un equipo: `/MovimientoEquipos/registros/?equipo=<id>`
- Tickets / mant. de un equipo: `?equipo=<id>` en sus listas

---

## 13. Archivos clave

| Archivo | Rol |
|---------|-----|
| `GestorApp/models.py` | `Equipo`, `MovimientoEquipo`, `AsignacionEquipo`, helpers de flujo |
| `GestorApp/views.py` | CRUD, sync, baja, dashboard, avisos, export CSV, movimientos audit-only |
| `GestorApp/historial.py` | Eventos de actividad del sistema |
| `GestorIT/urls.py` | Rutas |
| `GestorApp/Templates/equipo/` | list, detail, form, dashboard, baja, asignar, ubicacion |
| `GestorApp/Templates/movimientoequipo/` | list (historial), registros, detail, form |
| `GestorApp/Templates/home.html` | KPIs y alertas de inventario |
| `GestorApp/Templates/base.html` | Sidebar Inventario / Movimientos / Historial |

Constantes en vistas:
- `EQUIPO_LIST_PAGE_SIZE = 20`
- `EQUIPO_ASIGNACION_ALERTA_DIAS = 180`
- `EQUIPO_MANTENIMIENTO_LARGO_DIAS = 14`
- `MOVIMIENTO_LIST_PAGE_SIZE = 25`

---

## 14. Cómo usarlo (día a día)

1. Revisa **home**: sin ubicación, mant. prolongado y asignaciones antiguas.
2. Abre el **Dashboard de inventario** para priorizar.
3. En la **ficha del equipo**: asignar, devolver, cambiar ubicación o dar de baja (no borres si hay historial).
4. Consulta **Movimientos** para auditoría; usa **Exportar CSV** cuando necesites Excel.
5. Usa **Historial** solo para la actividad general del sistema (no confundir con movimientos de equipo).
6. Cruza con **Mantenimientos** y **Tickets** desde la ficha o con `?equipo=`.

---

## 15. Fuera de alcance (aún no)

- Notificaciones por **email**.
- Recepción automática desde orden de compra (OC → alta de equipos).
- Permisos finos para no-staff (p. ej. “mis equipos asignados”).
- Impresión de etiqueta / resguardo PDF.
- Campos extra (garantía, condición, QR).
- Stock de consumibles (el modelo sigue siendo unitario por pieza).
- Renombrar URLs históricas `MovimientoEquipos/` del historial general (la UI ya separa los conceptos).
