# Casos de uso — Sistema Gestor IT

Que puede hacer cada persona en la aplicacion, modulo por modulo.

Los avisos (SLA, checks, mantenimientos, solicitudes) se ven en **Inicio**, **campana** y **dashboards**. No se envia correo.

---

## Actores

| Actor | Quien es |
|-------|----------|
| **Visitante** | No ha iniciado sesion |
| **Usuario** | Empleado final (autoservicio) |
| **Tecnico IT** | Operacion diaria del area IT |
| **Administrador** | Gobierno: roles, borrados, plantillas, retencion |
| **Operativo** | Tecnico IT o Administrador (mismo trabajo de piso) |
| **Sistema** | Jobs en segundo plano (django-q2) |

Un Administrador puede hacer todo lo de Tecnico IT, mas gobierno y borrados.

---

## Indice

| ID | Caso de uso | Actor principal |
|----|-------------|-----------------|
| CU-01 | Registrarse | Visitante |
| CU-02 | Iniciar / cerrar sesion | Todos |
| CU-03 | Ver inicio, calendario y avisos | Todos |
| CU-04 | Consultar mis equipos | Todos |
| CU-05 | Crear ticket de soporte | Todos |
| CU-06 | Consultar y editar mis tickets | Usuario |
| CU-07 | Operar el backlog de tickets | Operativo |
| CU-08 | Registrar seguimiento de ticket | Operativo |
| CU-09 | Reabrir ticket | Operativo |
| CU-10 | Eliminar ticket o seguimiento | Administrador |
| CU-11 | Ver dashboard SLA | Todos (alcance distinto) |
| CU-12 | Registrar bitacora y respuestas | Operativo |
| CU-13 | Solicitar equipo | Todos |
| CU-14 | Revisar solicitud de equipo | Operativo |
| CU-15 | Cancelar solicitud de equipo | Solicitante / Operativo |
| CU-16 | Alta de equipo en inventario | Operativo |
| CU-17 | Asignar / devolver equipo | Operativo |
| CU-18 | Cambiar ubicacion de equipo | Operativo |
| CU-19 | Dar de baja / reactivar / eliminar equipo | Administrador |
| CU-20 | Consultar movimientos y auditoria | Operativo |
| CU-21 | Gestionar asignaciones | Operativo |
| CU-22 | Programar y ejecutar mantenimiento | Operativo |
| CU-23 | Cerrar mantenimiento y proximo ciclo | Operativo |
| CU-24 | Crear / subir orden de compra | Todos |
| CU-25 | Terminar orden y generar PDF | Todos (propias o todas) |
| CU-26 | Gestionar plantillas de documentos | Administrador |
| CU-27 | Mantener catalogos (org, ubicaciones, proveedores) | Operativo |
| CU-28 | Gestionar personal y roles | Administrador |
| CU-29 | Bajar roles masivo | Administrador |
| CU-30 | Delegar tickets (cobertura) | Operativo |
| CU-31 | Consultar matriz de permisos | Administrador |
| CU-32 | Archivar / purgar historial | Administrador |
| CU-33 | Acceder a Django Admin | Administrador |
| CU-34 | Retencion y recordatorios automaticos | Sistema |

---

## 1. Acceso y panel

### CU-01 — Registrarse

**Actor:** Visitante  
**Precondicion:** No tiene cuenta.

**Flujo**
1. Entra a `/signup/`.
2. Captura usuario, contraseña y datos de personal.
3. El sistema crea `User` + perfil `Personal` con rol **Usuario**.

**Resultado:** Puede iniciar sesion. No hay checkbox de “solicitar admin”.

---

### CU-02 — Iniciar / cerrar sesion

**Actor:** Usuario, Tecnico IT, Administrador  
**Precondicion:** Tiene cuenta.

**Flujo**
1. Entra a `/login/` (si ya esta autenticado, redirige a Inicio).
2. Tras login va a Inicio (`/`).
3. Cierra sesion en `/logout/`.

**Excepcion:** Ruta protegida sin sesion → redirect a login con `?next=`.

---

### CU-03 — Ver inicio, calendario y avisos

**Actor:** Todos los autenticados  
**Precondicion:** Sesion activa.

