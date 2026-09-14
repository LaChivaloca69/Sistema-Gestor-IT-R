# 10. Procesos de consumibles

---

## 10.1 Concepto

Un consumible es un producto con **stock por cantidad** (por ejemplo cables o alcohol). No se gestiona como una pieza con numero de serie individual.

---

## 10.2 Quien lo usa

Tecnico IT y Administrador. El Usuario no opera este modulo.

---

## 10.3 Alta de producto

1. Menu **Consumibles**.
2. Crear producto con SKU, nombre, categoria de tipo consumible, unidad y stock minimo.
3. El stock actual se alimenta con movimientos.

---

## 10.4 Movimientos de stock

| Tipo | Uso |
|------|-----|
| Entrada | Ingreso de material |
| Salida | Consumo o entrega |
| Ajuste | Correccion controlada cuando la pantalla lo permita |

En pantallas con tipo fijo (por ejemplo solo salida), el sistema ignora intentos de forzar otro tipo desde el navegador.

---

## 10.5 Alertas

Cuando el stock esta bajo o agotado respecto al minimo:

- aparece aviso en la campana (operativo);
- se puede filtrar el listado por alerta de stock bajo;
- conviene reponer o ajustar el minimo.

---

## 10.6 Panel de consumibles

Muestra el panorama de productos con problemas de stock y facilita priorizar reposiciones.
