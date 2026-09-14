# 8. Modulo tickets (mesa de ayuda)

---

## 8.1 Proposito

Gestionar solicitudes de soporte con SLA, seguimientos, comentarios, bitacora interna y cobertura entre tecnicos.

---

## 8.2 Conceptos

| Concepto | Modelo |
|----------|--------|
| Ticket | `TicketIT` |
| Seguimiento / check | `SeguimientoTicket` |
| Comentario | `ComentarioTicket` + `ComentarioTicketAdjunto` |
| Bitacora interna | `Bitacora` + `Answer` |
| Prioridad / SLA | `PrioridadSupport`, `SLA_HORAS_POR_PRIORIDAD` |
| Catalogo guiado | `ticket_catalog.py` |

---

## 8.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Vistas | `views/tickets.py`, alertas en `helpers` / `home` |
| Forms | `forms/tickets.py` |
| Cobertura query | `cobertura.py` |
| Templates | `ticketit/`, `seguimientoticket/`, `bitacora/`, `answer/` |
| URLs | `ticketit_*`, `seguimientoticket_*`, `bitacora_*`, `answer_*` |
| Media | `media_security.py` para adjuntos |

---

## 8.4 Flujos principales

### Crear ticket

Usuario: selector de problema o `?manual=1`. Operativo puede asignar tecnico. Folio automatico. `fecha_support` la fija el servidor (se ignora intento de falsear SLA con fecha cliente).

### Seguimiento

POST de check recalcula estado del ticket (En Proceso / Cerrado). Concluir exige solucion.

### Comentarios

Create con permisos; delete muestra confirmacion GET y borra en POST (`ticketit_comentario_delete`).

### Cobertura

`ticket_asignados_q_for_user` amplia “asignados a mi” con ausentes cubiertos.

---

## 8.5 Reglas

- Usuario solo ve/edita lo propio (edicion limitada).  
- Eliminar ticket: Admin y sin seguimientos.  
- Eliminar check: Admin.  
- Seguimiento/Answer fuerzan `usuario = request.user` en create.  
- Adjuntos: tipos y tamanos validados.

---

## 8.6 Permisos

Decoradores operativo en backlog IT; helpers `user_can_*` en detalle. Comentarios: ver ticket + reglas de cerrado.

---

## 8.7 Integraciones

Equipo opcional; Personal/area/puesto; nav badges SLA + sin check; calendario; historial.

---

## 8.8 Puntos delicados

- Reapertura crea seguimiento.  
- Cerrar ticket limpia pendientes de checks abiertos (ver tests).  
- Bitacora no es visible al Usuario en menu.

---

## 8.9 Como probar

`TicketComentarioTests`, `TicketCreateEquipoChoicesTests`, `TicketSelectorProblemaTests`, `TicketCierreLimpiaPendientesTests`, `BitacoraAnswerFlowTests`, `UserFailureHardeningTests.test_fecha_support_client_no_falsea_sla`.