**Flujo**
1. Abre **Inicio**.
2. Ve KPIs segun rol (tickets, SLA, equipos, mantenimientos, solicitudes).
3. Usa el **calendario** (tickets en fecha SLA, checks en proximo seguimiento, mantenimientos).
4. Abre la **campana** del topbar para ir al listado filtrado.

**Alcance**
- Usuario: solo lo suyo (tickets propios, calendario propio).
- Operativo: panorama de operacion (SLA, checks vencidos, solicitudes pendientes).

**Resultado:** Entiende que atender hoy, sin correo.

---

### CU-04 — Consultar mis equipos

**Actor:** Todos  
**Precondicion:** Tiene perfil de personal con asignaciones, o no tiene ninguna.

**Flujo**
1. Entra a **Mis equipos** (`/Equipos/mis/`).
2. Ve equipos con asignacion **Activa** a su personal.

**Resultado:** Consulta; no asigna ni da de baja desde aqui.

---

## 2. Soporte (tickets)

### CU-05 — Crear ticket de soporte

**Actor:** Todos  
**Precondicion:** Sesion activa.

**Flujo**
1. **Tickets → Nuevo** (`/Ticketit/create/`).
2. Describe el problema, tipo/subtipo, prioridad; puede ligar equipo e imagen.
3. Usuario: queda como solicitante; no asigna tecnico.
4. Operativo: puede asignar tecnico. Si asigna un ticket Abierto, pasa a **En revision**.
5. Se genera folio `SPR0-######` y abre el detalle.

**Variante:** Tipo **MANTENIMIENTO** = pedir mantenimiento via mesa de ayuda (no crea la orden formal de `/MantenimientoEquipos/`).

---

### CU-06 — Consultar y editar mis tickets

**Actor:** Usuario (solicitante)  
**Precondicion:** El ticket es suyo (`solicitado_por`).

**Flujo**
1. Lista **Tickets** (solo los propios). Filtros: busqueda, tipo, prioridad, estatus.
2. Abre el detalle: datos, SLA, timeline de seguimientos (solo lectura).
3. Puede **editar** solo si esta **Abierto** y **sin seguimientos**.

**Excepciones**
- Ticket ajeno → bloqueado.
- Ya hay checks → no edita ni elimina.

---

### CU-07 — Operar el backlog de tickets

**Actor:** Operativo  
**Precondicion:** Rol Tecnico IT o Administrador.

**Flujo**
1. Lista todos los tickets. Vistas: Todos / Mis tickets / Asignados a mi.
2. Filtra por SLA (vencido, por vencer), sin seguimiento, prioridad.
3. Abre un ticket Abierto sin checks y **Marca En revision** (si no hay asignado, se asigna a quien marca).
4. Atiende con seguimientos (CU-08).

**Cobertura:** Si cubre a un ausente (CU-30), los tickets de ese tecnico cuentan como “asignados a mi”.

---

### CU-08 — Registrar seguimiento de ticket

**Actor:** Operativo  
**Precondicion:** Ticket no cerrado (o se reabre antes).

**Flujo**
1. En el detalle, **Agregar seguimiento** (avance, pendiente, proximo paso, fecha de proximo check, solucion).
2. El estado del ticket se recalcula:
   - Sin checks: Abierto o En revision.
   - Ultimo check abierto: **En proceso**.
   - Check **Concluido** + solucion: **Cerrado**.
3. La fecha de proximo seguimiento genera aviso en Inicio si no esta concluido y el ticket no esta cerrado.

**Excepcion:** Concluido sin solucion → no guarda.

**Lista** `/SeguimientoTickets/`: filtros de vencidos / por vencer / por atender.

---

### CU-09 — Reabrir ticket

**Actor:** Operativo  
**Precondicion:** Ticket **Cerrado**.

**Flujo**
1. En el detalle, **Reabrir** (motivo opcional).
2. Se crea un seguimiento de reapertura.
3. El ticket vuelve a **En proceso**.

---

### CU-10 — Eliminar ticket o seguimiento

**Actor:** Administrador  
**Precondicion:** Ticket sin seguimientos para borrar el ticket.

**Flujo**
- Eliminar **seguimiento:** Admin, desde detalle o lista de checks.
- Eliminar **ticket:** solo si no tiene checks. Si tiene, hay que quitarlos primero.

**Usuario y Tecnico** no eliminan tickets ni checks (el Tecnico tampoco borra seguimientos).

