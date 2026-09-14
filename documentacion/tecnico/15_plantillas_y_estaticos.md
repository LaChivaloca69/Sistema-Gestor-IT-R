# 15. Plantillas HTML y estaticos

---

## 15.1 Templates

Ubicacion principal: `GestorApp/Templates/`.

Organizacion por dominio (`ticketit/`, `equipo/`, `historial/`, `gobierno/`, `partials/`, etc.). Layout base: `base.html` (menu lateral segun flags de rol y badges).

Partials reutilizables: cabeceras de pagina, filtros, empty states, row actions, hints.

Confirmaciones de borrado: patron `confirm_delete.html` por entidad; comentarios usan `ticketit/comentario_confirm_delete.html`.

---

## 15.2 Context processors

Registrados en settings:

- `roles`  
- `breadcrumbs`  
- `nav_badges`  
- `inventario_nav`  

---

## 15.3 Estaticos

| Ruta | Uso |
|------|-----|
| `static/GestorApp/css/` | Estilos de la app |
| `static/GestorApp/js/app.js` | UX (ataljos, confirmaciones de forms de borrado, etc.) |
| `STATICFILES_DIRS` | Apunta a `static/` del proyecto |

En produccion tipica se define `STATIC_ROOT` y `collectstatic` (no documentado aqui como despliegue LAN).

---

## 15.4 Media

`MEDIA_ROOT` / `MEDIA_URL`. En desarrollo, `urls.py` sirve media solo si `DEBUG=True`.

---

## 15.5 Breadcrumbs

`breadcrumbs.py` mapea `url_name` a titulos y padres; resuelve etiquetas de detalle desde modelos cuando hay pk.
