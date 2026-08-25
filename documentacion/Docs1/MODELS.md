# Modelos Django — Sistema Gestor IT

Fuente de verdad: `GestorApp/models.py`. Auth usa `django.contrib.auth.User` (sin `AUTH_USER_MODEL` propio).

**Última revisión:** agosto 2026.

---

## Tabla de contenidos

1. [Organización](#1-organización)
2. [Proveedores](#2-proveedores)
3. [Ubicaciones](#3-ubicaciones)
4. [Inventario](#4-inventario)
5. [Mantenimiento](#5-mantenimiento)
6. [Tickets, bitácora y answers](#6-tickets-bitácora-y-answers)
7. [Órdenes de compra](#7-órdenes-de-compra)
8. [Historial de actividad](#8-historial-de-actividad)
9. [Gobierno](#9-gobierno)
10. [Relaciones](#10-relaciones)
11. [Señales y managers](#11-señales-y-managers)

---

## 1. Organización

### `Area`

| Campo | Tipo | Notas |
|-------|------|-------|
| `nombre_area` | CharField(100) | |
| `descripcion_area` | CharField(255) | blank/null |
| `activo` | Boolean | default True |
| `fecha_creacion` | DateTime | auto_now_add |

### `Puesto`

| Campo | Tipo | Notas |
|-------|------|-------|
| `nombre_puesto` | CharField(100) | |
| `descripcion_puesto` | CharField(255) | blank/null |
| `activo` | Boolean | default True |

### `Personal`

Perfil laboral ligado a una cuenta.

| Campo | Tipo | Notas |
|-------|------|-------|
| `numero_empleado` | CharField(30) | **unique** |
| `user` | OneToOne → User | `SET_NULL`, `related_name='personal_profile'` |
| `admin_requested` | Boolean | Legacy; el signup ya no lo usa |
| `nombre`, `apellido_paterno` | CharField(100) | |
| `apellido_materno` | CharField(100) | blank/null |
| `correo` | EmailField | blank/null |
| `telefono` | CharField(30) | blank/null |
| `area` | FK Area | `SET_NULL` |
| `puesto` | FK Puesto | `SET_NULL` |
| `activo` | Boolean | default True |
| `fecha_ingreso` | Date | blank/null |
| `fecha_creacion` | DateTime | auto_now_add |

El **rol de negocio** no vive aquí: está en Groups del `User` (`Usuario`, `Tecnico IT`, `Administrador`). Ver `ROLES.md`.

---

## 2. Proveedores

### `TipoProveedor`

Hardware, Software, Mantenimiento, Telecomunicaciones, Consumibles, Otro.

### `Proveedor`

| Campo | Tipo | Notas |
|-------|------|-------|
| `codigo_interno` | CharField(30) | unique, auto `PROV-######` al guardar |
| `nombre_proveedor` | CharField(150) | Nombre comercial |
| `razon_social` | CharField(200) | blank/null |
| `rfc` | CharField(13) | blank/null |
| `tipo` | choices TipoProveedor | blank/null |
| `contacto`, `correo`, `telefono` | | blank/null |
| `sitio_web` | URLField | blank/null |
| `direccion`, `ciudad`, `estado`, `codigo_postal` | | blank/null |
| `notas` | TextField | blank/null |
| `activo` | Boolean | default True |

Meta: `ordering = nombre_proveedor`.

---

## 3. Ubicaciones

Jerarquía: **Edificio → ZonaEdificio → Ubicacion**.

| Modelo | Campos clave | Relación |
|--------|--------------|----------|
| `Edificio` | `nombre_edificio`, `descripcion_edificio`, `activo` | Independiente |
| `ZonaEdificio` | `nombre_zona`, `descripcion_zona`, `activo` | FK `edificio` **CASCADE**, `related_name='zonas'` |
| `Ubicacion` | `pasillo`, `referencia`, `activo` | FK `edificio` **PROTECT**, FK `zona` **PROTECT** |

`Equipo.ubicacion` apunta a `Ubicacion`.

---

## 4. Inventario

### `CategoriaEquipo`

`nombre_categoria`, `descripcion_categoria`, `activo`.

### `EstadoEquipo`

Valores persistidos (español):

| Constante | Valor en BD |
|-----------|-------------|
| `DISPONIBLE` | **En Stock** |
| `ASIGNADO` | Asignado |
| `EN_MANTENIMIENTO` | En Mantenimiento |
| `BAJA` | Baja |

No existe el valor `"Disponible"` en BD.

### `OrigenAltaEquipo`

Compra (con OC), Legado / histórico (default), Donacion, Transferencia, Otro.

### `Equipo`

Activo unitario (una fila = una pieza).

| Campo | Tipo | Notas |
|-------|------|-------|
| `codigo_inventario` | CharField(50) | unique |
| `numero_serie` | CharField(100) | unique, blank/null |
| `categoria` | FK CategoriaEquipo | **PROTECT** |
| `marca`, `modelo` | CharField(80) | blank/null |
| `Numero_Pedimiento` | CharField(15) | blank/null (nombre de campo en el modelo) |
| `descripcion_equipo` | CharField(255) | blank/null |
| `imagen` | ImageField | path seguro `media/equipos/` |
| `proveedor` | FK Proveedor | `SET_NULL` |
| `origen_alta` | choices | default Legado |
| `orden_compra` | FK OrdenCompra | `SET_NULL`, `related_name='equipos'` |
| `detalle_orden` | FK DetalleOrdenCompra | `SET_NULL`; consume cupo de la línea |
| `estado_equipo` | choices | default En Stock |
| `ubicacion` | FK Ubicacion | `SET_NULL` |
| `fecha_alta` | Date | default now |
| `fecha_baja`, `motivo_baja` | | blank/null |
| `activo` | Boolean | default True |
| `fecha_creacion` | DateTime | auto_now_add |

**Propiedades de negocio:** `asignacion_activa`, `puede_asignarse`, `puede_devolver`, `puede_dar_de_baja`, `puede_reactivar`, `puede_cambiar_ubicacion`, `puede_eliminar_fisico`.

Borrado físico solo si no hay asignaciones, mantenimientos, tickets ni movimientos distintos de “Dada de alta”.

### `TipoMovimiento`

Dada de alta, Dada de baja, Asignacion de equipo, Cambio de asignacion, En mantenimiento, Cambio de ubicacion.

### `MovimientoEquipo`

Bitácora del activo.

| Campo | Tipo | Notas |
|-------|------|-------|
| `equipo` | FK Equipo | CASCADE, `related_name='movimientos'` |
| `tipo_movimiento` | choices | |
| `fecha_movimiento` | DateTime | auto_now_add |
| `origen`, `destino` | CharField(150) | blank/null |
| `responsable` | FK Personal | `SET_NULL` |
| `observaciones` | CharField(255) | blank/null |

No hay campo `cantidad` (se eliminó; el inventario es unitario).

### `EstadoAsignacion`

Activa, Devuelta, Extraviada.

### `AsignacionEquipo`

| Campo | Tipo | Notas |
|-------|------|-------|
| `equipo` | FK Equipo | CASCADE, `related_name='asignaciones'` |
| `personal` | FK Personal | CASCADE, `related_name='equipos_asignados'` |
| `fecha_asignacion` | DateTime | auto_now_add |
| `fecha_devolucion` | DateTime | blank/null |
| `estado_asignacion` | choices | default Activa |
| `observaciones` | CharField(255) | blank/null |

La unicidad “máx. 1 Activa por equipo” se aplica en lógica de aplicación, no como constraint de BD.

---

## 5. Mantenimiento

### `TipoMantenimiento`

Preventivo, Correctivo, Predictivo.

### `EstadoMantenimiento`

Programado, En Proceso, Completado, Cancelado.

### `Mantenimiento`

| Campo | Tipo | Notas |
|-------|------|-------|
| `equipo` | FK Equipo | CASCADE, `related_name='mantenimientos'` |
| `tipo_mantenimiento` | choices | |
| `estado_mantenimiento` | choices | default Programado |
| `fecha_programada` | Date | |
| `tecnico_responsable` | CharField(150) | Texto (no FK) |
| `costo_mantenimiento` | Decimal(12,2) | default 0 |
| `descripcion_falla` | CharField(255) | blank/null |

Folio: `folio_mantenimiento()` → `MAN{pk:03d}-{MMDDYY}`.

Métodos: `iniciar()`, `cancelar()`, `marcar_completado()`, `reabrir()`.  
Propiedades: `tiene_cierre`, `puede_iniciar`, `puede_cancelar`, `puede_completar`, `puede_reabrir`.

### `AgendaMantenimiento`

Cierre de la orden (en UI se llama **Cierre**; en código/URLs sigue `AgendaMantenimiento`).

| Campo | Tipo | Notas |
|-------|------|-------|
| `mantenimiento` | OneToOne | CASCADE, `related_name='cierre'` |
| `fecha_inicio`, `fecha_fin` | DateTime | blank/null |
| `acciones_realizadas` | Text | blank/null |
| `observaciones` | CharField(255) | blank/null |
| `proxima_fecha_mantenimiento` | Date | blank/null; alimenta el próximo ciclo |

No hay `canal_recordatorio` ni `enviado` (se quitaron).

---

## 6. Tickets, bitácora y answers

### Choices de soporte

| Enum | Valores |
|------|---------|
| `TipoTicketSupport` | ADMINISTRACION, BPCS, HARDWARE, HELPDESK, TELEFONIA, SOFTWARE, MANTENIMIENTO |
| `EstadoSupport` | Abierto, En Revision, En Proceso, Cerrado |
| `PrioridadSupport` | Baja, Media, Alta, Urgente |

`TipoEquipoSupport` existe en código pero **no** se usa en `TicketIT`: el tipo de equipo es FK a `CategoriaEquipo`.

### SLA (`SLA_HORAS_POR_PRIORIDAD`)

Horas **calendario** desde `fecha_support`: Urgente 4, Alta 24, Media 72, Baja 168.

### `TicketIT`

| Campo | Tipo | Notas |
|-------|------|-------|
| `folio_ticket` | CharField(30) | unique, auto `SPR0-######` |
| `fecha_support` | DateTime | default now |
| `requerimiento` | CharField(180) | |
| `area` | FK Area | `SET_NULL` |
| `puesto` | FK Puesto | `SET_NULL` |
| `solicitado_por` | FK User | `SET_NULL` |
| `asignado_a` | FK User | `SET_NULL` (técnico operativo) |
| `tipo_ticket` | choices | default HELPDESK |
| `sub_tipo_ticket` | CharField(150) | blank/null; opciones en `forms/common.py` |
| `prioridad` | choices | default Media |
| `equipo` | FK Equipo | `SET_NULL` |
| `tipo_equipo` | FK CategoriaEquipo | PROTECT, null |
| `otro_tipo_equipo` | CharField(120) | si categoría = “Otro” |
| `detalle` | CharField(255) | blank/null |
| `descripcion` | Text | |
| `imagen` | ImageField | un adjunto; `media/support/` |
| `status` | choices | default Abierto; **no se edita a mano** |

**Flujo (`refresh_status_from_followups`):**

- Sin seguimientos: Abierto, o En Revision si ya se tomó.
- Último check `ya_terminado=False` → En Proceso.
- Último check `ya_terminado=True` → Cerrado (exige `solucion`).

Métodos: `marcar_en_revision()`, `reabrir()` (crea un check de reapertura).  
SLA: `sla_horas_objetivo`, `sla_fecha_limite`, `sla_vencido`, `sla_estado` (`ok` / `por_vencer` / `vencido` / `cerrado`).

### `SeguimientoTicket`

| Campo | Tipo | Notas |
|-------|------|-------|
| `ticket` | FK TicketIT | CASCADE, `related_name='seguimientos'` |
| `folio_check` | CharField(30) | se sincroniza con el folio del ticket |
| `fecha_check` | DateTime | default now |
| `avance_realizado`, `pendiente`, `proximo_paso` | Text | blank/null |
| `fecha_proximo_seguimiento` | Date | avisos en home |
| `usuario` | FK User | `SET_NULL` |
| `solucion` | Text | default `''`; obligatoria si `ya_terminado` |
| `observacion` | Text | blank/null |
| `ya_terminado` | Boolean | default False |

Al guardar/borrar se llama `ticket.refresh_status_from_followups()`.

### `Bitacora`

Registro operativo paralelo (no es un ticket). Folio auto `BIT-######`.

| Campo | Tipo |
|-------|------|
| `folio_bitacora` | unique |
| `fecha_bitacora` | DateTime |
| `situacion` | CharField(180) |
| `descripcion_situacion` | Text |

No se elimina si tiene respuestas (`puede_eliminar`).

### `Answer`

Respuesta a una bitácora. Folio copiado del `BIT-` padre.

| Campo | Tipo |
|-------|------|
| `bitacora` | FK CASCADE, `related_name='answers'` |
| `folio_answer` | sincronizado |
| `fecha_answer` | DateTime |
| `solucion` | CharField(180) |
| `descripcion_solucion` | Text |
| `usuario` | FK User SET_NULL |

---

## 7. Órdenes de compra

Reemplazan a los antiguos `Presupuesto` / `CompraMaterial`. Alias legacy: `EstadoPresupuesto = EstadoOrdenCompra`.

### Choices

| Enum | Valores |
|------|---------|
| `EstadoOrdenCompra` | Borrador, En Proceso, Terminado, Cancelado |
| `OrigenOrdenCompra` | CREADO, SUBIDO |
| `TipoMoneda` | MXN, USD |
| `IvaOpcion` | 8, 16, OTRO |
| `TipoPlantillaDocumento` | DOCX, XLSX, PDF |

### `PlantillaDocumento`

| Campo | Tipo | Notas |
|-------|------|-------|
| `nombre` | CharField(150) | |
| `descripcion` | CharField(255) | blank/null |
| `tipo_archivo` | choices | |
| `archivo` | FileField | `media/plantillas_orden_compra/` |
| `campos` | JSONField | placeholders detectados |
| `activo` | Boolean | |
| `creado_en` | DateTime | auto_now_add |

### `OrdenCompra`

Folio auto `OC-######`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `folio_orden` | unique | |
| `elaborado_por` | FK User | `SET_NULL` |
| `origen` | CREADO / SUBIDO | |
| `fecha` | Date | |
| `proveedor` | FK Proveedor | `SET_NULL`; obligatorio si CREADO |
| `tipo_moneda` | MXN/USD | |
| `iva_opcion`, `iva_porcentaje` | | |
| `subtotal`, `iva_monto`, `total` | Decimal | recalculados |
| `comentarios`, `notas` | | |
| `estado` | choices | default Borrador |
| `archivo_pdf` | FileField | `media/ordenes_compra/` |
| `plantilla` | FK PlantillaDocumento | `SET_NULL` |
| `creado_en` | DateTime | auto_now_add |

Helpers: `lista_para_inventario`, `puede_recibir_equipos`, `recalcular_totales()`.

### `DetalleOrdenCompra`

| Campo | Tipo | Notas |
|-------|------|-------|
| `orden` | FK OrdenCompra | CASCADE, `related_name='detalles'` |
| `id_producto` | CharField(80) | blank/null |
| `descripcion` | CharField(255) | |
| `cantidad` | Decimal(10,2) | |
| `precio_unitario` | Decimal(12,2) | |
| `importe` | Decimal(14,2) | cantidad × precio |

`cantidad_disponible()` = parte entera de `cantidad` − equipos ligados a esa línea.

---

## 8. Historial de actividad

### Choices

| Enum | Valores |
|------|---------|
| `ModuloHistorial` | ticket, seguimiento, equipo, asignacion, movimiento_equipo, personal, mantenimiento, orden_compra, bitacora, sistema, gobierno, solicitud_equipo |
| `AccionHistorial` | creacion, actualizacion, eliminacion, cambio_estado, asignacion, devolucion, otro |
| `NivelHistorial` | info, advertencia, critico |

### `HistorialActividad`

| Campo | Notas |
|-------|-------|
| `fecha` | index |
| `modulo`, `accion`, `nivel` | index |
| `es_automatico` | True si lo generó el sistema |
| `usuario` | FK User SET_NULL |
| `titulo`, `descripcion` | |
| `objeto_tipo`, `objeto_id`, `objeto_etiqueta` | objeto afectado |
| `entidad_relacionada_*` | contexto padre (ticket de un check, etc.) |
| `enlace_nombre`, `enlace_pk` | deep-link en UI |
| `metadata` | JSON |
| `archivado`, `fecha_archivado` | retención |

API de escritura: `GestorApp/historial.py`. Política: `HISTORIAL_RETENCION` en settings.

---

## 9. Gobierno

### `CoberturaTickets`

Delegación: suplente atiende tickets del ausente.

| Campo | Tipo |
|-------|------|
| `ausente`, `suplente` | FK User CASCADE |
| `fecha_inicio`, `fecha_fin` | Date |
| `activa` | Boolean |
| `motivo` | CharField(255) blank |
| `creado_por` | FK User SET_NULL |
| `fecha_creacion` | auto_now_add |

Validación: ausente ≠ suplente; fin ≥ inicio. Propiedad `vigente_hoy`.

### `EstadoSolicitudEquipo`

Pendiente, En revision, Aprobada, Rechazada, Completada, Cancelada.

### `UrgenciaSolicitudEquipo`

Baja, Media, Alta.

### `SolicitudEquipo`

Folio auto `SOL-{pk:06d}`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `folio` | unique | se asigna tras el primer save |
| `solicitante` | FK User | CASCADE |
| `personal` | FK Personal | SET_NULL; destino de la asignación |
| `categoria` | FK CategoriaEquipo | SET_NULL |
| `titulo` | CharField(160) | |
| `justificacion` | Text | |
| `urgencia` | choices | default Media |
| `estado` | choices | default Pendiente |
| `notas_solicitante` | CharField(255) | blank |
| `notas_it` | Text | blank |
| `revisado_por` | FK User | SET_NULL |
| `equipo` | FK Equipo | SET_NULL; al completar |
| `fecha_creacion` | auto_now_add | |
| `fecha_actualizacion` | auto_now | |
| `fecha_resolucion` | DateTime | blank/null |

### `SeguimientoSolicitudEquipo`

Hilo **Revision IT** (misma forma que un check de ticket).

Al guardar, si la solicitud está **Pendiente**, pasa a **En revision**.

---

## 10. Relaciones

```
User ──1:1── Personal ── Area, Puesto
User ──────── TicketIT (solicitado_por / asignado_a)
User ──────── OrdenCompra.elaborado_por
User ──────── CoberturaTickets, SolicitudEquipo

Edificio ── ZonaEdificio ── Ubicacion ── Equipo

Proveedor ── Equipo
Proveedor ── OrdenCompra
CategoriaEquipo ── Equipo, TicketIT.tipo_equipo, SolicitudEquipo

OrdenCompra ── DetalleOrdenCompra ── Equipo (cupo)
PlantillaDocumento ── OrdenCompra

Equipo ── AsignacionEquipo ── Personal
Equipo ── MovimientoEquipo
Equipo ── Mantenimiento ── AgendaMantenimiento (cierre 1:1)
Equipo ── TicketIT ── SeguimientoTicket

Bitacora ── Answer
SolicitudEquipo ── SeguimientoSolicitudEquipo
HistorialActividad ── (cualquier módulo, por referencia)
```

---

## 11. Señales y managers

- **Señal** `post_delete` en `Personal`: borra el `User` ligado.
- **Hook** `post_migrate` en `apps.py`: registra schedules de django-q2.
- No hay managers custom.

Índices explícitos en `HistorialActividad` (`fecha`, `modulo`, `accion`, `nivel`, `es_automatico`, `archivado`) y `SolicitudEquipo.estado`.

---

## Documentación relacionada

| Documento | Enfoque |
|-----------|---------|
| `DocModels.md` | Diccionario de tablas/campos |
| `INVENTARIO.md` | Ciclo de vida del equipo |
| `TICKETS.md` | Flujo y SLA |
| `MANTENIMIENTO.md` | Órdenes y cierres |
| `ROLES.md` | Groups y permisos |
| `MODULOS.md` | Arquitectura y archivos |
