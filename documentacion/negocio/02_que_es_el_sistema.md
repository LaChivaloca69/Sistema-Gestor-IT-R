# 2. Que es el sistema

**Sistema Web para la gestion de inventario y Mesa de ayuda TI**

---

## 2.1 Proposito

Es una aplicacion web interna para el area de Tecnologias de la Informacion. Centraliza:

- el inventario de activos de TI (equipos, perifericos, herramientas);
- el stock de consumibles;
- la mesa de ayuda (tickets de soporte);
- el mantenimiento de equipos;
- las ordenes de compra relacionadas con TI;
- la organizacion (personal, departamentos, puestos);
- las ubicaciones fisicas (edificios, zonas, espacios);
- el gobierno de roles y la auditoria de actividad.

El objetivo es tener un unico lugar para **saber que hay**, **a quien esta asignado**, **que fallas se atienden** y **quien hizo cada cambio relevante**.

---

## 2.2 Alcance funcional

| Dominio | Que cubre |
|---------|-----------|
| Inventario unitario | Alta, ubicacion, asignacion, devolucion, baja, kit de perifericos |
| Consumibles | Productos con cantidad, entradas, salidas y alertas de stock bajo |
| Mesa de ayuda | Tickets, prioridades, SLA, seguimientos (checks), comentarios y adjuntos |
| Bitacora interna | Situaciones internas de TI con respuestas |
| Mantenimiento | Programacion, inicio, cierre y proximo ciclo |
| Compras | Ordenes creadas en sistema o subidas, PDF, vinculo al alta de equipos |
| Solicitudes de equipo | Pedido del usuario y decision de TI |
| Organizacion | Departamentos, puestos, personal vinculado a cuenta de acceso |
| Ubicaciones | Edificio, zona, ubicacion y mapa de sedes |
| Gobierno | Administrar el sistema: roles, coberturas, solicitudes de equipo, matriz de permisos, guia SLA y retencion del historial (ver glosario) |
| Auditoria | Historial de actividad filtrable |

---

## 2.3 Limites del sistema.

| Limite | Detalle |
|--------|---------|
| No es un ERP completo | No gestiona nominas, contabilidad general ni produccion de planta |
| No envia correo | Los avisos se ven en Inicio, campana y paneles; no hay notificaciones por email |
| Registro publico | Por defecto el alta de cuentas publicas esta desactivada; el Administrador da de alta al personal |
| Un solo equipo activo | Un equipo fisico no puede tener dos asignaciones activas a la vez |
| Consumibles distintos de equipos | Los consumibles se manejan por cantidad, no como pieza con serie individual |

---

## 2.4 Actores del sistema

| Actor | Descripcion |
|-------|-------------|
| Visitante | Persona sin sesion iniciada |
| Usuario | Empleado final en autoservicio |
| Tecnico IT | Personal de operacion diaria de TI |
| Administrador | Responsable del gobierno del sistema; tambien puede hacer lo operativo |
| Operativo | Termino de este manual: Tecnico IT o Administrador |
| Sistema | Tareas automaticas en segundo plano (retencion, recordatorios) |

Un Administrador puede realizar todo lo que hace un Tecnico IT, y ademas las funciones de **gobierno** (definir quien puede que, coberturas, tramites formales de solicitud, consulta de permisos/SLA y politicas del historial). Ver la entrada **Gobierno** en el glosario.
---

## 2.5 Principios de uso

1. Cada persona entra con su propia cuenta y un rol asignado.
2. Lo que se ve en el menu depende del rol.
3. Las acciones criticas (borrados, baja de equipos, roles, plantillas) estan reservadas al Administrador.
4. Los cambios relevantes quedan registrados en el historial de actividad.
5. Los estados de tickets, equipos y mantenimientos se controlan con acciones de pantalla, no escribiendo el estado a mano en la mayoria de los casos.
