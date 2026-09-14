# 7. Guia del Administrador

Manual de tareas para el rol **Administrador**.

---

## 7.1 Alcance

El Administrador incluye todas las capacidades del Tecnico IT y, ademas, el gobierno del sistema.

---

## 7.2 Alta de personas y roles

1. Crear o editar **Personal** (numero de empleado, datos, area, puesto).
2. Vincular o crear la cuenta de acceso asociada.
3. Asignar el **Rol del sistema**: Usuario, Tecnico IT o Administrador.
4. Comunicar credenciales por un canal seguro.

El registro publico de cuentas esta desactivado por defecto.

### Quitar roles

En **Admin / Quitar roles** se puede bajar a Usuario a tecnicos o administradores en bloque. No aplica a superusuarios ni a la propia cuenta que ejecuta la accion.

### Baja de personal

Al eliminar un registro de Personal se liberan equipos asignados y la cuenta vinculada queda **inactiva** (no se elimina el usuario de la base solo por borrar la ficha).

---

## 7.3 Acciones exclusivas o tipicas de Administrador

| Area | Accion |
|------|--------|
| Tickets | Eliminar ticket (sin seguimientos) y eliminar checks |
| Inventario | Dar de baja, reactivar y eliminar equipo cuando las reglas lo permiten |
| Compras | Gestionar **Plantillas** de documentos |
| Catalogos | Eliminar registros de catalogo |
| Gobierno | Matriz de permisos, guia SLA, archivar historial |
| Plataforma | Acceso a Django Admin si tiene privilegio de personal de plataforma |

---

## 7.4 Historial y retencion

1. Consultar **Historial de actividad** para auditoria.
2. Usar **Archivar historial** segun la politica configurada (activo, archivo, purga).
3. Los eventos criticos pueden estar protegidos segun configuracion.

Las tareas automaticas de retencion y recordatorios requieren el proceso de trabajos en segundo plano en el entorno donde corre el sistema.

---

## 7.5 Buenas practicas de gobierno

- Asignar Tecnico IT solo a quien opera TI.
- Revisar periodicamente roles elevados.
- No compartir la cuenta de Administrador.
- Antes de borrar, preferir baja logica (equipos) o desactivacion (personal) cuando baste.
- Verificar plantillas de documentos antes de terminar ordenes en masa.
