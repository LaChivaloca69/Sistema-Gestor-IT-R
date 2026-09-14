# 12. Historial y auditoria

---

## 12.1 Proposito

Registrar actividad del sistema (quien, que, cuando, modulo) y aplicar retencion (archivar / purgar).

---

## 12.2 Conceptos

| Concepto | Modelo / API |
|----------|--------------|
| Evento | `HistorialActividad` |
| Modulo / accion / nivel | `ModuloHistorial`, `AccionHistorial`, `NivelHistorial` |
| API escritura | `historial.registrar_historial`, `registrar_creacion`, `registrar_actualizacion`, `registrar_eliminacion` |
| Enlace | `enlace_nombre` + `enlace_pk` resueltos con `resolver_enlace` |

---

## 12.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Servicio | `GestorApp/historial.py` |
| Listado / detalle | `views/movimiento.py` (`historial_actividad_list`, `historial_actividad_detail`) |
| UI retencion | `views/organizacion.py` (`historial_retencion_admin`) |
| Templates | `historial/list.html`, `auditoria_detail.html`, `retencion.html` |
| URLs | `historial_actividad_list` (`/Auditoria/`), `historial_actividad_detail`, `historial_retencion_admin` |
| Redirect legado | `/MovimientoEquipos/` redirige al listado de auditoria |

**No confundir** con `movimientoequipo_registros` (ciclo de vida del activo).

---

## 12.4 Flujo de escritura

1. Vista o tarea llama `registrar_*`.  
2. Se guarda titulo, descripcion, usuario, etiquetas de objeto, metadata JSON.  
3. En listados se intenta armar URL segura; si el name no acepta pk, se degrada sin tumbar la pagina.

---

## 12.5 Retencion

Configuracion `HISTORIAL_RETENCION` en settings:

| Clave | Default tipico |
|-------|----------------|
| `modo` | `archivar_luego_purgar` |
| `dias_activo` | 180 |
| `dias_archivo` | 365 |
| `proteger_criticos` | True |

Ejecucion: schedule diario, comando `limpiar_historial`, o pantalla Admin.

---

## 12.6 Permisos

Listado/detalle: operativo. Archivar: admin.

---

## 12.7 Integraciones

Casi todos los CRUD; tasks de retencion y recordatorios; invalidacion de metrics cache tras retencion.

---

## 12.8 Puntos delicados

Nivel critico no se archiva/purga si `proteger_criticos`. Fingerprint de recordatorios evita spam de eventos identicos.

---

## 12.9 Como probar

`AuditoriaHistorialTests`.
