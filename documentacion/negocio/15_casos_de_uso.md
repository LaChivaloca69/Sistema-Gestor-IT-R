# 15. Casos de uso

Catalogo formal de capacidades del **Sistema Web para la gestion de inventario y Mesa de ayuda TI**.

**Ultima revision:** septiembre 2026.

Los avisos se consultan en Inicio, campana y paneles. El sistema no envia correo.

---

## Actores

| Actor | Quien es |
|-------|----------|
| Visitante | No ha iniciado sesion |
| Usuario | Empleado final (autoservicio) |
| Tecnico IT | Operacion diaria del area TI |
| Administrador | Gobierno y operacion completa |
| Operativo | Tecnico IT o Administrador |
| Sistema | Trabajos en segundo plano |

---

## Indice

| ID | Caso de uso | Actor principal |
|----|-------------|-----------------|
| CU-01 | Alta de cuenta por Administrador | Administrador |
| CU-02 | Iniciar y cerrar sesion | Todos |
| CU-03 | Ver inicio, calendario y avisos | Todos |
| CU-04 | Consultar mis equipos y detalle propio | Todos |
| CU-05 | Crear ticket de soporte | Todos |
| CU-06 | Consultar y editar mis tickets | Usuario |
| CU-07 | Operar el backlog de tickets | Operativo |
| CU-08 | Registrar seguimiento de ticket | Operativo |
| CU-09 | Reabrir ticket | Operativo |
| CU-10 | Eliminar ticket o seguimiento | Administrador |
| CU-11 | Comentar y eliminar comentario con confirmacion | Solicitante / Operativo / Administrador |
| CU-12 | Ver panel SLA de tickets | Todos (alcance distinto) |
| CU-13 | Registrar bitacora y respuestas | Operativo |
| CU-14 | Solicitar equipo | Todos |
| CU-15 | Revisar solicitud de equipo | Operativo |
| CU-16 | Cancelar solicitud de equipo | Solicitante / Operativo |
| CU-17 | Alta de equipo, periferico o herramienta | Operativo |
| CU-18 | Asignar y devolver equipo | Operativo |
| CU-19 | Cambiar ubicacion de equipo | Operativo |
| CU-20 | Dar de baja, reactivar o eliminar equipo | Administrador |
| CU-21 | Consultar movimientos de equipo | Operativo |
| CU-22 | Consultar historial de actividad (auditoria) | Operativo |
| CU-23 | Gestionar asignaciones y kits | Operativo |
| CU-24 | Gestionar consumibles y stock | Operativo |
| CU-25 | Programar y ejecutar mantenimiento | Operativo |
| CU-26 | Cerrar mantenimiento y proximo ciclo | Operativo |
| CU-27 | Crear o subir orden de compra | Todos |
| CU-28 | Terminar orden y generar PDF | Operativo |
| CU-29 | Gestionar plantillas de documentos | Administrador |
| CU-30 | Mantener catalogos (org, ubicaciones, proveedores, categorias) | Operativo / Administrador |
| CU-31 | Gestionar personal y roles | Administrador |
| CU-32 | Bajar roles masivo | Administrador |
| CU-33 | Delegar tickets (cobertura) | Operativo |
| CU-34 | Consultar matriz de permisos y guia SLA | Administrador |
| CU-35 | Archivar o purgar historial | Administrador |
| CU-36 | Acceder a Django Admin | Administrador |
| CU-37 | Retencion y recordatorios automaticos | Sistema |

---

## 1. Acceso y panel

### CU-01 — Alta de cuenta por Administrador

**Actor:** Administrador  
**Precondicion:** Tiene privilegios de gobierno.

**Flujo**
1. Crea o edita **Personal**.
2. Vincula o crea la cuenta de acceso.
3. Asigna rol Usuario, Tecnico IT o Administrador.

**Resultado:** La persona puede iniciar sesion.  
**Nota:** El registro publico (`/signup/`) esta desactivado por defecto.

---

### CU-02 — Iniciar y cerrar sesion

**Actor:** Usuario, Tecnico IT, Administrador  

**Flujo**
1. Inicia sesion en la pantalla de acceso.
2. El sistema redirige a Inicio.
3. Cierra sesion desde el encabezado.

**Excepcion:** Ruta protegida sin sesion redirige al login.

---

### CU-03 — Ver inicio, calendario y avisos

**Actor:** Todos los autenticados  

**Flujo**
1. Abre Inicio.
2. Consulta indicadores segun rol.
3. Usa el calendario (tickets, checks, mantenimientos).
4. Abre la campana para ir a listados filtrados.

