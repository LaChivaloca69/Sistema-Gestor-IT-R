# Inventario de equipos — Guía de funcionamiento

Documento actualizado del módulo de **Inventario**: equipos, ubicaciones, proveedores, asignaciones, movimientos, vínculo con **órdenes de compra** y avisos operativos.

Relacionado: `ROLES.md` (permisos Usuario / Tecnico IT / Administrador).

---

## 1. Resumen

El inventario gestiona **activos unitarios de TI** (una fila = una pieza), no stock de consumibles. Opera como ciclo de vida:

| Área | Qué hace |
|------|----------|
| Ficha de equipo | Hub: datos, asignación, movimientos, mant., tickets, OC |
| Estados | Disponible / Asignado / En Mantenimiento / Baja |
| Alta | Manual (legado) o desde OC terminada (compra, con cupo por línea) |
| Operación | Asignar, devolver, ubicación, baja lógica, reactivar |
| Avisos | Home + dashboard (sin email) |
| Auditoría | `MovimientoEquipo` + `HistorialActividad` |

**Importante:** las notificaciones son solo avisos en **home**, **lista** y **dashboard**. No se envía correo.

---

## 2. Mapa de relaciones

```
Proveedor ──────────────┐
CategoriaEquipo ────────┤
Edificio → Zona → Ubicacion ─┤
OrdenCompra → DetalleOrdenCompra ─┐
                                 │
                                 ▼
                              Equipo
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
   AsignacionEquipo      MovimientoEquipo           TicketIT
   (Personal)                                       Mantenimiento
                                                    AgendaMantenimiento
```

| Entidad | Relación con `Equipo` | Notas |
|---------|----------------------|--------|
| `CategoriaEquipo` | FK obligatoria | Laptop, Monitor, etc. |
| `Proveedor` | FK opcional | También se usa en OC |
| `Ubicacion` | FK opcional | Jerarquía Edificio → Zona → Ubicación |
| `OrdenCompra` | FK opcional | Solo si origen de alta = Compra |
| `DetalleOrdenCompra` | FK opcional | Línea concreta; descuenta cupo (1 por alta) |
| `AsignacionEquipo` | 1:N | Quién lo tiene; máx. una **Activa** |
| `MovimientoEquipo` | 1:N | Bitácora física append-only |
| `Mantenimiento` | 1:N | Sync de estado En Mantenimiento |
| `TicketIT` | 1:N (opcional) | Soporte ligado al activo |
| `Personal` | vía asignación | Custodio actual |

### Entidades de apoyo (catálogos)

| Modelo | Uso |
|--------|-----|
| `CategoriaEquipo` | Clasificación del activo |
| `Proveedor` | Código auto `PROV-######`, RFC, razón social, tipo, ciudad/estado/CP, sitio web, notas |
| `Edificio` / `ZonaEdificio` / `Ubicacion` | Ubicación física en planta |
| `OrdenCompra` / `DetalleOrdenCompra` | Compra → recepción a inventario |

---

## 3. Conceptos del equipo

### Estados (`EstadoEquipo`)

| Estado | Significado |
|--------|-------------|
| Disponible | Sin asignación activa |
| Asignado | Tiene asignación **Activa** |
| En Mantenimiento | Mantenimiento en curso (prevalece sobre Disponible/Asignado) |
| Baja | Baja lógica; `activo=False`; se conserva historial |

### Origen de alta (`OrigenAltaEquipo`)

Define **cómo entró** el equipo al sistema:

| Origen | Cuándo usarlo | ¿Pide OC? |
|--------|---------------|-----------|
| **Compra (con OC)** | Comprado y documentado en una orden terminada | Sí (orden + producto/línea) |
| **Legado / histórico** | Equipos viejos sin OC en el sistema (default) | No |
| **Donacion** | Donado | No |
| **Transferencia** | Traspaso de otra área/planta | No |
| **Otro** | Casos especiales | No |

En el formulario de alta/edición, los campos **Orden de compra** y **Producto de la orden** solo se muestran si el origen es **Compra**. En cualquier otro origen se ocultan y se limpian al guardar.

### Campos principales de `Equipo`

