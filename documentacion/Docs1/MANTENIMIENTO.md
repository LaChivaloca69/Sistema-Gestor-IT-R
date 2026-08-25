# Mantenimiento y Cierres — Guía de funcionamiento

Documento de **Mantenimientos** y **Cierres** (modelo `AgendaMantenimiento`). **Última revisión:** agosto 2026.

---

## 1. Resumen

Se reforzó el ciclo de vida del mantenimiento, la sincronización con el equipo, los avisos en home/dashboard (sin email), la UX de listas y un panel operativo con próximo ciclo automático al cerrar.

| Área | Qué se hizo |
|------|-------------|
| Flujo y estados | Iniciar, Cerrar/Completar, Cancelar, Reabrir; estado no editable a mano |
| Detalle | Vista única con equipo, fechas, técnico y panel de cierre |
| Equipo | Al iniciar → En Mantenimiento; al completar/cancelar → restaura + movimiento |
| Avisos | Vencidos, por vencer (7 días), próximo ciclo (panel, sin email) |
| UX lista | Búsqueda, filtros, orden, paginación, CTA Cerrar |
| Cierre claro | “Agenda” renombrada a **Cierres** en la UI |
| Dashboard | Conteos por estado/tipo, costos, vencidos, ciclos |
| Próximo ciclo | Al cerrar con `proxima_fecha`, programa el siguiente (opcional) |

**Importante:** las notificaciones son solo avisos en **home**, **lista** y **dashboard**. No se envía correo.

---

## 2. Conceptos

### Mantenimiento (`Mantenimiento`)
Orden de trabajo sobre un equipo. Folio `MAN###-MMDDYY` (según `pk` y fecha programada).

### Cierre (`AgendaMantenimiento`)
Registro de ejecución: fechas inicio/fin, acciones, observaciones y **próxima fecha**.  
En código/URLs sigue el nombre histórico `AgendaMantenimiento`; en la UI se muestra como **Cierre**.

### Roles
El módulo de mantenimiento es **operativo** (`operativo_required`: Tecnico IT o Administrador).  
Borrar mantenimiento o cierre: **solo Admin** (`admin_required`). El Usuario pide mantenimiento con ticket tipo **MANTENIMIENTO**, no opera este módulo.

---

## 3. Flujo de estados

Estados: **Programado** → **En Proceso** → **Completado** / **Cancelado** (y reabrir).

```
Programado
   │  Iniciar
   ▼
En Proceso
   │  Registrar cierre ──────────────┐
   │                                 ▼
   │                            Completado
   │  Cancelar
   ▼
Cancelado

Completado / Cancelado
   │  Reabrir
   ▼
En Proceso (si había cierre) o Programado
```

### Reglas
- El campo **Estado no se edita a mano** en el formulario; lo mueven las acciones.
- **Iniciar:** solo desde Programado → En Proceso.
- **Cerrar / Completar:** vía formulario de cierre; exige acciones realizadas y fecha fin.
- **Cancelar:** desde Programado o En Proceso.
- **Reabrir:** desde Completado o Cancelado.

### Sincronización con equipo
| Acción | Efecto en equipo |
|--------|------------------|
| Iniciar | Estado → `En Mantenimiento` + movimiento |
| Completar / Cancelar | Restaura **En Stock** o Asignado (según asignación activa) + movimiento |
| Si otro mantenimiento del mismo equipo sigue En Proceso | No restaura aún |

---

## 4. Vista detalle

Ruta: `/MantenimientoEquipos/<id>/`

- Datos del mantenimiento y estado del equipo.
- Panel **Cierre** (pendiente o registrado).
- Acciones según estado: Iniciar, Registrar cierre, Cancelar, Reabrir, Editar, Eliminar.
- Tras crear/editar → redirige al detalle.

---

## 5. Avisos en home (sin email)

Solo operativo. Ventana de aviso corto: **7 días**. KPI de próximos activos: **30 días**.

| Aviso | Criterio |
|-------|----------|
| **Vencido** | Programado / En Proceso con `fecha_programada` &lt; hoy |
| **Por vencer** | Mismos estados, fecha entre hoy y hoy+7 |
| **Próximo ciclo** | Cierre completado con `proxima_fecha_mantenimiento` en ventana, y el equipo **no** tiene mantenimiento abierto |

El KPI “próximos 30 días” **solo cuenta activos** (ya no incluye Completado/Cancelado).

Aparecen en:
- KPI del home
- Banners de alerta
- Tabla “Mantenimientos por atender”
- Filtros de la lista (`?alerta=vencidos|proximos|atencion|ciclo`)

---

## 6. UX de lista

### Mantenimientos (`/MantenimientoEquipos/`)
- Búsqueda: folio (núm.), equipo, técnico, falla, tipo.
- Filtros: aviso, estado, tipo, equipo, técnico, rango de fechas.
- Orden: fecha programada asc/desc, recientes, estado, equipo.
- Columna **Aviso** (Vencido / Hoy / Por vencer / ciclo).
- CTA principal **Cerrar** si se puede completar; si no, **Abrir**.
- Paginación (20).
- Enlaces a **Dashboard** y **Cierres**.

