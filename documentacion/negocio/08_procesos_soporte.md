# 8. Procesos de soporte (mesa de ayuda)

---

## 8.1 Tickets

### Crear

1. Menu **Tickets**, opcion de alta.
2. El Usuario puede pasar por un selector de problemas o modo manual.
3. Capturar requerimiento, tipo, prioridad y, si aplica, equipo.
4. El sistema genera folio y deja el ticket visible para TI.

La fecha de soporte la fija el servidor; no se debe confiar en fechas alteradas desde el navegador para el SLA.

### Atender (operativo)

1. Filtrar por SLA, sin seguimiento o asignados.
2. Abrir el ticket y marcar **En revision** si corresponde.
3. Agregar **seguimientos (checks)** con avance, pendiente y solucion.
4. Un check concluido con solucion cierra el ticket.
5. Si hace falta, **reabrir** un ticket cerrado.

### Editar (Usuario)

Solo sus tickets en estado Abierto y sin seguimientos.

### Eliminar

Solo Administrador, y solo si no hay seguimientos.

---

## 8.2 Comentarios y adjuntos

- Sirven para evidencia (texto, imagen o PDF) sin sustituir el check formal.
- El solicitante comenta en tickets abiertos propios.
- TI puede comentar tambien en cerrados.
- Eliminar un comentario pide **confirmacion** en pantalla; solo el autor o el Administrador, segun reglas de permiso.

---

## 8.3 Checks (lista de seguimientos)

La lista de Checks permite filtrar vencidos, por vencer o por atender. El detalle del ticket sigue siendo el lugar principal para agregar un seguimiento.

---

## 8.4 Bitacora y respuestas

Uso interno de TI:

1. Crear una bitacora con la situacion.
2. Agregar respuestas en el detalle.
3. Eliminar bitacora o respuesta: Administrador; no se elimina una bitacora si ya tiene respuestas.

El Usuario no ve estas opciones en el menu.

---

## 8.5 Cobertura de tickets

Cuando un tecnico estara ausente:

1. Crear cobertura: ausente, suplente, periodo, motivo.
2. Mientras este vigente y activa, el suplente ve esos tickets en su filtro de asignados.
3. No deben solaparse dos coberturas activas del mismo ausente en las mismas fechas.
4. Un Tecnico IT gestiona coberturas en las que participa; el Administrador puede ver todas.

---

## 8.6 Panel tickets y SLA

El panel resume estados, prioridades y cumplimiento de SLA. El Usuario ve metricas de su universo; el operativo, el de toda la operacion.

La guia **Como funciona el SLA** (Administrador) documenta tiempos por prioridad en lenguaje de negocio.