| Campo | Descripción |
|-------|-------------|
| `codigo_inventario` | ID único |
| `numero_serie` | Único, opcional |
| `categoria`, `marca`, `modelo` | Identificación |
| `Numero_Pedimiento` | Texto corto; al alta desde OC suele copiar el folio |
| `descripcion_equipo`, `imagen` | Detalle |
| `proveedor` | FK opcional |
| `origen_alta` | Compra / Legado / … |
| `orden_compra`, `detalle_orden` | Vínculo a compra (solo Compra) |
| `estado_equipo`, `ubicacion` | Estado y lugar |
| `fecha_alta`, `fecha_baja`, `motivo_baja`, `activo` | Ciclo de vida |

---

## 4. Roles y permisos (inventario)

Ver detalle en `ROLES.md`. Resumen operativo:

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| **Mis equipos** (`/Equipos/mis/`) | Sí (solo los asignados a su Personal) | Sí | Sí |
| Lista / dashboard / ficha inventarios | No | Sí | Sí |
| Alta / editar / asignar / devolver / ubicación | No | Sí | Sí |
| Movimientos / asignaciones CRUD operativo | No | Sí | Sí |
| Dar de baja / reactivar / borrar equipo | No | No | Sí |
| Dar de alta desde OC | No | Sí | Sí |

Decoradores: `operativo_required` (Técnico + Admin), `admin_required` (solo Admin).

---

## 5. Sync estado ↔ asignación

```
Asignar (Activa) ──────────────► Equipo: Asignado
Devolver / Extraviada ────────► Equipo: Disponible
Baja / En Mantenimiento ──────► Prevalecen sobre la asignación
```

### Reglas
- **Disponible / Asignado** se reconcilian con la asignación activa al guardar equipo o asignación.
- No se puede asignar si el equipo está en **Baja** o **En Mantenimiento**.
- Al crear una asignación Activa se cierran otras activas del mismo equipo (lógica de aplicación).
- Helpers: `asignacion_activa`, `puede_asignarse`, `puede_devolver`, `puede_dar_de_baja`, `puedereactivar`, `puede_cambiar_ubicacion`, `puede_eliminar_fisico`.

---

## 6. Alta de equipos y órdenes de compra

### 6.1 Flujo compra (con OC)

```
OC creada (líneas) ──► Marcar Terminado ──► Cupo por línea
OC PDF subida ───────► Terminado + capturar líneas ──► Cupo por línea
                              │
                              ▼
                    Dar de alta equipo(s)
                    (origen=Compra, elige Producto de la orden)
                              │
                              ▼
                    Se descuenta 1 disponible de esa línea
```

1. La OC debe estar en estado **Terminado** y tener al menos una línea (`DetalleOrdenCompra`).
2. En la OC aparece la tabla **Productos de la orden (cupo inventario)**:
   - Cantidad OC
   - Dados de alta
   - Disponibles
   - Botón **Alta (-1)** por línea con cupo
3. Al crear el equipo:
   - Origen = **Compra**
   - Se elige **Producto de la orden** (etiqueta tipo: `Laptop — disponibles: 1 (alta: 1/2)`)
   - Cada alta válida **descuenta 1** de esa línea
4. Si no queda cupo en ninguna línea → no se puede seguir dando de alta contra esa OC.
5. Equipos ligados se listan en la ficha de la OC.

Rutas útiles:
- Terminar OC: `/OrdenesCompra/<id>/terminar/` (`ordencompra_terminar`)
- Alta con OC: `/Equipos/create/?orden=<id>` o `?orden=<id>&detalle=<id>`

### 6.2 Cupo por línea (`DetalleOrdenCompra`)

| Concepto | Cálculo |
|----------|---------|
| Cantidad esperada | Parte entera de `cantidad` de la línea |
| Dados de alta | Nº de `Equipo` con `detalle_orden` = esa línea |
| Disponibles | esperada − dados de alta |

Validaciones:
- Origen Compra exige OC + línea.
- No se permite alta si `disponibles <= 0`.
- Al editar un equipo ya ligado, su propio registro no “consume” cupo extra.

### 6.3 Alta sin OC (legado y otros)

1. Nuevo equipo → origen **Legado** (default), **Donacion**, **Transferencia** u **Otro**.
2. No aparecen campos de OC.
3. Filtros en lista: **Origen alta** y **Solo sin orden**.

Así los equipos históricos quedan ordenados sin inventar órdenes falsas.

### 6.4 OC creada vs OC subida (PDF)

| Origen OC | Al marcar Terminado |
|-----------|---------------------|
| Creada en app (plantilla/líneas) | Usa las líneas ya capturadas |
| Subida PDF | Exige capturar varias líneas (descripción + cantidad) antes de quedar lista |

