# Diccionario de datos — Sistema Gestor IT

Esquema actual según Django ORM (`GestorApp/models.py`) y PostgreSQL.

- **Proyecto:** Sistema Gestor IT
- **Motor:** PostgreSQL
- **ORM:** Django 6.0
- **Última revisión:** agosto 2026

Los nombres de tabla en Postgres los genera Django (`gestorapp_*` en minúsculas). Aquí se documentan los **modelos** y sus campos.

Auth: tabla `auth_user` de Django. El rol de negocio está en `auth_group` (`Usuario`, `Tecnico IT`, `Administrador`).

---

## 1. Objetivo

Gestionar el área de TI de una fábrica: inventario unitario, altas/bajas, asignaciones, mantenimiento, tickets, órdenes de compra, gobierno de roles y auditoría.

---

## 2. Módulos cubiertos

1. Catálogos organizacionales
2. Proveedores
3. Ubicación física
4. Inventario, movimientos y asignaciones
5. Mantenimiento y cierres
6. Tickets, seguimientos, bitácora
7. Órdenes de compra y plantillas
8. Historial de actividad
9. Gobierno (coberturas y solicitudes de equipo)

**Fuera del esquema actual:** `Presupuesto`, `DetallePresupuesto`, `CompraMaterial`, `DetalleCompraMaterial`. Esos modelos se unificaron en `OrdenCompra` / `DetalleOrdenCompra`.

---

## 3. Convenciones

- PK autoincremental `id`.
- Bajas lógicas con `activo` donde aplica.
- Estados con `TextChoices` (valores en español en inventario/tickets/mantenimiento).
- Folios automáticos: `SPR0-`, `BIT-`, `OC-`, `PROV-`, `SOL-`, `MAN###-`.
- `ON DELETE`: CASCADE en detalles e historiales dependientes; PROTECT o SET_NULL cuando hay que conservar contexto.

---

## 4. Diccionario

### 4.1 Organización

#### `Area`

| Campo | Tipo | Nulo | Restricción | Descripción |
|-------|------|------|-------------|-------------|
| id | PK | No | auto | Idetificador unico |
| nombre_area | varchar(100) | No | No | Nombre del area |
| descripcion_area | varchar(255) | Sí | No | Descripcion del area |
| activo | boolean | No | default true | En uso o desuso |
| fecha_creacion | timestamptz | No | auto_now_add | |

#### `Puesto`

| Campo | Tipo | Nulo | Restricción | Descripción |
|-------|------|------|-------------|-------------|
| id | PK | No | auto | Identificador |
| nombre_puesto | varchar(100) | No | No | Nombre del puesto |
| descripcion_puesto | varchar(255) | Sí | No | Descripcion general del puesto |
| activo | boolean | No | default true | En uso o desuso |

#### `Personal`

| Campo | Tipo | Nulo | Restricción | Descripción |
|-------|------|------|-------------|-------------|
| id | PK | No | auto | Identificador unico |
| numero_empleado | varchar(30) | No | unique | Numero del empleado |
| user_id | FK User | Sí | SET_NULL, OneToOne | Login ligado |
| admin_requested | boolean | No | default false | Legacy |
| nombre | varchar(100) | No | No | Nombre del empleado |
| apellido_paterno | varchar(100) | No | No | Apellido Paterno del empleado |
| apellido_materno | varchar(100) | Sí | No | Apellido Materno del empleado |
| correo | email | Sí | No | Correo electronico del empleado |
| telefono | varchar(30) | Sí | No | Numero de telefono del empleado |
| area_id | FK Area | Sí | SET_NULL | Identificador de area |
| puesto_id | FK Puesto | Sí | SET_NULL | Identificador de puesto |
| activo | boolean | No | default true | Persona activo o de baja |
| fecha_ingreso | date | Sí | No | Fecha de Ingreso del empleado |
| fecha_creacion | timestamptz | No | auto_now_add | Fecha de creacion del Usuario |

Al borrar Personal se elimina el User ligado (señal).

---

### 4.2 Proveedor