### Cierres (`/AgendaMantenimiento/`)
- Título y menú: **Cierres** (ya no “Agenda”).
- Búsqueda y paginación.
- Enlace al detalle del mantenimiento; editar/eliminar cierre.

---

## 7. Próximo ciclo automático

Al **Registrar cierre** (o editar cierre con la opción activa):

1. Si hay `proxima_fecha_mantenimiento` y el checkbox  
   **Crear próximo mantenimiento automáticamente** está marcado:
2. Se crea un mantenimiento **Programado** (tipo **Preventivo**; si el origen era Correctivo, el ciclo también pasa a Preventivo).
3. Copia técnico del origen; descripción: `Ciclo automatico tras MAN…`.
4. **No duplica** si el equipo ya tiene uno Programado/En Proceso, o uno Programado en esa misma fecha.
5. Si se creó, redirige al detalle del nuevo mantenimiento y deja historial.

En **crear cierre** el checkbox viene **marcado** por defecto.  
En **editar cierre** viene **desmarcado** (evita ciclos accidentales).

---

## 8. Dashboard de mantenimientos

Ruta: `/MantenimientoEquipos/dashboard/`

También desde lista, home (sección de avisos) y accesos rápidos.

### Contenido
- KPI: activos, vencidos, por vencer, próximos ciclos.
- Totales, próximos 30 días (solo activos), costo completados / activos.
- Por estado y por tipo (con enlaces filtrados).
- Equipos con más mantenimientos.
- Listas de vencidos y de próximos ciclos.

---

## 9. Rutas principales

| Ruta | Nombre | Quién |
|------|--------|--------|
| `/MantenimientoEquipos/` | `mantenimiento_list` | Operativo |
| `/MantenimientoEquipos/dashboard/` | `mantenimiento_dashboard` | Operativo |
| `/MantenimientoEquipos/create/` | `mantenimiento_create` | Operativo |
| `/MantenimientoEquipos/<id>/` | `mantenimiento_detail` | Operativo |
| `/MantenimientoEquipos/update/<id>/` | `mantenimiento_update` | Operativo |
| `/MantenimientoEquipos/delete/<id>/` | `mantenimiento_delete` | Admin |
| `/MantenimientoEquipos/<id>/iniciar/` | `mantenimiento_iniciar` | Operativo |
| `/MantenimientoEquipos/<id>/cancelar/` | `mantenimiento_cancelar` | Operativo |
| `/MantenimientoEquipos/<id>/reabrir/` | `mantenimiento_reabrir` | Operativo |
| `/AgendaMantenimiento/` | `agendamantenimiento_list` | Operativo (UI: Cierres) |
| `/AgendaMantenimiento/create/` | `agendamantenimiento_create` | Operativo |
| `/AgendaMantenimiento/update/<id>/` | `agendamantenimiento_update` | Operativo |
| `/AgendaMantenimiento/delete/<id>/` | `agendamantenimiento_delete` | Admin |

Prefill al programar desde un ciclo:  
`/MantenimientoEquipos/create/?equipo=<id>&fecha=YYYY-MM-DD`

---

## 10. Archivos clave

| Archivo | Rol |
|---------|-----|
| `GestorApp/models.py` | `Mantenimiento`, `AgendaMantenimiento`, estados, métodos de flujo |
| `GestorApp/views/mantenimiento.py` | CRUD, sync equipo, avisos, lista, dashboard, ciclo automático |
| `GestorApp/forms/mantenimiento.py` | Forms de orden y cierre |
| `GestorApp/historial.py` | Historial (incluye serialización de fechas en metadata) |
| `GestorIT/urls.py` | Rutas |
| `GestorApp/Templates/mantenimiento/` | list, detail, form, dashboard, confirm_delete |
| `GestorApp/Templates/agendamantenimiento/` | list, form, confirm_delete (UI “Cierres”) |
| `GestorApp/Templates/home.html` | KPIs y alertas de mantenimiento |
| `GestorApp/Templates/base.html` | Sidebar Mantenim. / Cierres |

Constantes en vistas:
- `MANTENIMIENTO_ALERTA_DIAS = 7`
- `MANTENIMIENTO_PROXIMOS_DIAS = 30`
- `MANTENIMIENTO_LIST_PAGE_SIZE = 20`

---

## 11. Cómo usarlo (día a día)

1. Revisa **home**: vencidos, por vencer y próximos ciclos.
2. Abre el **Dashboard** para priorizar.
3. **Programa** un mantenimiento (o usa el botón Programar desde un ciclo pendiente).
4. Cuando toque: **Iniciar** → el equipo pasa a En Mantenimiento.
5. **Registrar cierre** (acciones + fecha fin; opcional próxima fecha + ciclo automático).
6. El equipo se restaura; si se creó el próximo ciclo, ya queda Programado.
7. Si hace falta, **Reabrir** o **Cancelar**.

---

## 12. Fuera de alcance (aún no)

- Notificaciones por **email**.
- Técnico como FK a User/Proveedor (sigue siendo texto).
- Permisos finos para no-operativo (p. ej. ver solo sus equipos).
- Soft-delete.
- Renombrar modelo/URLs `AgendaMantenimiento` en código (solo UI).

Cuando se activen correos, conviene reutilizar los mismos criterios de aviso que ya existen en home/lista/dashboard.
