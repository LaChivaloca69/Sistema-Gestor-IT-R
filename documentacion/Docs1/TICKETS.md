# Tickets y Seguimiento — Guía de funcionamiento

Documento de **Tickets (Support)** y **Seguimiento (Checks)**. **Última revisión:** agosto 2026.

---

## 1. Resumen

Se reforzó el ciclo de vida del ticket, la experiencia de uso, los permisos por rol, los avisos operativos en home/dashboard (sin email) y un panel de operación con SLA por prioridad.

| Área | Qué se hizo |
|------|-------------|
| Flujo y estados | Status automático, En Revisión usable, reabrir, asignado |
| UX Tickets | Detalle, timeline, búsqueda, Mis tickets, paginación |
| UX Seguimiento | Filtros, avisos de próximo check en home |
| Permisos | Solicitante vs operativo; borrado de ticket/check solo Admin |
| SLA y operación | Tiempos por prioridad + dashboard operativo |

**Importante:** las notificaciones son solo avisos en **home** y **dashboard**. No se envía correo.

---

## 2. Conceptos

### Ticket (`TicketIT`)
Solicitud de soporte. Folio automático `SPR0-######`.

### Seguimiento / Check (`SeguimientoTicket`)
Avance sobre un ticket. El último check define si el ticket sigue en proceso o se cierra (`ya_terminado`).

### Roles
| Rol | Quién |
|-----|--------|
| Solicitante | Usuario autenticado (rol **Usuario**) |
| Operativo | **Tecnico IT** o **Administrador** (`is_operativo`) |

El criterio ya **no** es `is_staff`. Ver `ROLES.md`.

---

## 3. Flujo de estados

Estados: **Abierto** → **En Revision** → **En Proceso** → **Cerrado** (y reabrir).

```
Abierto
   │  Operativo marca En Revision / asigna técnico
   ▼
En Revision
   │  Se registra el primer seguimiento
   ▼
En Proceso
   │  Seguimiento con “Concluido” + solución
   ▼
Cerrado
   │  Operativo reabre (crea check de reapertura)
   ▼
En Proceso
```

### Reglas automáticas
- Sin seguimientos: **Abierto**, o **En Revision** si ya se tomó el ticket.
- Último seguimiento no concluido: **En Proceso**.
- Último seguimiento concluido (`ya_terminado`): **Cerrado**.
- El campo **Estado no se edita a mano** en el formulario; lo mueven seguimientos y acciones de flujo.

### Acciones de operativo
- **Marcar En Revision:** solo si está Abierto y sin checks. Si no hay asignado, se asigna al usuario actual.
- **Reabrir:** solo si está Cerrado. Crea un seguimiento de reapertura y deja el ticket en En Proceso.
- **Asignado a:** usuario operativo (Técnico o Admin). Si el ticket está Abierto y se asigna, pasa a En Revision.

### Cierre
Para marcar un seguimiento como **Concluido**, la **solución es obligatoria**.

---

## 4. UX de Tickets

### Lista (`/Ticketit/`)
- Búsqueda: folio, problema, descripción, equipo, usuarios.
- Vista: Todos / Mis tickets / Asignados a mí (operativo). Solicitante solo ve los suyos.
- Filtros: tipo, prioridad, estatus, operación (SLA), sin seguimiento.
- Columna **SLA** (En tiempo / Por vencer / Vencido).
- Paginación (20).
- Enlace a **Dashboard**.

### Detalle (`/Ticketit/<id>/`)
- Datos del ticket, imagen, SLA y límite.
- Timeline de seguimientos.
- Operativo: agregar seguimiento embebido, marcar revisión, reabrir.
- Botones Editar / Eliminar según permisos.

### Formulario crear/editar
- Status fuera del form (automático).
- Solicitante: `solicitado_por` fijo; no asigna técnico.
- Operativo: puede asignar `asignado_a`.
- Tras guardar → detalle del ticket.

---

## 5. UX de Seguimiento

### Lista (`/SeguimientoTickets/`) — solo operativo
- Búsqueda, Mis checks, estado del ticket, concluido.
- Avisos: Por atender / Vencidos / Por vencer (según `fecha_proximo_seguimiento`).
- Enlace al detalle del ticket.
- Paginación.

### Avisos en home (operativo)
Si un check:
- no está concluido,
- tiene `fecha_proximo_seguimiento`,
- y el ticket no está cerrado,

entonces:
- fecha pasada → **Vencido**
- dentro de 7 días → **Por vencer**

Aparecen en KPI, banners y panel del home. **Sin email.**

---

## 6. Permisos

| Acción | Solicitante (Usuario) | Operativo | Admin |
|--------|-----------------------|-----------|-------|
| Ver | Solo los suyos (`solicitado_por`) | Todos | Todos |
| Crear | Sí | Sí | Sí |
| Editar | Solo si está **Abierto** y **sin checks** | Sí | Sí |
| Eliminar ticket | No | No | Solo **sin seguimientos** |
| Flujo (revisión / reabrir) | No | Sí | Sí |
| Crear/editar checks | No | Sí | Sí |
| Borrar checks | No | No | Sí |