| Campo | Tipo | Nulo | Restricción | Descripción |
|-------|------|------|-------------|-------------|
| id | PK | No | auto | Identificador |
| codigo_interno | varchar(30) | Sí | unique | Auto `PROV-######` |
| nombre_proveedor | varchar(150) | No | | Nombre comercial |
| razon_social | varchar(200) | Sí | No | Nombre de real de la empresa o proveedor ante el SAT |
| rfc | varchar(13) | Sí | No | Registro Federal de Contribuyentes |
| tipo | varchar(30) | Sí | choices | Hardware/Software/… |
| contacto | varchar(150) | Sí | No | Nombre del contacto |
| correo | email | Sí | No | Correo electronico del proveedor |
| telefono | varchar(30) | Sí | No | Telefono del proveedor |
| sitio_web | url | Sí | No | Sitio Web del Proveedor |
| direccion | varchar(255) | Sí | No | Direccion del proveedor |
| ciudad | varchar(100) | Sí | No | Ciudad del proveedor |
| estado | varchar(100) | Sí | No | Estado donde recide |
| codigo_postal | varchar(10) | Sí | No | Codigo postal |
| notas | text | Sí | No | Notas |
| activo | boolean | No | default true | Activo o de baja |

---

### 4.3 Ubicación física

#### `Edificio`

| Campo | Tipo | Nulo | Descripción |
|-------|------|------|-------------|
| id | PK | No | Identificador |
| nombre_edificio | varchar(100) | No | Nombre del edificio |
| descripcion_edificio | varchar(255) | Sí | Descripcion |
| activo | boolean | No | Edificio en uso o desuso |

#### `ZonaEdificio`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No  |
| edificio_id | FK Edificio | No | No |
| nombre_zona | varchar(100) | No | No |
| descripcion_zona | varchar(255) | No | |
| activo | boolean | No | Activo o en desuso |

#### `Ubicacion`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| edificio_id | FK Edificio | No | PROTECT |
| zona_id | FK ZonaEdificio | No | PROTECT |
| pasillo | varchar(50) | Sí | No |
| referencia | varchar(255) | Sí | No |
| activo | boolean | No | default true |

---

### 4.4 Inventario

#### `CategoriaEquipo`

| Campo | Tipo | Nulo |
|-------|------|------|
| id | PK | No |
| nombre_categoria | varchar(100) | No |
| descripcion_categoria | varchar(255) | Sí |
| activo | boolean | No |

#### `Equipo`

| Campo | Tipo | Nulo | Restricción | Descripción |
|-------|------|------|-------------|-------------|
| id | PK | No | auto | Identificador |
| codigo_inventario | varchar(50) | No | unique | Codigo de Inventario del equipo |
| numero_serie | varchar(100) | Sí | unique | Numero de serie |
| categoria_id | FK CategoriaEquipo | No | PROTECT | Identificador de categoria de equipo |
| marca | varchar(80) | Sí | No | Marca del equipo |
| modelo | varchar(80) | Sí | No | Modelo del equipo |
| Numero_Pedimiento | varchar(15) | Sí | | Pedimento / folio OC |
| descripcion_equipo | varchar(255) | Sí | No | Descripcion del equipo |
| imagen | varchar (path) | Sí | | Foto del equipo |
| proveedor_id | FK Proveedor | Sí | SET_NULL | Identificador del proveedor |
| origen_alta | varchar(20) | No | choices | Compra/Legado/Donacion/Transferencia/Otro |
| orden_compra_id | FK OrdenCompra | Sí | SET_NULL | Identificador de orden de compra |
| detalle_orden_id | FK DetalleOrdenCompra | Sí | SET_NULL | Línea que consume cupo |
| estado_equipo | varchar(30) | No | choices | **En Stock** / Asignado / En Mantenimiento / Baja |
| ubicacion_id | FK Ubicacion | Sí | SET_NULL | Ubicacion del equipo |
| fecha_alta | date | No | default hoy | fecha de dada de alta del equipo |
| fecha_baja | date | Sí | No | Fecha de dada de baja |
| motivo_baja | varchar(255) | Sí | No | Motivo de la baja |
| activo | boolean | No | default true | Baja lógica |
| fecha_creacion | timestamptz | No | auto_now_add | Fecha de creacion |

Campos **eliminados** del diseño original: `fecha_compra`, `costo_compra`, `garantia_meses`.

