# 9. Modulo mantenimiento

---

## 9.1 Proposito

Ordenes formales de mantenimiento sobre un `Equipo`, con inicio, cancelacion, cierre y proximo ciclo.

---

## 9.2 Conceptos

| Concepto | Modelo |
|----------|--------|
| Orden | `Mantenimiento` |
| Cierre | `AgendaMantenimiento` (OneToOne `cierre`) |
| Tipos | Preventivo, Correctivo, Predictivo |
| Estados | Programado, En Proceso, Completado, Cancelado |

Metodos de modelo: `iniciar`, `cancelar`, `marcar_completado`, `reabrir`, propiedades `puede_*`.

---

## 9.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Vistas | `views/mantenimiento.py` |
| Forms | `forms/mantenimiento.py` |
| Templates | `mantenimiento/`, `agendamantenimiento/` |
| URLs | `mantenimiento_*`, `agendamantenimiento_*` |
| Sync equipo | `_sync_equipo_inicio_mantenimiento`, `_sync_equipo_fin_mantenimiento` |

---

## 9.4 Flujos principales

1. Crear mantenimiento (estado Programado).  
2. Iniciar: En Proceso + equipo En Mantenimiento + movimiento.  
3. Cerrar via `AgendaMantenimientoForm`:  
   - si estaba Programado, `iniciar` y luego `marcar_completado`;  
   - sync de inicio (si aplica) y fin del equipo;  
   - IntegrityError si ya existe cierre (double submit).  
4. Opcional: crear proximo ciclo por fecha.

---

## 9.5 Reglas

- `puede_completar` exige En Proceso y sin cierre; el form puede iniciar antes de completar.  
- No iniciar sobre equipo en Baja.  
- Si otro mantenimiento sigue En Proceso, no restaurar estado del equipo al cerrar uno.  
- Eliminar: Admin.

---

## 9.6 Permisos

Operativo en rutas de mantenimiento/agenda; deletes admin.

---

## 9.7 Integraciones

Equipo, movimientos, historial, avisos home/nav, calendario.

---

## 9.8 Puntos delicados

Cierre desde Programado debe dejar traza de inicio (movimiento) aunque sea instantaneo.

---

## 9.9 Como probar

`AltosMantenimientoPersonalComprasTests`, `UserFailureHardeningTests.test_cierre_desde_programado_inicia_y_completa`.