---

### CU-11 — Ver dashboard SLA

**Actor:** Todos (login)  
**Ruta:** `/Ticketit/dashboard/`

**Flujo**
1. Ve conteos por estado, prioridad, SLA vencido / por vencer, sin seguimiento.
2. Usuario: metricas de su universo. Operativo: operacion completa.

---

### CU-12 — Registrar bitacora y respuestas

**Actor:** Operativo  
**Precondicion:** Rol operativo.

**Flujo**
1. Crea una **Bitacora** (situacion interna, folio `BIT-######`).
2. En el detalle agrega **respuestas** (solucion / descripcion), equivalente al seguimiento del ticket.
3. Consulta el listado de respuestas.
4. Editar: operativo. Eliminar bitacora/respuesta: **Admin**. No se borra bitacora si ya tiene respuestas.

**Usuario** no ve Bitacora ni Respuestas en el menu.

---

## 3. Solicitudes de equipo

### CU-13 — Solicitar equipo

**Actor:** Todos  
**Precondicion:** Sesion activa.

**Flujo**
1. **Solicitudes → Nueva** (`/SolicitudesEquipo/create/`).
2. Titulo, justificacion, urgencia, categoria opcional, personal destino (si el Usuario tiene perfil, se sugiere el suyo).
3. Folio `SOL-######`, estado **Pendiente**.

**Usuario:** ve las suyas y el hilo de **Revision IT** (solo lectura).  
**Operativo:** ve todas y el badge de pendientes.

---

### CU-14 — Revisar solicitud de equipo

**Actor:** Operativo  
**Precondicion:** Estado Pendiente, En revision o Aprobada.

**Flujo** (un solo bloque **Revision IT**)
1. Abre el detalle.
2. En el mismo formulario:
   - registra **avance** (lo que se le va a hacer / se hizo);
   - toma **decision**: En revision, Aprobar, Rechazar o Cerrar.
3. Opcional: elige equipo disponible y se asigna al personal destino al aprobar/cerrar.
4. El historial de revisiones queda en el mismo panel.

**Resultado**
- Avance sin cerrar → suele pasar a **En revision**.
- Aprobar → lista para asignar (si hay equipo, puede completar y asignar).
- Rechazar / Cerrar → termina el caso.

El solicitante no guarda revisiones.

---

### CU-15 — Cancelar solicitud de equipo

**Actor:** Solicitante (la suya) o Operativo  
**Precondicion:** El solicitante solo si esta Pendiente o En revision.

**Flujo**
1. **Cancelar solicitud** y confirma.
2. Estado **Cancelada**.

---

## 4. Inventario

### CU-16 — Alta de equipo en inventario

**Actor:** Operativo  
**Precondicion:** Catalogos listos (categoria; opcional proveedor, ubicacion, orden de compra).

**Flujo**
1. **Equipos → Nuevo**.
2. Codigo de inventario, serie, categoria, origen (compra / legado / donacion…).
3. Si viene de una OC, liga orden + linea y consume cantidad disponible.
4. Queda en stock (o el estado que corresponda) y se registra movimiento / historial.

**Usuario** no entra al inventario completo; usa Mis equipos y Solicitudes.

---

### CU-17 — Asignar / devolver equipo

**Actor:** Operativo  
**Precondicion:** Equipo **puede asignarse** (disponible) o tiene asignacion activa para devolver.

**Asignar**
1. Desde el detalle, **Asignar** a un personal activo.
2. Cierra asignacion previa si existia.
3. Estado del equipo → **Asignado**. Movimiento de asignacion.

**Devolver**
1. **Devolver**.
2. Asignacion → Devuelta. Equipo → disponible (si aplica).

Tambien se puede asignar al cerrar una solicitud (CU-14).

---

### CU-18 — Cambiar ubicacion de equipo

**Actor:** Operativo  
**Precondicion:** Equipo existente.

**Flujo**
1. En el detalle, cambiar ubicacion (edificio → zona → ubicacion).
2. Se crea movimiento de **cambio de ubicacion**.

---

### CU-19 — Dar de baja / reactivar / eliminar equipo

**Actor:** Administrador  
**Precondicion:** Reglas del modelo (`puede_dar_de_baja`, etc.).

