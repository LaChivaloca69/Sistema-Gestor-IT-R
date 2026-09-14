# 5. Modulo ubicaciones

---

## 5.1 Proposito

Modelar el espacio fisico y las categorias de inventario; ofrecer navegacion por mapa de sedes.

---

## 5.2 Conceptos

| Concepto | Modelo |
|----------|--------|
| Edificio | `Edificio` |
| Zona | `ZonaEdificio` (FK edificio) |
| Espacio | `Ubicacion` (FK zona; flag stock default) |
| Categoria | `CategoriaEquipo` + `TipoCategoriaInventario` (equipo, periferico, herramienta, consumible) |

---

## 5.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Vistas | `GestorApp/views/ubicaciones.py` |
| Forms | `GestorApp/forms/ubicaciones.py` |
| Templates | `edificio/`, `zonaedificio/`, `ubicacion/`, `categoriaequipo/`, `espacios/` |
| URLs | `edificio_*`, `zonaedificio_*`, `ubicacion_*`, `categoriaequipo_*`, `mapa_sedes` |
| Helpers stock | `views/helpers.py` (`_get_espacio_stock_default`, etc.) |

---

## 5.4 Flujo principal

1. Alta de edificio, zonas y ubicaciones.  
2. Marcar una ubicacion como stock por defecto si el flujo de devolucion lo requiere.  
3. Categorias tipan el inventario y limitan querysets (equipo vs consumible).  
4. Mapa de sedes agrega la jerarquia y equipos por lugar.

---

## 5.5 Reglas

- Zona pertenece a un edificio; la ubicacion a una zona.  
- El tipo de categoria condiciona pantallas de alta (`inventory_types.py`).  
- Eliminacion de catalogos: Administrador.

---

## 5.6 Permisos

CRUD operativo; deletes admin en rutas `admin_required`.

---

## 5.7 Integraciones

Equipo.ubicacion, Personal.ubicacion, movimientos de cambio de ubicacion, devoluciones a stock default.

---

## 5.8 Puntos delicados

Filtros de zona por edificio en formularios; evitar ubicaciones huerfanas de contexto.

---

## 5.9 Como probar

Crear edificio/zona/ubicacion, asignar a un equipo, verificar mapa y listados filtrados.
