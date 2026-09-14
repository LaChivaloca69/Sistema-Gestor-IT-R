# 11. Procesos de mantenimiento

---

## 11.1 Diferencia con el ticket de mantenimiento

| Via | Uso |
|-----|-----|
| Ticket tipo MANTENIMIENTO | El usuario pide ayuda por la mesa de ayuda |
| Modulo Mantenimientos | Orden formal sobre un equipo (programacion y cierre) |

Ambas pueden coexistir; la orden formal es la que cambia el estado del equipo a En Mantenimiento al iniciar.

---

## 11.2 Programar

1. Menu **Mantenimientos**, crear.
2. Elegir equipo, tipo (preventivo, correctivo, predictivo), fecha y responsable.
3. Estado inicial: **Programado**.

---

## 11.3 Iniciar

1. Accion **Iniciar**.
2. Estado: **En Proceso**.
3. El equipo pasa a **En Mantenimiento** y se registra movimiento.

No se inicia si el equipo esta en Baja.

---

## 11.4 Cerrar

1. Desde el detalle o desde **Cierres de mantenimiento**.
2. Registrar fechas, acciones realizadas y observaciones.
3. El mantenimiento queda **Completado**.
4. El equipo vuelve a En Stock o Asignado si no hay otro mantenimiento en proceso.

Tambien es valido cerrar un mantenimiento aun **Programado**: el sistema lo inicia y lo completa en el mismo procedimiento, dejando trazabilidad de inicio y fin.

Opcionalmente se indica la **proxima fecha** para generar el siguiente ciclo.

---

## 11.5 Cancelar y reabrir

- Cancelar: desde Programado o En Proceso.
- Reabrir: desde Completado o Cancelado, segun reglas de pantalla.

Eliminar mantenimiento o cierre: Administrador.
