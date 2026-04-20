# Documentación de Base de Datos - Sistema IT para Fábrica

## 1. Información General

- **Proyecto:** Sistema IT para Fábrica
- **Motor de base de datos:** PostgreSQL
- **Framework backend:** Python + Django
- **ORM:** Django ORM
- **Fecha:** 2026-04-20

## 2. Objetivo

Diseñar y documentar una base de datos para la gestión integral del área de TI en una fábrica, incluyendo:

- Inventario general de equipos (CRUD)
- Altas y bajas de activos
- Entradas y salidas de equipos
- Asignación de equipos a personal
- Mantenimiento (registro, calendario y agenda de próximos servicios)
- Sistema de tickets IT
- Gestión de presupuestos y compras de materiales
- Ubicación física de activos por edificio y zona

## 3. Alcance Funcional

### 3.1 Módulos incluidos

1. Catálogos organizacionales
2. Ubicación física en planta
3. Inventario de equipos
4. Movimientos de equipos
5. Asignaciones de equipos
6. Mantenimiento y agenda
7. Tickets IT y seguimiento
8. Presupuestos
9. Compras de materiales

## 4. Convenciones de Diseño

- Nomenclatura de tablas y campos en español.
- Claves primarias autoincrementales (`id` en Django / `SERIAL` o `BIGSERIAL` en PostgreSQL).
- Fechas de auditoría en campos `fecha_creacion`, `fecha_evento`, etc.
- Bajas lógicas mediante el campo `activo`.
- Catálogos de estado modelados con `choices` en Django o tablas catálogo según necesidad.
- Integridad referencial mediante claves foráneas.

## 5. Modelo de Datos (Resumen de Entidades)

- **Organización:** Area, Puesto, Personal
- **Inventario:** CategoriaEquipo, Proveedor, Equipo
- **Ubicación:** Edificio, ZonaEdificio, Ubicacion
- **Operación de activos:** MovimientoEquipo, AsignacionEquipo
- **Mantenimiento:** Mantenimiento, AgendaMantenimiento
- **Soporte:** TicketIT, SeguimientoTicket
- **Gestión económica:** Presupuesto, DetallePresupuesto, CompraMaterial, DetalleCompraMaterial

## 6. Diccionario de Datos

## 6.1 Catálogos organizacionales

### Tabla: `area`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador único |
| nombre_area | varchar(100) | No |  | Nombre del área |
| descripcion_area | varchar(255) | Sí |  | Descripción |
| activo | boolean | No | default true | Estado lógico |
| fecha_creacion | datetime | No | auto_now_add | Fecha de creación |

### Tabla: `puesto`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador único |
| nombre_puesto | varchar(100) | No |  | Nombre del puesto |
| descripcion_puesto | varchar(255) | Sí |  | Descripción |
| activo | boolean | No | default true | Estado lógico |

### Tabla: `personal`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador único |
| numero_empleado | varchar(30) | No | unique | Folio de empleado |
| nombre | varchar(100) | No |  | Nombre |
| apellido_paterno | varchar(100) | No |  | Apellido paterno |
| apellido_materno | varchar(100) | Sí |  | Apellido materno |
| correo | email | Sí |  | Correo electrónico |
| telefono | varchar(30) | Sí |  | Teléfono |
| area_id | FK | Sí | area(id) | Área del empleado |
| puesto_id | FK | Sí | puesto(id) | Puesto del empleado |
| activo | boolean | No | default true | Estado lógico |
| fecha_ingreso | date | Sí |  | Fecha de ingreso |
| fecha_creacion | datetime | No | auto_now_add | Fecha de creación |

## 6.2 Ubicación física

### Tabla: `edificio`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| nombre_edificio | varchar(100) | No |  | Nombre del edificio |
| descripcion_edificio | varchar(255) | Sí |  | Descripción |
| activo | boolean | No | default true | Estado lógico |

### Tabla: `zona_edificio`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| edificio_id | FK | No | edificio(id) | Edificio padre |
| nombre_zona | varchar(100) | No |  | Nombre de zona |
| descripcion_zona | varchar(255) | Sí |  | Descripción |
| activo | boolean | No | default true | Estado lógico |