#### `MovimientoEquipo`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| equipo_id | FK Equipo | No | CASCADE |
| tipo_movimiento | varchar(20) | No | Dada de alta/baja, Asignacion, Cambio de asignacion, En mantenimiento, Cambio de ubicacion |
| fecha_movimiento | timestamptz | No | auto_now_add |
| origen | varchar(150) | Sí | No |
| destino | varchar(150) | Sí | No |
| responsable_id | FK Personal | Sí | SET_NULL |
| observaciones | varchar(255) | Sí | No |

Sin campo `cantidad` (inventario unitario).

#### `AsignacionEquipo`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| equipo_id | FK Equipo | No | CASCADE |
| personal_id | FK Personal | No | CASCADE |
| fecha_asignacion | timestamptz | No | auto_now_add |
| fecha_devolucion | timestamptz | Sí | |
| estado_asignacion | varchar(20) | No | Activa / Devuelta / Extraviada |
| observaciones | varchar(255) | Sí | No |

---

### 4.5 Mantenimiento

#### `Mantenimiento`

| Campo | Tipo | Nulo | Descripción |
|-------|------|------|-------------|
| id | PK | No | Folio derivado `MANnnn-MMDDYY` |
| equipo_id | FK Equipo | No | CASCADE |
| tipo_mantenimiento | varchar(20) | No | Preventivo / Correctivo / Predictivo |
| estado_mantenimiento | varchar(20) | No | Programado / En Proceso / Completado / Cancelado |
| fecha_programada | date | No | Fecha programada del mantenimiento |
| tecnico_responsable | varchar(150) | Sí | Texto, no FK |
| costo_mantenimiento | numeric(12,2) | No | default 0 |
| descripcion_falla | varchar(255) | Sí | Descripcion del error |

Fechas reales, acciones y próxima fecha viven en el **cierre**, no en esta tabla.

#### `AgendaMantenimiento` (cierre)

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| mantenimiento_id | FK Mantenimiento | No | OneToOne CASCADE, related `cierre` |
| fecha_inicio | timestamptz | Sí | No |
| fecha_fin | timestamptz | Sí | No |
| acciones_realizadas | text | Sí | |
| observaciones | varchar(255) | Sí | No |
| proxima_fecha_mantenimiento | date | Sí | Próximo ciclo |

Campos **eliminados:** `fecha_recordatorio`, `canal_recordatorio`, `enviado`.

---

### 4.6 Soporte

#### `TicketIT`

| Campo | Tipo | Nulo | Restricción | Descripción |
|-------|------|------|-------------|-------------|
| id | PK | No | | |
| folio_ticket | varchar(30) | No | unique | Auto `SPR0-######` |
| fecha_support | timestamptz | No | default now | Inicio SLA |
| requerimiento | varchar(180) | No | No | Titulo para el ticket o problema |
| area_id | FK Area | Sí | SET_NULL | Identificador de area |
| puesto_id | FK Puesto | Sí | SET_NULL | Identificador de puesto |
| solicitado_por_id | FK User | Sí | SET_NULL | identificador de usuario |
| asignado_a_id | FK User | Sí | SET_NULL | Técnico |
| tipo_ticket | varchar(30) | No | choices | HELPDESK, HARDWARE, … |
| sub_tipo_ticket | varchar(150) | Sí | No | Catálogo en forms |
| prioridad | varchar(10) | No | Baja/Media/Alta/Urgente | Prioridad de atencion |
| equipo_id | FK Equipo | Sí | SET_NULL | Identificador de equipo |
| tipo_equipo_id | FK CategoriaEquipo | Sí | PROTECT | Tipo de equipo |
| otro_tipo_equipo | varchar(120) | Sí | | Si categoría “Otro” |
| detalle | varchar(255) | Sí | No | Detalles del problema |
| descripcion | text | No | No | Descripcion completa del problema |
| imagen | path | Sí | | `media/support/` |
| status | varchar(20) | No | Abierto / En Revision / En Proceso / Cerrado | Automático |

