# 9. Procesos de inventario

Incluye equipos, perifericos, herramientas, movimientos y asignaciones.

---

## 9.1 Tipos de inventario

| Tipo | Caracteristica |
|------|----------------|
| Equipo | Activo principal asignable (laptop, PC, etc.) |
| Periferico | Puede formar parte de un kit (equipo padre) |
| Herramienta | Inventario de taller; no se asigna a personal como custodia tipica de laptop |

Los **consumibles** se documentan en el capitulo 10 (stock por cantidad).

---

## 9.2 Alta de un equipo

1. Menu **Equipos** (o Perifericos / Herramientas segun el tipo).
2. Capturar codigo de inventario, categoria, datos tecnicos y origen (legado, compra, etc.).
3. Si viene de una orden de compra, vincular la orden y la linea; el sistema controla el cupo de la linea.
4. Queda disponible (En Stock) salvo reglas del flujo.

---

## 9.3 Asignar y devolver

### Asignar

1. Desde el detalle del equipo, **Asignar**.
2. Elegir personal **activo**.
3. El equipo pasa a Asignado. Solo puede existir **una** asignacion activa por equipo.

### Devolver

1. Desde el detalle, **Devolver**.
2. La asignacion queda Devuelta y el equipo vuelve a En Stock si corresponde.

El Usuario ve el resultado en **Mis equipos**. Tambien puede ver el detalle en solo lectura.

---

## 9.4 Ubicacion y movimientos

- Cambiar el espacio fisico genera un movimiento de ubicacion.
- La lista **Movimientos de equipo** muestra el ciclo de vida del activo (alta, asignacion, mantenimiento, etc.).
- El **Historial de actividad** es la auditoria de acciones de usuarios en el sistema (capitulo 14).

---

## 9.5 Kit de perifericos

1. En un equipo principal, vincular perifericos.
2. Al asignar o mover el padre, el kit se contempla en la operacion de custodia.
3. Existen acciones de desvincular o reemplazar periferico segun el caso.

---

## 9.6 Baja, reactivacion y eliminacion

| Accion | Quien | Efecto |
|--------|-------|--------|
| Dar de baja | Administrador | Baja logica; el equipo deja de operar |
| Reactivar | Administrador | Vuelve a operacion |
| Eliminar | Administrador | Borrado fisico solo si no hay historial bloqueante |

No se inicia mantenimiento sobre un equipo en Baja.

---

## 9.7 Panel de inventario

Resume avisos: equipos sin ubicacion, mantenimiento prolongado, asignaciones antiguas, entre otros indicadores operativos.