### Tabla: `ubicacion`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| edificio_id | FK | No | edificio(id) | Edificio |
| zona_id | FK | No | zona_edificio(id) | Zona |
| pasillo | varchar(50) | Sí |  | Pasillo |
| rack | varchar(50) | Sí |  | Rack |
| anaquel | varchar(50) | Sí |  | Anaquel |
| referencia | varchar(255) | Sí |  | Referencia textual |
| activo | boolean | No | default true | Estado lógico |

## 6.3 Inventario

### Tabla: `categoria_equipo`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| nombre_categoria | varchar(100) | No |  | Categoría |
| descripcion_categoria | varchar(255) | Sí |  | Descripción |
| activo | boolean | No | default true | Estado lógico |

### Tabla: `proveedor`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| nombre_proveedor | varchar(150) | No |  | Proveedor |
| contacto | varchar(150) | Sí |  | Nombre de contacto |
| correo | email | Sí |  | Correo |
| telefono | varchar(30) | Sí |  | Teléfono |
| direccion | varchar(255) | Sí |  | Dirección |
| activo | boolean | No | default true | Estado lógico |

### Tabla: `equipo`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| codigo_inventario | varchar(50) | No | unique | Código interno |
| numero_serie | varchar(100) | Sí | unique | Serie de fabricante |
| categoria_id | FK | No | categoria_equipo(id) | Categoría |
| marca | varchar(80) | Sí |  | Marca |
| modelo | varchar(80) | Sí |  | Modelo |
| descripcion_equipo | varchar(255) | Sí |  | Descripción |
| fecha_compra | date | Sí |  | Fecha de compra |
| costo_compra | numeric(12,2) | Sí |  | Costo |
| garantia_meses | int | No | default 0 | Garantía en meses |
| proveedor_id | FK | Sí | proveedor(id) | Proveedor |
| estado_equipo | varchar(30) | No | choices | Estado del equipo |
| ubicacion_id | FK | Sí | ubicacion(id) | Ubicación física |
| fecha_alta | date | No |  | Fecha de alta |
| fecha_baja | date | Sí |  | Fecha de baja |
| motivo_baja | varchar(255) | Sí |  | Motivo |
| activo | boolean | No | default true | Baja lógica |
| fecha_creacion | datetime | No | auto_now_add | Auditoría |

## 6.4 Movimientos y asignaciones

### Tabla: `movimiento_equipo`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| equipo_id | FK | No | equipo(id) | Equipo |
| tipo_movimiento | varchar(20) | No | choices | Entrada/Salida/Transferencia/Baja |
| fecha_movimiento | datetime | No | auto_now_add | Fecha del movimiento |
| cantidad | int | No | default 1 | Cantidad |
| origen | varchar(150) | Sí |  | Origen |
| destino | varchar(150) | Sí |  | Destino |
| responsable | varchar(150) | Sí |  | Responsable |
| observaciones | varchar(255) | Sí |  | Notas |

### Tabla: `asignacion_equipo`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| equipo_id | FK | No | equipo(id) | Equipo asignado |
| personal_id | FK | No | personal(id) | Personal asignado |
| fecha_asignacion | datetime | No | auto_now_add | Inicio de asignación |
| fecha_devolucion | datetime | Sí |  | Devolución |
| estado_asignacion | varchar(20) | No | choices | Activa/Devuelta/Extraviada |
| observaciones | varchar(255) | Sí |  | Notas |

## 6.5 Mantenimiento

### Tabla: `mantenimiento`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| equipo_id | FK | No | equipo(id) | Equipo |
| tipo_mantenimiento | varchar(20) | No | choices | Preventivo/Correctivo/Predictivo |
| estado_mantenimiento | varchar(20) | No | choices | Programado/En Proceso/Completado/Cancelado |
| fecha_programada | date | No |  | Fecha objetivo |
| fecha_inicio | datetime | Sí |  | Inicio real |
| fecha_fin | datetime | Sí |  | Fin real |
| tecnico_responsable | varchar(150) | Sí |  | Técnico |
| costo_mantenimiento | numeric(12,2) | No | default 0 | Costo |
| descripcion_falla | varchar(255) | Sí |  | Falla reportada |
| acciones_realizadas | text | Sí |  | Trabajo ejecutado |
| proxima_fecha_mantenimiento | date | Sí |  | Próximo mantenimiento |
| observaciones | varchar(255) | Sí |  | Notas |

