# 7. Modulo consumibles

---

## 7.1 Proposito

Inventario por cantidad (SKU + stock), distinto del activo unitario.

---

## 7.2 Conceptos

| Concepto | Modelo |
|----------|--------|
| Producto | `ProductoConsumible` |
| Movimiento | `MovimientoStock` |
| Tipos movimiento | Entrada, Salida, Ajuste (`TipoMovimientoStock`) |
| Unidad | `UnidadConsumible` |

La categoria debe ser tipo consumible.

---

## 7.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Vistas | `views/consumibles.py` |
| Forms | `forms/consumibles.py` |
| Templates | `consumible/` |
| URLs | `producto_consumible_*`, `movimiento_stock_list`, `consumible_dashboard` |
| Badges | `nav_badges.py` (alerta stock bajo) |

---

## 7.4 Flujo principal

1. Alta de producto con stock minimo.  
2. Registrar movimiento (entrada/salida/ajuste segun pantalla).  
3. Actualizar `stock_actual`.  
4. Listar / dashboard filtrando stock bajo.

---

## 7.5 Reglas

- `MovimientoStockForm` con `tipo_fijo` fuerza el tipo en `clean` (no se puede forjar otro tipo en POST).  
- Alertas cuando stock actual <= minimo (o agotado segun query de alerta).

---

## 7.6 Permisos

Solo operativo (`operativo_required` en URLs).

---

## 7.7 Integraciones

Campana/nav badges; categorias de inventario; historial de operaciones relevantes.

---

## 7.8 Puntos delicados

No mezclar con `Equipo`: son modelos y menús distintos.

---

## 7.9 Como probar

`UserFailureHardeningTests.test_tipo_fijo_ignora_ajuste_forjado`.