#### `SeguimientoTicket`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| ticket_id | FK TicketIT | No | CASCADE |
| folio_check | varchar(30) | Sí | = folio del ticket |
| fecha_check | timestamptz | No | No |
| avance_realizado | text | Sí | No |
| pendiente | text | Sí | No |
| proximo_paso | text | Sí | No |
| fecha_proximo_seguimiento | date | Sí | Avisos home |
| usuario_id | FK User | Sí | SET_NULL |
| solucion | text | No | Obligatoria si ya_terminado |
| observacion | text | Sí | No |
| ya_terminado | boolean | No | default false |

#### `Bitacora`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| folio_bitacora | varchar(30) | No | unique, auto `BIT-######` |
| fecha_bitacora | timestamptz | No | No |
| situacion | varchar(180) | No | No |
| descripcion_situacion | text | No | No |

#### `Answer`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| bitacora_id | FK Bitacora | No | CASCADE |
| folio_answer | varchar(30) | No | = folio bitácora |
| fecha_answer | timestamptz | No | No |
| solucion | varchar(180) | No | No |
| descripcion_solucion | text | No | No |
| usuario_id | FK User | Sí | SET_NULL |

---

### 4.7 Compras

#### `PlantillaDocumento`

| Campo | Tipo | Nulo |
|-------|------|------|
| id | PK | No |
| nombre | varchar(150) | No |
| descripcion | varchar(255) | Sí |
| tipo_archivo | varchar(10) | DOCX / XLSX / PDF |
| archivo | path | `media/plantillas_orden_compra/` |
| campos | json | Lista de placeholders |
| activo | boolean | No |
| creado_en | timestamptz | No |

#### `OrdenCompra`

| Campo | Tipo | Nulo | Restricción | Descripción |
|-------|------|------|-------------|-------------|
| id | PK | No | No | Identificador |
| folio_orden | varchar(30) | No | unique | Auto `OC-######` |
| elaborado_por_id | FK User | Sí | SET_NULL | Dueño para alcance Usuario |
| origen | varchar(10) | No | CREADO / SUBIDO | Si el archivo se creara o solamente se subira |
| fecha | date | Sí | No | Fecha de creacion |
| proveedor_id | FK Proveedor | Sí | SET_NULL | Obligatorio si CREADO |
| tipo_moneda | varchar(3) | No | MXN / USD | Tipo de moneda |
| iva_opcion | varchar(4) | No | 8 / 16 / OTRO | Iva |
| iva_porcentaje | numeric(5,2) | No | default 16 | Porcentaje de Iva |
| subtotal | numeric(14,2) | No | No | Recalculado |
| iva_monto | numeric(14,2) | No | No | Monto de Iva |
| total | numeric(14,2) | No | No | Total |
| comentarios | text | Sí | No | Comentarios |
| notas | varchar(255) | Sí | No | Notas |
| estado | varchar(30) | No | Borrador / En Proceso / Terminado / Cancelado | Estado de la orden |
| archivo_pdf | path | Sí | | `media/ordenes_compra/` |
| plantilla_id | FK PlantillaDocumento | Sí | SET_NULL | Identificador de plantilla |
| creado_en | timestamptz | No | auto_now_add | Tipo de creacion |

#### `DetalleOrdenCompra`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| orden_id | FK OrdenCompra | No | CASCADE |
| id_producto | varchar(80) | Sí | No |
| descripcion | varchar(255) | No | No |
| cantidad | numeric(10,2) | No | default 1 |
| precio_unitario | numeric(12,2) | No | default 0 |
| importe | numeric(14,2) | No | cantidad × precio |

Cupo inventario: parte entera de `cantidad` menos equipos con `detalle_orden_id` = esta línea.

---

### 4.8 Historial

#### `HistorialActividad`

| Campo | Tipo | Nulo | Notas |
|-------|------|------|-------|
| id | PK | No | Identificador |
| fecha | timestamptz | No | index |
| modulo | varchar(32) | No | index; ver MODELS.md |
| accion | varchar(24) | No | index |
| nivel | varchar(16) | No | info / advertencia / critico |
| es_automatico | boolean | No | Si o no |
| usuario_id | FK User | Sí | SET_NULL |
| titulo | varchar(200) | No | Titulo |
| descripcion | text | No | blank ok |
| objeto_tipo / objeto_id / objeto_etiqueta | Varchar | Sí | Tipo de Objeto |
| entidad_relacionada_* | | Sí | Contexto padre |
| enlace_nombre / enlace_pk | | Sí | Deep-link UI |
| metadata | json | Sí | |
| archivado | boolean | No | index |
| fecha_archivado | timestamptz | Sí | fecha en que fue archivado |