Ambas, una vez Terminadas con líneas y cupo, usan el mismo botón **Dar de alta equipo**.

---

## 7. Vista detalle del equipo

Ruta: `/Equipos/<id>/`

Muestra:
- Datos, imagen, ubicación, estado, pedimiento, proveedor.
- **Origen de alta** y enlace a **Orden de compra** (si hay).
- Asignación activa.
- Movimientos recientes.
- Mantenimientos y tickets ligados.
- Historial de asignaciones.

### Acciones desde el detalle

| Acción | Efecto | Quién |
|--------|--------|-------|
| Asignar | Asignación Activa + movimiento + Asignado | Operativo |
| Devolver | Cierra asignación + movimiento + Disponible | Operativo |
| Ubicacion | Cambia ubicación + movimiento | Operativo |
| Dar de baja | Baja lógica (Admin) | Admin |
| Reactivar | Sale de Baja | Admin |
| Programar mant. | Prefill mantenimiento | Operativo |
| Editar | Formulario (OC solo si origen=Compra) | Operativo |
| Eliminar | Solo si `puede_eliminar_fisico` | Admin |

---

## 8. Baja lógica vs eliminación física

### Dar de baja (recomendado)
- Estado → **Baja**, `activo=False`, `fecha_baja` + `motivo_baja`.
- Cierra asignaciones activas.
- Movimiento `Dada de baja`.
- **No borra** el registro ni el historial.

### Eliminar físico
Solo si `puede_eliminar_fisico`:
- Sin asignaciones, mantenimientos ni tickets.
- Sin historial operativo relevante en movimientos.

Si no cumple → error y se pide usar **Dar de baja**.

---

## 9. Lista de equipos

Ruta: `/Equipos/`

- Búsqueda: código, serie, marca, modelo, pedimiento, descripción.
- Filtros: aviso, estado, categoría, ubicación, sin ubicación, **origen alta**, **sin OC**, activo, fechas de alta.
- Paginación (20).
- Exportar CSV (respeta filtros).
- Enlace a Dashboard.

### Filtros de aviso (`?alerta=`)

| Valor | Criterio |
|-------|----------|
| `sin_ubicacion` | Activo, no Baja, sin ubicación |
| `mant_largo` | En Mantenimiento &gt; 14 días |
| `asignacion_antigua` | Asignación Activa ≥ 180 días |
| `baja` | Estado Baja |

### Mis equipos

Ruta: `/Equipos/mis/` — cualquier usuario autenticado ve solo asignaciones **Activas** de su perfil `Personal`. Desde ahí puede ir a crear un ticket (p. ej. tipo Mantenimiento).

---

## 10. Avisos en home (sin email)

Visible para rol **operativo** (Técnico IT / Admin).

| Aviso | Criterio |
|-------|----------|
| Sin ubicación | Activo, no Baja, `ubicacion` nula |
| Mant. prolongado | En Mantenimiento más de **14 días** |
| Asignaciones antiguas | Activa desde hace más de **180 días** |

Aparecen en KPI, banners y tablas de home; deep-link al dashboard/lista filtrada.

---

## 11. Dashboard de inventario

Ruta: `/Equipos/dashboard/`

- KPI por estado.
- Focos: sin ubicación, mant. prolongado, asignaciones antiguas.
- Desglose por estado, categoría y ubicación (enlaces filtrados).
- Tablas de atención.

---

## 12. Movimientos (auditoría de equipo)

Ruta lista: `/MovimientoEquipos/registros/`  
Detalle: `/MovimientoEquipos/<id>/`

- Se crean **automáticamente** (alta, baja, asignar, devolver, ubicación, mantenimiento).
- Tras crear: **no se editan ni eliminan** (append-only).
- Alta manual excepcional (“Registrar movimiento”).
- Filtros + export CSV.

### Tipos
- Dada de alta / Dada de baja  
- Asignacion de equipo / Cambio de asignacion  
- En mantenimiento / Cambio de ubicacion  

---

## 13. Historial general vs Movimientos

| Pantalla | Ruta | Modelo |
|----------|------|--------|
| **Historial** | `/MovimientoEquipos/` | `HistorialActividad` (todo el sistema) |
| **Movimientos** | `/MovimientoEquipos/registros/` | `MovimientoEquipo` (solo equipos) |