**Alcance:** Usuario ve lo propio; operativo ve el panorama de operacion.

---

### CU-04 — Consultar mis equipos y detalle propio

**Actor:** Todos  

**Flujo**
1. Entra a **Mis equipos**.
2. Ve asignaciones activas y perifericos del kit.
3. Puede abrir el detalle de un equipo propio en modo consulta.

**Excepcion:** Un Usuario no abre el detalle de un equipo ajeno.

---

## 2. Soporte

### CU-05 — Crear ticket de soporte

**Actor:** Todos  

**Flujo**
1. Crea un ticket (selector de problema o modo manual).
2. Captura requerimiento, tipo y prioridad; puede ligar equipo.
3. Se genera folio y abre el detalle.

**Variante:** Tipo MANTENIMIENTO solicita ayuda por mesa de ayuda; no crea por si solo la orden formal de mantenimiento.

---

### CU-06 — Consultar y editar mis tickets

**Actor:** Usuario (solicitante)  

**Flujo**
1. Lista solo sus tickets.
2. Abre el detalle.
3. Edita solo si esta Abierto y sin seguimientos.

---

### CU-07 — Operar el backlog de tickets

**Actor:** Operativo  

**Flujo**
1. Lista todos los tickets; filtra por SLA, asignacion o sin seguimiento.
2. Marca En revision.
3. Atiende con seguimientos (CU-08).

**Cobertura:** Los tickets del ausente cuentan para el suplente (CU-33).

---

### CU-08 — Registrar seguimiento de ticket

**Actor:** Operativo  

**Flujo**
1. Agrega check con avance, pendiente, proximo paso y solucion.
2. El estado del ticket se recalcula (En proceso o Cerrado).
3. Las fechas de proximo seguimiento generan avisos si aplican.

**Excepcion:** Concluido sin solucion no guarda.

---

### CU-09 — Reabrir ticket

**Actor:** Operativo  
**Precondicion:** Ticket cerrado.

**Flujo**
1. Reabrir con motivo opcional.
2. El ticket vuelve a En Proceso.

---

### CU-10 — Eliminar ticket o seguimiento

**Actor:** Administrador  

- Eliminar seguimiento: permitido para Admin.
- Eliminar ticket: solo sin seguimientos.

Usuario y Tecnico IT no eliminan tickets ni checks.

---

### CU-11 — Comentar y eliminar comentario con confirmacion

**Actor:** Solicitante, Operativo, Administrador  

**Flujo**
1. Publicar comentario y adjuntos permitidos.
2. Para eliminar, abrir la confirmacion y confirmar.

En ticket cerrado, el solicitante no comenta; TI si puede.

---

### CU-12 — Ver panel SLA de tickets

**Actor:** Todos autenticados  

Metricas por estado, prioridad y SLA. Alcance segun rol.

---

### CU-13 — Registrar bitacora y respuestas

**Actor:** Operativo  

1. Crea bitacora.
2. Agrega respuestas.
3. Eliminar: Administrador; no borra bitacora con respuestas.

---

## 3. Solicitudes de equipo

### CU-14 — Solicitar equipo

**Actor:** Todos  

Captura titulo, justificacion, urgencia y destino. Folio de solicitud en estado Pendiente.

---

### CU-15 — Revisar solicitud de equipo

**Actor:** Operativo  

En el detalle registra avance y decision (En revision, Aprobar, Rechazar, Cerrar). Puede asignar equipo disponible al completar.

---

### CU-16 — Cancelar solicitud de equipo

**Actor:** Solicitante (estados permitidos) u Operativo  

No se cancela una solicitud ya completada o cerrada en sentido final equivalente.

---

## 4. Inventario y consumibles

### CU-17 — Alta de equipo, periferico o herramienta

**Actor:** Operativo  

Alta con categoria y origen; si aplica, consume cupo de linea de OC.

---

### CU-18 — Asignar y devolver equipo

**Actor:** Operativo  

Asigna a personal activo. Una sola asignacion activa por equipo. Devolver regresa a En Stock si corresponde.

---

### CU-19 — Cambiar ubicacion de equipo

**Actor:** Operativo  

Actualiza espacio fisico y registra movimiento.

---

### CU-20 — Dar de baja, reactivar o eliminar equipo

**Actor:** Administrador  

Baja logica, reactivacion o eliminacion fisica con restricciones.

---

### CU-21 — Consultar movimientos de equipo

**Actor:** Operativo  

Lista el ciclo de vida del activo (alta, asignacion, ubicacion, mantenimiento, etc.).

---

### CU-22 — Consultar historial de actividad (auditoria)

**Actor:** Operativo  

