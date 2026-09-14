# 16. Tests y calidad

---

## 16.1 Ubicacion

Suite principal: `GestorApp/tests.py`.

Ejecucion tipica:

```text
python manage.py test GestorApp.tests --keepdb
```

En entornos con base de prueba ya creada, `--keepdb` evita prompts interactivos de destruccion.

---

## 16.2 Clases principales

| Clase | Enfoque |
|-------|---------|
| `AuthFlowTests` | Login / signup (con override de `SIGNUP_ENABLED`) |
| `SmokeFlowTests` | Humo de pantallas basicas |
| `EquipoFormCriticosTests` | Formulario equipo / tags / estados |
| `AltosMantenimientoPersonalComprasTests` | Mant., personal, OC |
| `AuditoriaHistorialTests` | Listado y detalle de historial |
| `MediaHardeningTests` | Uploads maliciosos / limites |
| `TicketCreateEquipoChoicesTests` | Equipos elegibles al crear ticket |
| `SolicitudEquipoSeguimientoTests` | Solicitudes |
| `BitacoraAnswerFlowTests` | Bitacora |
| `TicketCierreLimpiaPendientesTests` | Cierre limpia checks |
| `TicketComentarioTests` | Comentarios y confirmacion delete |
| `PropagarCustodiaPersonalTests` | Ubicacion / custodia |
| `InventarioImportTests` | Importacion |
| `SlaGuiaAdminTests` | Guia SLA solo Admin |
| `TicketSelectorProblemaTests` | Selector de problemas |
| `MisEquiposViewTests` | Mis equipos |
| `QueryOptimizationTests` | Anotaciones / N+1 |
| `SecurityAndUIFixesTests` | Redirects de permiso (assertRedirects a home) |
| `UserFailureHardeningTests` | Abusos de usuario autenticado |

---

## 16.3 Criterios de calidad observados en codigo

- Permisos denegados deben ser **302 a home/login**, no un 500 silencioso.  
- Folios unicos con reintento ante carrera.  
- Constraints de BD donde el negocio lo exige (asignacion activa).  
- Forms que no confian en campos forjados del cliente.  
- Confirmacion antes de borrar comentarios.

---

## 16.4 Relacion con documentacion

Al cambiar un modulo, actualizar:

1. Capitulo tecnico correspondiente.  
2. Caso de uso de negocio si cambia la capacidad visible.  
3. Test de regresion en la clase adecuada.
