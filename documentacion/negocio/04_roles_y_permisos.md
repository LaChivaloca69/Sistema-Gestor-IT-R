# 4. Roles y permisos

---

## 4.1 Roles de negocio

El sistema usa tres roles. Cada cuenta debe tener **un** rol de negocio.

| Rol | Proposito |
|-----|-----------|
| Usuario | Autoservicio: tickets propios, equipos asignados, solicitudes y ordenes propias |
| Tecnico IT | Operacion diaria: inventario, soporte completo, mantenimiento, coberturas, catalogos |
| Administrador | Todo lo operativo mas gobierno: personal, roles, borrados criticos, plantillas, retencion |

El **superusuario** de la plataforma se trata como Administrador.

Tener solo la marca tecnica de personal de Django (`is_staff`) **sin** el grupo Administrador **no** otorga privilegios de Administrador en la aplicacion web.

---

## 4.2 Quien asigna el rol

| Situacion | Quien |
|-----------|-------|
| Alta de persona y cuenta | Administrador (el registro publico esta desactivado por defecto) |
| Cambio de rol | Administrador, desde Personal |
| Bajar varios a Usuario | Administrador, menu Admin / Quitar roles |

---

## 4.3 Matriz resumida de capacidades

| Capacidad | Usuario | Tecnico IT | Administrador |
|-----------|:-------:|:----------:|:-------------:|
| Iniciar sesion, Inicio, calendario | Si | Si | Si |
| Mis equipos (consulta) | Si | Si | Si |
| Crear y ver tickets propios | Si | Si | Si |
| Comentar en tickets propios (abiertos) | Si | Si | Si |
| Ver y operar todos los tickets | No | Si | Si |
| Checks, bitacora y respuestas | No | Si | Si |
| Eliminar ticket o check | No | No | Si |
| Solicitar equipo | Si | Si | Si |
| Revisar solicitudes (decision IT) | No | Si | Si |
| Inventario completo y consumibles | No | Si | Si |
| Dar de baja o eliminar equipo | No | No | Si |
| Ordenes de compra propias | Si | Si | Si |
| Ver todas las ordenes | No | Si | Si |
| Terminar orden de compra | No | Si | Si |
| Plantillas de documentos | No | No | Si |
| Catalogos (alta y edicion) | No | Si | Si |
| Eliminar catalogos | No | No | Si |
| Personal (escritura) y roles | No | No | Si |
| Cobertura de tickets | No | Si | Si |
| Matriz de permisos, archivar historial | No | No | Si |
| Acceso a panel Django Admin | No | No | Si (con privilegio de personal de plataforma) |

---

## 4.4 Reglas importantes de permisos

1. El Usuario no opera el inventario general; consulta **Mis equipos** y puede abrir el detalle de un equipo que tenga asignado.
2. Solo el Administrador elimina tickets, y solo si no tienen seguimientos.
3. Terminar una orden de compra es accion de personal operativo (Tecnico IT o Administrador), no del Usuario elaborador.
4. El Tecnico IT puede crear y editar coberturas en las que participa (ausente, suplente o creador); el Administrador ve todas.
5. Al eliminar un registro de Personal, la cuenta de acceso vinculada **se desactiva**; no se borra el historial asociado de forma agresiva eliminando al usuario.

---

## 4.5 Pantalla Matriz de permisos

El Administrador puede abrir **Admin / Matriz permisos** para consultar una tabla documentada de capacidades por rol. Esa pantalla es de consulta; los permisos reales se aplican por rol asignado en Personal.