| Accion | Efecto |
|--------|--------|
| Baja | Baja logica + movimiento |
| Reactivar | Vuelve a operacion |
| Eliminar | Borrado fisico con restricciones (no si hay historial bloqueante) |

El Tecnico no da de baja ni elimina.

---

### CU-20 — Consultar movimientos y auditoria

**Actor:** Operativo  

**Movimientos** (`/MovimientoEquipos/registros/`): ciclo de vida del activo (alta, baja, asignacion, ubicacion, mantenimiento). Alta/edicion operativa; borrado Admin.

**Auditoria** (`/MovimientoEquipos/` y detalle `/Auditoria/<id>/`): **quien hizo que** en el sistema (historial de actividad), filtrable por modulo, usuario, fecha.

---

### CU-21 — Gestionar asignaciones

**Actor:** Operativo  
**Ruta:** `/AsignacionEquipos/`

CRUD de `AsignacionEquipo` (Activa / Devuelta / Extraviada). Borrar: Admin.

El Usuario las ve reflejadas en **Mis equipos**, no en este listado.

---

### CU-22 — Programar y ejecutar mantenimiento

**Actor:** Operativo  
**Precondicion:** Equipo existente.

**Flujo**
1. Crea mantenimiento (tipo preventivo/correctivo/predictivo, fecha, tecnico, falla). Folio tipo `MAN###-…`.
2. Estado inicial **Programado** (no se edita a mano).
3. **Iniciar** → **En proceso**. El equipo pasa a **En mantenimiento** + movimiento.
4. Puede **Cancelar** (Programado o En proceso).
5. Dashboard y avisos: vencidos, por vencer (7 dias).

**Reabrir:** desde Completado o Cancelado.

El Usuario pide mantenimiento con ticket tipo MANTENIMIENTO (CU-05), no opera este modulo.

---

### CU-23 — Cerrar mantenimiento y proximo ciclo

**Actor:** Operativo  
**Precondicion:** Mantenimiento en proceso (o flujo de cierre desde detalle).

**Flujo**
1. En el detalle o en **Cierres** (`/AgendaMantenimiento/`) registra fechas reales, acciones y observaciones.
2. El mantenimiento queda **Completado**.
3. El equipo vuelve a Disponible o Asignado (si no hay otro mant. en proceso).
4. Si indica **proxima fecha**, se puede programar el siguiente ciclo.

Eliminar mantenimiento o cierre: **Admin**.

---

## 5. Compras

### CU-24 — Crear / subir orden de compra

**Actor:** Todos  
**Precondicion:** Sesion activa.

**Flujo**
1. **Ordenes → Nueva** (`/OrdenesCompra/nueva/`).
2. Elige **crear en sistema** o **subir** archivo.
3. Captura proveedor, moneda/IVA, lineas de detalle (o PDF/archivo subido).
4. Folio `OC-######`.

**Alcance:** Usuario solo las que elaboro el. Operativo ve todas.

---

### CU-25 — Terminar orden y generar PDF

**Actor:** Quien puede gestionar esa orden  
**Precondicion:** Orden no terminada / con datos suficientes.

**Flujo**
1. Edita lineas si aplica.
2. **Terminar** genera PDF (plantilla + motor de documentos / LibreOffice si aplica).
3. **Preview** antes de cerrar.

**Borrar:** el dueño (Usuario, la suya) u operativo (todas). Queda evento en Historial; si borra un no-admin el nivel es critico para que Admin lo vea.

La orden terminada puede usarse al dar de alta equipos (CU-16).

---

### CU-26 — Gestionar plantillas de documentos

**Actor:** Administrador  
**Ruta:** `/Plantillas/`

Sube/edita plantillas DOCX/XLSX/PDF con campos detectados. El Tecnico no entra a este menu.

---

## 6. Organizacion y catalogos

### CU-27 — Mantener catalogos

**Actor:** Operativo (crear/editar), Administrador (eliminar)

| Catalogo | Para que |
|----------|----------|
| Areas, Puestos | Organizacion; tickets y personal |
| Edificios, Zonas, Ubicaciones | Donde esta el equipo (ubicacion filtra zonas por edificio) |
| Categorias de equipo | Tipo de activo; tickets y solicitudes |
| Proveedores | Inventario y compras (`PROV-######`) |

**Personal en lectura:** el Tecnico lista y ve detalle; no crea/edita/borra personas (eso es CU-28).

