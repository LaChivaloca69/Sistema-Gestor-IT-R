# 14. Formularios, permisos finos y media

---

## 14.1 Formularios

Paquete `GestorApp/forms/` paralelo a dominios. `forms/common.py` concentra helpers como resolucion de Personal del usuario.

Patrones frecuentes:

- Filtrar querysets segun rol (`is_operativo`).  
- Forzar campos de auditoria (`usuario = request_user`).  
- `tipo_fijo` en movimientos de stock.  
- `restrict_estado` en OC de Usuario.  
- Validaciones de solape en coberturas.

---

## 14.2 Helpers de permiso (`views/helpers.py`)

Ademas de decoradores de URL, el objeto se filtra o se niega con helpers. Ejemplos:

| Helper | Uso |
|--------|-----|
| `user_can_view_ticket` / `edit` / `delete` | Tickets |
| `user_can_comment_ticket` / `delete_comentario` | Hilo |
| `user_can_view_equipo` | Detalle inventario |
| `user_can_manage_orden` / `terminar` / `delete` | Compras |
| `user_can_manage_cobertura` | Gobierno |

---

## 14.3 Media segura

`media_security.py` + `MEDIA_UPLOAD` en settings:

- Limites de tamano por tipo.  
- Extensiones permitidas.  
- Rechazo de ejecutables disfrazados.  
- Renombrado seguro de rutas.

Vistas de tickets, equipos y plantillas delegan validacion al subir.

---

## 14.4 Cache de metricas

`metrics_cache.py` + `nav_badges.py` + KPIs de `home.py`:

- LocMem por proceso.  
- TTL corto (`METRICS_CACHE_TTL`).  
- Invalidacion por version tras ciertos jobs.

En varios workers WSGI la cache no es compartida.

---

## 14.5 Como probar

`MediaHardeningTests`, `QueryOptimizationTests`, pruebas de hardening de usuario y seguridad UI.
