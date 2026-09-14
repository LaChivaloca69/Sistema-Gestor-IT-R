# 10. Modulo compras y documentos

---

## 10.1 Proposito

Ordenes de compra (crear o subir), lineas de detalle, generacion de PDF con plantillas, y vinculo al alta de equipos.

---

## 10.2 Conceptos

| Concepto | Modelo |
|----------|--------|
| Orden | `OrdenCompra` |
| Linea | `DetalleOrdenCompra` |
| Plantilla | `PlantillaDocumento` |
| Origen | Creado / Subido |
| Motor PDF | `document_engine.py` |

`fecha` de OC usa `timezone.localdate`.

---

## 10.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Vistas | `views/compras.py` (tambien `mis_equipos`) |
| Forms | `forms/compras.py` |
| Templates | `ordencompra/`, `plantilladocumento/` |
| URLs | `ordencompra_*`, `plantilla_*`, `mis_equipos` |
| Helpers | `user_can_manage_orden`, `user_can_terminar_orden`, `user_can_delete_orden` |

---

## 10.4 Flujos principales

1. Elegir crear o subir.  
2. Capturar cabecera y lineas / archivo.  
3. Terminar (solo operativo): genera PDF via plantilla + conversion si aplica.  
4. Alta de equipos consume cupo de linea con lock.

---

## 10.5 Reglas

- Usuario ve solo ordenes elaboradas por el.  
- Usuario **no** termina ordenes.  
- No borrar si Terminado o si ya tiene equipos ligados (helper).  
- Forms de Usuario pueden restringir cambio de estado (`restrict_estado`).

---

## 10.6 Permisos

| Accion | Quien |
|--------|-------|
| CRUD propio | Usuario (limitado) |
| Ver todas / terminar | Operativo |
| Plantillas | Admin |
| Delete sensible | Helpers + Admin en rutas criticas |

---

## 10.7 Integraciones

Proveedor, Equipo (origen compra), historial, document_engine (LibreOffice si el entorno lo tiene).

---

## 10.8 Puntos delicados

Actualizar OC subida sin reenviar PDF; cupo de lineas en altas concurrentes.

---

## 10.9 Como probar

`UserFailureHardeningTests.test_usuario_no_termina_ni_borra_oc_terminada`, tests de OC en `AltosMantenimientoPersonalComprasTests`.