Retención: `HISTORIAL_RETENCION` (activo 180 d → archivo 365 d → purga; críticos protegidos).

---

### 4.9 Gobierno

#### `CoberturaTickets`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| ausente_id | FK User | No | CASCADE |
| suplente_id | FK User | No | CASCADE |
| fecha_inicio | date | No | No |
| fecha_fin | date | No | ≥ inicio |
| activa | boolean | No | default true |
| motivo | varchar(255) | No | blank ok |
| creado_por_id | FK User | Sí | SET_NULL |
| fecha_creacion | timestamptz | No | No |

#### `SolicitudEquipo`

| Campo | Tipo | Nulo | Restricción |
|-------|------|------|-------------|
| id | PK | No | No |
| folio | varchar(30) | No | unique, auto `SOL-000001` |
| solicitante_id | FK User | No | CASCADE |
| personal_id | FK Personal | Sí | SET_NULL |
| categoria_id | FK CategoriaEquipo | Sí | SET_NULL |
| titulo | varchar(160) | No | No |
| justificacion | text | No | No |
| urgencia | varchar(10) | No | Baja / Media / Alta |
| estado | varchar(20) | No | Pendiente / En revision / Aprobada / Rechazada / Completada / Cancelada |
| notas_solicitante | varchar(255) | No | blank |
| notas_it | text | No | blank |
| revisado_por_id | FK User | Sí | SET_NULL |
| equipo_id | FK Equipo | Sí | SET_NULL |
| fecha_creacion | timestamptz | No | No |
| fecha_actualizacion | timestamptz | No | No |
| fecha_resolucion | timestamptz | Sí | No |

#### `SeguimientoSolicitudEquipo`

| Campo | Tipo | Nulo |
|-------|------|------|
| id | PK | No |
| solicitud_id | FK SolicitudEquipo | No, CASCADE |
| fecha_check | timestamptz | No |
| avance_realizado / pendiente / proximo_paso | text | Sí |
| fecha_proximo_seguimiento | date | Sí |
| usuario_id | FK User | Sí |
| solucion | text | blank |
| observacion | text | Sí |
| ya_terminado | boolean | No |

---

## 5. Reglas de negocio (persistidas en código)

1. Asignación **Activa** → equipo **Asignado**. Devolución → **En Stock** (si no está Baja / En Mantenimiento).
2. Iniciar mantenimiento → equipo **En Mantenimiento**. Completar/cancelar restaura En Stock o Asignado si no hay otro En Proceso.
3. Ticket: el status lo mueven seguimientos y acciones de flujo, no el formulario.
4. OC: `importe` de línea = cantidad × precio; cabecera recalcula subtotal/IVA/total.
5. Alta origen Compra exige OC **Terminado** + línea con cupo > 0.
6. Folios únicos: `numero_empleado`, `codigo_inventario`, `numero_serie`, `folio_ticket`, `folio_bitacora`, `folio_orden`, `codigo_interno` de proveedor, `folio` de solicitud.

---

## 6. Integridad

| Relación | on_delete |
|----------|-----------|
| Detalles de OC, seguimientos, answers, movimientos, asignaciones, mantenimientos, revisiones de solicitud | CASCADE |
| Categoría de equipo, ubicación (edificio/zona en Ubicacion) | PROTECT |
| User en tickets/OC/historial, proveedor en equipo | SET_NULL |
| Zona al borrar edificio | CASCADE (zonas) |

---

## 7. Índices relevantes

- `HistorialActividad`: fecha, modulo, accion, nivel, es_automatico, archivado
- `SolicitudEquipo.estado`
- Uniques listados en la sección 5

Consultas operativas típicas (equipo por estado, tickets por status/prioridad, asignaciones activas) se filtran en vistas; no hay índices compuestos extra en el modelo de equipo/ticket.

---

## 8. Control de cambios

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| 1.0 | 2026-04-20 | Esquema inicial (incluye presupuestos/compras materiales) |
| 2.0 | 2026-08 | Alineado al código: OC unificada, gobierno, historial, bitácora, SLA, En Stock, cierres |
