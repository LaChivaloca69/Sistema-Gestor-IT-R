# 14. Procesos de gobierno y auditoria

---

## 14.1 Coberturas

Ver tambien el capitulo de soporte. Puntos de gobierno:

- evitan dejar tickets sin atencion durante ausencias;
- no deben solaparse coberturas activas del mismo ausente;
- el Administrador supervisa el listado completo.

---

## 14.2 Matriz de permisos y guia SLA

| Pantalla | Uso |
|----------|-----|
| Matriz permisos | Consulta de capacidades por rol |
| Como funciona el SLA | Explica tiempos por prioridad (solo Administrador) |

No sustituyen la asignacion real de roles en Personal.

---

## 14.3 Historial de actividad

Menu **Historial de actividad** (antes confundido con la lista de movimientos de equipo).

Permite filtrar por modulo, usuario, accion, nivel, fechas y estado (activo o archivado).

Cada evento puede abrir un detalle y, si existe, un enlace al objeto relacionado.

Los **movimientos de equipo** siguen en su propia opcion de menu y describen el ciclo fisico del activo.

---

## 14.4 Archivar historial

Solo Administrador.

Aplica la politica de retencion configurada:

1. Los eventos antiguos dejan de mostrarse como activos (archivo).
2. Mas adelante pueden purgarse segun dias configurados.
3. Los eventos criticos pueden protegerse.

Conviene ejecutar o supervisar esta tarea con criterio; es irreversible en la fase de purga.

---

## 14.5 Panel Django Admin

Herramienta tecnica de plataforma para Administradores con privilegio de personal. No es la interfaz principal de negocio; se usa con precaucion.