Menú:
- **Inventario → Movimientos**
- **Operaciones → Historial**

---

## 14. Export CSV

| Origen | Parámetro | Archivo |
|--------|-----------|---------|
| Lista de equipos | `?export=csv` | `inventario_equipos.csv` |
| Movimientos | `?export=csv` | `movimientos_equipo.csv` |

UTF-8 con BOM para Excel.

---

## 15. Rutas principales

| Ruta | Nombre | Quién |
|------|--------|--------|
| `/Equipos/mis/` | `mis_equipos` | Autenticado |
| `/Equipos/` | `equipo_list` | Operativo |
| `/Equipos/dashboard/` | `equipo_dashboard` | Operativo |
| `/Equipos/create/` | `equipo_create` | Operativo |
| `/Equipos/<id>/` | `equipo_detail` | Operativo |
| `/Equipos/update/<id>/` | `equipo_update` | Operativo |
| `/Equipos/delete/<id>/` | `equipo_delete` | Admin |
| `/Equipos/<id>/baja/` | `equipo_dar_baja` | Admin |
| `/Equipos/<id>/reactivar/` | `equipo_reactivar` | Admin |
| `/Equipos/<id>/asignar/` | `equipo_asignar` | Operativo |
| `/Equipos/<id>/devolver/` | `equipo_devolver` | Operativo |
| `/Equipos/<id>/ubicacion/` | `equipo_cambiar_ubicacion` | Operativo |
| `/MovimientoEquipos/registros/` | `movimientoequipo_registros` | Operativo |
| `/AsignacionEquipos/` | `asignacionequipo_list` | Operativo |
| `/OrdenesCompra/<id>/terminar/` | `ordencompra_terminar` | Dueño OC / reglas compras |
| `/OrdenesCompra/...` + alta `?orden=` | vínculo Compra → inventario | Operativo (alta) |

Filtros útiles:
- `/Equipos/?alerta=sin_ubicacion`
- `/Equipos/?origen_alta=Legado`
- `/Equipos/?sin_oc=1`
- `/MovimientoEquipos/registros/?equipo=<id>`

---

## 16. Archivos clave

| Archivo | Rol |
|---------|-----|
| `GestorApp/models.py` | `Equipo`, `OrigenAltaEquipo`, OC/detalle (cupo), asignación, movimiento, ubicación, proveedor |
| `GestorApp/views.py` | CRUD equipo, cupo OC, sync, baja, dashboard, mis equipos |
| `GestorApp/historial.py` | Actividad del sistema |
| `GestorIT/urls.py` | Rutas y decoradores de rol |
| `GestorApp/Templates/equipo/` | list, detail, form, dashboard, mis_equipos, baja, asignar, ubicacion |
| `GestorApp/Templates/ordencompra/` | terminar, cupo en form_crear/form_subir |
| `ROLES.md` | Matriz de roles completa |

Constantes en vistas:
- `EQUIPO_LIST_PAGE_SIZE = 20`
- `EQUIPO_ASIGNACION_ALERTA_DIAS = 180`
- `EQUIPO_MANTENIMIENTO_LARGO_DIAS = 14`
- `MOVIMIENTO_LIST_PAGE_SIZE = 25`

---

## 17. Cómo usarlo (día a día)

1. **Home (operativo):** revisa focos de inventario.
2. **Dashboard / lista:** prioriza sin ubicación, mant. largo, asignaciones viejas.
3. **Compra nueva:** termina la OC → da de alta equipos eligiendo el producto de la línea (se descuenta cupo).
4. **Equipo viejo:** alta con origen **Legado** (sin OC).
5. **Ficha:** asignar, devolver, ubicar; baja solo Admin.
6. **Usuario final:** Mis equipos + tickets (p. ej. tipo Mantenimiento).
7. **Auditoría:** Movimientos (equipo) vs Historial (sistema).

---

## 18. Fuera de alcance (aún no)

- Notificaciones por **email**.
- Recepción guiada masiva (N series de una línea en un solo wizard).
- Impresión de etiqueta / resguardo PDF / QR.
- Campos extra (garantía, condición, hostname, costo).
- Stock de consumibles (el modelo sigue siendo unitario por pieza).
- Constraint de BD “máx. 1 asignación Activa” (hoy solo en lógica de app).
- Renombrar URLs históricas `MovimientoEquipos/` del historial general.