### Tabla: `agenda_mantenimiento`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| mantenimiento_id | FK | No | mantenimiento(id) | Relación de mantenimiento |
| fecha_recordatorio | datetime | No |  | Fecha/hora del recordatorio |
| canal_recordatorio | varchar(50) | Sí |  | Canal (correo/sistema) |
| enviado | boolean | No | default false | Estado de envío |

## 6.6 Tickets IT

### Tabla: `ticket_it`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| folio_ticket | varchar(30) | No | unique | Folio |
| fecha_creacion | datetime | No | auto_now_add | Fecha de alta |
| personal_solicitante_id | FK | No | personal(id) | Solicitante |
| equipo_id | FK | Sí | equipo(id) | Equipo relacionado |
| titulo | varchar(150) | No |  | Resumen del problema |
| descripcion | text | No |  | Detalle del caso |
| prioridad | varchar(10) | No | choices | Baja/Media/Alta/Crítica |
| estado_ticket | varchar(20) | No | choices | Abierto/En Proceso/Resuelto/Cerrado |
| tecnico_asignado | varchar(150) | Sí |  | Técnico responsable |
| fecha_cierre | datetime | Sí |  | Fecha de cierre |
| solucion | text | Sí |  | Solución aplicada |

### Tabla: `seguimiento_ticket`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| ticket_id | FK | No | ticket_it(id) | Ticket relacionado |
| fecha_evento | datetime | No | auto_now_add | Fecha/hora del evento |
| comentario | text | No |  | Comentario de seguimiento |
| usuario_evento | varchar(150) | No |  | Usuario que registra |
| cambio_estado | varchar(100) | Sí |  | Cambio aplicado |

## 6.7 Presupuestos y compras

### Tabla: `presupuesto`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| folio_presupuesto | varchar(30) | No | unique | Folio |
| fecha_presupuesto | date | No |  | Fecha |
| cliente_o_area | varchar(150) | No |  | Destinatario |
| elaborado_por | varchar(150) | No |  | Responsable |
| subtotal | numeric(12,2) | No | default 0 | Suma de importes |
| impuestos | numeric(12,2) | No | default 0 | IVA u otro impuesto |
| total | numeric(12,2) | No | default 0 | Total final |
| estado_presupuesto | varchar(30) | No | default 'Borrador' | Estado |
| notas | varchar(255) | Sí |  | Notas |

### Tabla: `detalle_presupuesto`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| presupuesto_id | FK | No | presupuesto(id), cascade | Cabecera |
| concepto | varchar(150) | No |  | Concepto |
| descripcion | varchar(255) | Sí |  | Descripción |
| cantidad | numeric(10,2) | No |  | Cantidad |
| precio_unitario | numeric(12,2) | No |  | Precio unitario |
| importe | numeric(12,2) | No | default 0 | cantidad * precio_unitario |

### Tabla: `compra_material`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| folio_compra | varchar(30) | No | unique | Folio |
| fecha_compra | date | No |  | Fecha |
| proveedor_id | FK | Sí | proveedor(id) | Proveedor |
| solicitado_por | varchar(150) | Sí |  | Responsable |
| subtotal | numeric(12,2) | No | default 0 | Subtotal |
| impuestos | numeric(12,2) | No | default 0 | Impuestos |
| total | numeric(12,2) | No | default 0 | Total |
| estado_compra | varchar(30) | No | default 'Solicitada' | Estado |
| observaciones | varchar(255) | Sí |  | Notas |