---

### CU-28 — Gestionar personal y roles

**Actor:** Administrador  
**Precondicion:** Persona con usuario vinculado para asignar rol.

**Flujo**
1. Crea o edita **Personal** (numero de empleado, area, puesto, usuario).
2. Campo **Rol del sistema:** Usuario / Tecnico IT / Administrador.
3. Al borrar Personal se elimina el User ligado.

**Excepcion:** No se baja a uno mismo ni a superusuarios por el atajo masivo (CU-29).

---

### CU-29 — Bajar roles masivo

**Actor:** Administrador  
**Ruta:** Admin → **Bajar roles**

Pasa Tecnicos/Admins a **Usuario**. No aplica a superusuarios ni a quien ejecuta la accion.

---

## 7. Gobierno

### CU-30 — Delegar tickets (cobertura)

**Actor:** Operativo  
**Ruta:** `/Gobierno/coberturas/`

**Flujo**
1. Crea cobertura: ausente, suplente, fechas, activa.
2. Mientras esta vigente, el suplente ve y atiende tickets asignados al ausente.

Ausente y suplente deben ser personas distintas. Fechas coherentes (fin ≥ inicio).

---

### CU-31 — Consultar matriz de permisos

**Actor:** Administrador  
**Ruta:** `/Gobierno/permisos/`

Consulta documentada de quien puede que. No cambia permisos en vivo (eso son Groups + decoradores).

---

### CU-32 — Archivar / purgar historial

**Actor:** Administrador  
**Ruta:** Admin → **Archivar** (`/Admin/historial-retencion/`)

Aplica politica de retencion (activo → archivo → purga) en caliente o via job (CU-34). Comando: `limpiar_historial`.

---

### CU-33 — Acceder a Django Admin

**Actor:** Administrador con `is_staff` (o superuser)  
**Ruta:** `/admin/`

Backoffice Django. El Tecnico no tiene `is_staff`.

---

## 8. Sistema

### CU-34 — Retencion y recordatorios automaticos

**Actor:** Sistema (`python manage.py qcluster`)

| Job | Cuando | Que hace |
|-----|--------|----------|
| Retencion de historial | Diario ~02:00 | Archiva / purga segun configuracion |
| Recordatorios operativos | Cada 15 min | Si cambia el panorama SLA/mant., deja evento en historial |

Sin worker, las tareas pueden ejecutarse en el mismo request (fallback) o quedar en cola.

---

## Matriz resumida

| Capacidad | Usuario | Tecnico IT | Admin |
|-----------|:-------:|:----------:|:-----:|
| Signup / login / inicio / mis equipos | Si | Si | Si |
| Tickets propios | Si | Si | Si |
| Todos los tickets, seguimientos, bitacora | No | Si | Si |
| Borrar ticket / seguimiento / bitacora | No | No | Si |
| Solicitar equipo | Si | Si | Si |
| Revision IT de solicitudes | No | Si | Si |
| Inventario, mant., asignaciones, movimientos | No | Si | Si |
| Baja / eliminar equipo | No | No | Si |
| Ordenes propias | Si | Si | Si |
| Todas las ordenes | No | Si | Si |
| Plantillas PDF | No | No | Si |
| Catalogos (alta/edicion) | No | Si | Si |
| Borrar catalogos | No | No | Si |
| Personal escritura y roles | No | No | Si |
| Coberturas | No | Si | Si |
| Matriz, archivar, /admin/ | No | No | Si |

---

## Flujos de punta a punta (referencia)

1. **Nuevo empleado:** CU-01 → CU-05 / CU-13 / CU-24 → Admin lo eleva (CU-28) si entra a IT.
2. **Falla de equipo:** Usuario CU-05 → Tecnico CU-07 + CU-08 → cierra con solucion. Si aplica, CU-22.
3. **Pedir laptop:** Usuario CU-13 → IT CU-14 (avance + asignar/cerrar) → Usuario lo ve en CU-04.
4. **Compra a inventario:** CU-24 → CU-25 → CU-16 (liga OC) → CU-17.
5. **Tecnico de vacaciones:** CU-30 → suplente opera CU-07.

Detalle de reglas: `ROLES.md`, `TICKETS.md`, `MANTENIMIENTO.md`, `INVENTARIO.md`, `MODULOS.md`.