Lista quien hizo que en el sistema, con filtros. Detalle por evento.

---

### CU-23 — Gestionar asignaciones y kits

**Actor:** Operativo  

Listado de asignaciones, vinculacion de perifericos y migracion de kit cuando aplique.

---

### CU-24 — Gestionar consumibles y stock

**Actor:** Operativo  

Alta de productos, entradas, salidas y consulta de alertas de stock bajo.

---

## 5. Mantenimiento

### CU-25 — Programar y ejecutar mantenimiento

**Actor:** Operativo  

Crea orden Programada; al iniciar pasa a En Proceso y el equipo a En Mantenimiento.

---

### CU-26 — Cerrar mantenimiento y proximo ciclo

**Actor:** Operativo  

Registra cierre. Puede hacerse desde En Proceso o desde Programado (inicio y cierre en el mismo flujo). Opcional: proxima fecha de ciclo.

---

## 6. Compras

### CU-27 — Crear o subir orden de compra

**Actor:** Todos  

Crear en sistema o subir archivo. Usuario solo gestiona las propias en consulta/edicion permitida.

---

### CU-28 — Terminar orden y generar PDF

**Actor:** Operativo  

Termina la orden y genera PDF. El Usuario no termina ordenes.

---

### CU-29 — Gestionar plantillas de documentos

**Actor:** Administrador  

Alta y edicion de plantillas para generacion documental.

---

## 7. Organizacion, ubicaciones y gobierno

### CU-30 — Mantener catalogos

**Actor:** Operativo (alta/edicion), Administrador (eliminacion)  

Departamentos, puestos, edificios, zonas, ubicaciones, categorias, proveedores.

---

### CU-31 — Gestionar personal y roles

**Actor:** Administrador  

CRUD de Personal, vinculo a cuenta y rol. Al eliminar Personal se desactiva la cuenta vinculada.

---

### CU-32 — Bajar roles masivo

**Actor:** Administrador  

Pasa tecnicos o administradores a Usuario, con exclusiones de seguridad (superusuario y uno mismo).

---

### CU-33 — Delegar tickets (cobertura)

**Actor:** Operativo  

Crea cobertura ausente/suplente/fechas. Sin solapes activos del mismo ausente. Alcance de edicion segun participacion o rol Admin.

---

### CU-34 — Consultar matriz de permisos y guia SLA

**Actor:** Administrador  

Pantallas de consulta documental.

---

### CU-35 — Archivar o purgar historial

**Actor:** Administrador  

Aplica politica de retencion sobre el historial de actividad.

---

### CU-36 — Acceder a Django Admin

**Actor:** Administrador con privilegio de personal de plataforma  

Backoffice tecnico.

---

## 8. Sistema

### CU-37 — Retencion y recordatorios automaticos

**Actor:** Sistema  

| Trabajo | Periodicidad tipica | Efecto |
|---------|---------------------|--------|
| Retencion de historial | Diario | Archiva o purga segun configuracion |
| Recordatorios operativos | Periodico corto | Deja rastro si cambia el panorama de alertas |

Requiere el proceso de trabajos en segundo plano en el entorno de ejecucion.

---

## Matriz resumida

| Capacidad | Usuario | Tecnico IT | Admin |
|-----------|:-------:|:----------:|:-----:|
| Login / inicio / mis equipos | Si | Si | Si |
| Tickets propios y comentarios | Si | Si | Si |
| Todos los tickets, checks, bitacora | No | Si | Si |
| Borrar ticket / check | No | No | Si |
| Solicitar equipo | Si | Si | Si |
| Revision IT de solicitudes | No | Si | Si |
| Inventario, consumibles, mantenimiento | No | Si | Si |
| Baja / eliminar equipo | No | No | Si |
| Ordenes propias | Si | Si | Si |
| Terminar ordenes / ver todas | No | Si | Si |
| Plantillas | No | No | Si |
| Personal y roles | No | No | Si |
| Coberturas | No | Si | Si |
| Matriz, archivar, Django Admin | No | No | Si |

---

## Flujos de punta a punta (referencia)

1. **Nuevo empleado:** CU-01, luego CU-05 / CU-14 / CU-27; elevacion de rol con CU-31 si entra a TI.
2. **Falla de equipo:** Usuario CU-05; TI CU-07 y CU-08; si aplica, CU-25.
3. **Pedir laptop:** CU-14, revision CU-15, consulta en CU-04.
4. **Compra a inventario:** CU-27, CU-28, CU-17, CU-18.
5. **Tecnico ausente:** CU-33 y operacion CU-07 por el suplente.
6. **Consumible agotado:** CU-24 y reposicion via compras si aplica.