### Detalles
- Intento de ver/editar un ticket ajeno → bloqueado con mensaje.
- Ticket con seguimientos → no se elimina; hay que quitar los checks primero.
- Home y calendario del solicitante: solo sus tickets.
- Lista de seguimientos: `operativo_required`. Borrado de checks: `admin_required`.

---

## 7. SLA por prioridad (punto 18)

Tiempo objetivo desde `fecha_support` (horas calendario):

| Prioridad | Horas SLA |
|-----------|-----------|
| Urgente | 4 |
| Alta | 24 |
| Media | 72 |
| Baja | 168 (7 días) |

### Estados SLA (tickets no cerrados)
- **En tiempo:** lejos del límite.
- **Por vencer:** cerca del límite (menor entre 4 h y 25 % del SLA).
- **Vencido:** ya pasó el límite.

Definido en `GestorApp/models.py` como `SLA_HORAS_POR_PRIORIDAD`.  
Avisos en home/lista/dashboard; **sin email**.

---

## 8. Dashboard de tickets (punto 19)

Ruta: `/Ticketit/dashboard/`

También en sidebar (**Dashboard**) y accesos rápidos del home.

### Contenido
- KPI: activos, SLA vencidos, SLA por vencer, sin seguimiento.
- Tabla SLA por prioridad (horas + conteo).
- Conteos por estado y por tipo (con enlaces filtrados).
- Listas: tickets fuera de SLA y tickets sin checks.

Los conteos respetan permisos: el solicitante ve solo lo suyo; operativo ve el total operativo.

---

## 9. Rutas principales

| Ruta | Nombre | Quién |
|------|--------|--------|
| `/Ticketit/` | `ticketit_list` | Autenticado (scoped) |
| `/Ticketit/dashboard/` | `ticketit_dashboard` | Autenticado (scoped) |
| `/Ticketit/create/` | `ticketit_create` | Autenticado |
| `/Ticketit/<id>/` | `ticketit_detail` | Dueño u operativo |
| `/Ticketit/update/<id>/` | `ticketit_update` | Según permisos de edición |
| `/Ticketit/delete/<id>/` | `ticketit_delete` | Admin, sin checks |
| `/Ticketit/<id>/marcar-revision/` | `ticketit_marcar_revision` | Operativo |
| `/Ticketit/<id>/reabrir/` | `ticketit_reabrir` | Operativo |
| `/SeguimientoTickets/` | `seguimientoticket_list` | Operativo |

---

## 10. Archivos clave

| Archivo | Rol |
|---------|-----|
| `GestorApp/models.py` | `TicketIT`, `SeguimientoTicket`, estados, SLA |
| `GestorApp/forms/tickets.py` | Formularios ticket/check, validación de cierre |
| `GestorApp/forms/common.py` | Subtipos por `tipo_ticket` |
| `GestorApp/views/tickets.py` | CRUD, permisos, SLA, dashboard |
| `GestorApp/views/helpers.py` | Visibilidad y ownership |
| `GestorApp/cobertura.py` | Suplente ve tickets del ausente |
| `GestorIT/urls.py` | Rutas |
| `GestorApp/Templates/ticketit/` | list, detail, form, dashboard, confirm_delete |
| `GestorApp/Templates/seguimientoticket/` | list, form, confirm_delete |
| `GestorApp/Templates/home.html` | KPIs y alertas operativas |
| `static/GestorApp/css/app.css` | Estilos de detalle, alertas, dashboard |

Migración relacionada: `0031_ticketit_asignado_a_flujo_estados.py` (campo `asignado_a`).

---

## 11. Cómo usarlo (día a día)

### Solicitante
1. Crea un ticket.
2. Consulta solo los suyos en lista / home / calendario.
3. Puede editarlo mientras esté Abierto y sin checks.
4. Ve el avance en el detalle (timeline), sin poder agregar checks.

### Operativo (Tecnico IT / Admin)
1. Revisa home: SLA vencidos, sin seguimiento, checks por atender.
2. Abre el **Dashboard** para priorizar.
3. Asigna o marca **En Revision**.
4. Registra seguimientos desde el detalle del ticket.
5. Cierra con check **Concluido** + solución.
6. Si hace falta, **Reabre** el ticket.
7. Solo Admin borra tickets (sin checks) o seguimientos.

---

## 12. Fuera de alcance (aún no)

- Envío de notificaciones por **email**.
- Soft-delete de tickets.
- Multi-adjuntos.
- SLA en días hábiles (hoy es tiempo calendario continuo).

Cuando se activen correos, conviene reutilizar los mismos criterios de aviso que ya existen en home/dashboard.