### Tabla: `detalle_compra_material`
| Campo | Tipo | Nulo | Restricción | Descripción |
|---|---|---|---|---|
| id | PK | No | Autoincremental | Identificador |
| compra_id | FK | No | compra_material(id), cascade | Cabecera |
| concepto | varchar(150) | No |  | Concepto |
| descripcion | varchar(255) | Sí |  | Descripción |
| cantidad | numeric(10,2) | No |  | Cantidad |
| costo_unitario | numeric(12,2) | No |  | Costo unitario |
| importe | numeric(12,2) | No | default 0 | cantidad * costo_unitario |

## 7. Reglas de Negocio

1. Cuando una asignación se crea en estado `Activa`, el equipo cambia a estado `Asignado`.
2. Cuando una asignación cambia a `Devuelta`, el equipo cambia a estado `Disponible`.
3. Cuando se crea un mantenimiento, el equipo cambia a estado `En Mantenimiento`.
4. En detalles de presupuesto y compra:
   - `importe = cantidad * precio_unitario` (o `costo_unitario`)
   - Se recalculan automáticamente `subtotal`, `impuestos` y `total` en la cabecera.
5. En baja lógica de equipo:
   - `activo = false`
   - se registra `fecha_baja` y `motivo_baja`.

## 8. Integridad y Restricciones

### 8.1 Restricciones de unicidad

- `personal.numero_empleado`
- `equipo.codigo_inventario`
- `equipo.numero_serie`
- `ticket_it.folio_ticket`
- `presupuesto.folio_presupuesto`
- `compra_material.folio_compra`

### 8.2 Integridad referencial

- Uso de claves foráneas en todas las relaciones críticas.
- Uso de `on_delete=CASCADE` en tablas detalle e historiales dependientes.
- Uso de `on_delete=PROTECT` o `SET_NULL` cuando se requiere conservar historial.

## 9. Índices Recomendados

Para mejorar rendimiento en consultas operativas y reportes:

- `equipo(estado_equipo, activo)`
- `equipo(categoria_id)`
- `equipo(ubicacion_id)`
- `movimiento_equipo(fecha_movimiento, tipo_movimiento)`
- `asignacion_equipo(personal_id, estado_asignacion)`
- `mantenimiento(fecha_programada, proxima_fecha_mantenimiento)`
- `ticket_it(estado_ticket, prioridad, fecha_creacion)`
- `ticket_it(personal_solicitante_id)`

## 10. Vistas de Reporteo Recomendadas

1. **vista_inventario_general**
   - Equipos activos con categoría, estado y ubicación.

2. **vista_equipos_asignados**
   - Equipos con asignación activa por empleado.

3. **vista_tickets_abiertos**
   - Tickets en estados `Abierto` y `En Proceso`.

4. **vista_mantenimientos_proximos**
   - Mantenimientos con próximas fechas dentro de una ventana configurable (ej. 30 días).

## 11. Seguridad y Auditoría

- Definir roles de base de datos:
  - `rol_lectura_it` (solo lectura)
  - `rol_operacion_it` (CRUD operativo)
  - `rol_admin_it` (administración)
- En Django, usar grupos y permisos por módulo.
- Mantener trazabilidad de cambios en:
  - `seguimiento_ticket`
  - `movimiento_equipo`
- Configurar respaldos automáticos diarios y política de retención.

## 12. Flujo Operativo Sugerido

1. Alta de catálogos (áreas, categorías, edificios, zonas, proveedores).
2. Registro de equipos y ubicación inicial.
3. Registro de entradas/salidas y asignaciones.
4. Atención y seguimiento de tickets IT.
5. Programación y cierre de mantenimientos.
6. Generación de presupuestos y compras con cálculo automático de totales.

## 13. Glosario

- **Alta:** Creación de un registro nuevo y activo.
- **Baja lógica:** Desactivación de un registro sin eliminarlo físicamente.
- **Ticket:** Solicitud o incidente reportado al área IT.
- **Mantenimiento preventivo:** Servicio programado para evitar fallas.
- **Presupuesto:** Documento económico previo a compra o servicio.

## 14. Control de Cambios del Documento

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| 1.0 | 2026-04-20 | Equipo IT | Versión inicial de documentación de base de datos |
