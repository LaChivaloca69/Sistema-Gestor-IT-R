# 11. Modulo gobierno

---

## 11.1 Proposito

Coberturas entre tecnicos, solicitudes de equipo, matriz de permisos y guia SLA (documentacion en UI).

Archivo de vistas dedicado: `GestorApp/gobierno_views.py` (no esta bajo `views/`).

---

## 11.2 Conceptos

| Concepto | Modelo |
|----------|--------|
| Cobertura | `CoberturaTickets` |
| Solicitud | `SolicitudEquipo` (+ folio `SOL-`) |
| Revision | `SeguimientoSolicitudEquipo` / forms de decision |
| Matriz | `permissions_matrix.py` |
| Guia SLA | `sla_guide.py` |

---

## 11.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Vistas | `gobierno_views.py` |
| Forms | `forms/gobierno.py` |
| Cobertura helpers | `cobertura.py` |
| Templates | `gobierno/` |
| URLs | `cobertura_*`, `solicitud_equipo_*`, `permisos_matriz`, `sla_guia` |
| Helpers | `user_can_manage_cobertura`, `_crear_asignacion_activa` al completar |

---

## 11.4 Flujos principales

### Cobertura

Alta con ausente/suplente/fechas. Listado filtrado: no admin solo ve las suyas (ausente, suplente o creador). Validacion de solape en `clean` del modelo y del form.

### Solicitud

Usuario crea; operativo decide y puede asignar equipo disponible (transaccion con candado de asignacion).

### Matriz / SLA

Solo Admin; pantallas de lectura.

---

## 11.5 Reglas

- Ausente != suplente; fin >= inicio.  
- No dos coberturas activas solapadas del mismo ausente.  
- Tecnico solo gestiona coberturas donde participa (salvo Admin).  
- Folio de solicitud unico con reintento (mismo patron que tickets).  
- Solicitud completada no se cancela.

---

## 11.6 Permisos

| Pantalla | Decorador / helper |
|----------|--------------------|
| Coberturas | `operativo_required` + queryset/helper |
| Solicitudes | `login_required` + filtros |
| Matriz / SLA | `admin_required` |

---

## 11.7 Integraciones

Tickets (cobertura), inventario (asignacion), historial, badges de solicitudes.

---

## 11.8 Puntos delicados

Enlace de historial debe usar nombres de URL que acepten pk (`cobertura_update`, no list + pk incorrecto).

---

## 11.9 Como probar

`SolicitudEquipoSeguimientoTests`, `UserFailureHardeningTests` (folio, cobertura solape, tecnico no edita ajena), `SlaGuiaAdminTests`.
