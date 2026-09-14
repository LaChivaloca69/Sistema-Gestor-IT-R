# 16. Avisos y tableros

---

## 16.1 Donde aparecen los avisos

| Lugar | Que muestra |
|-------|-------------|
| Inicio | Indicadores y listas de atencion segun rol |
| Campana del encabezado | Lista de avisos con enlace al listado filtrado |
| Badges del menu | Conteo junto a Tickets, Checks, Mantenimientos, Solicitudes, Consumibles, etc. |
| Paneles | Panel tickets, panel inventario, panel consumibles, dashboards de mantenimiento |

No hay envio de correo.

---

## 16.2 Tipos de aviso frecuentes

| Aviso | Significado | Quien lo ve tipicamente |
|-------|-------------|-------------------------|
| Tickets fuera de SLA | Superaron el tiempo segun prioridad | Operativo (y metricas propias del Usuario) |
| Tickets sin seguimiento | Abiertos sin check registrado | Operativo |
| Checks por atender | Proximo seguimiento vencido o cercano | Operativo |
| Mantenimientos por atender | Fecha programada vencida o cercana | Operativo |
| Avisos de inventario | Sin ubicacion, mant. largo, asignaciones antiguas | Operativo |
| Solicitudes pendientes | Pedidos de equipo por revisar | Operativo |
| Consumibles con stock bajo | Bajo el minimo o agotado | Operativo |

La campana puede mostrar a la vez avisos de SLA y de tickets sin check, y tambien consumibles.

---

## 16.3 Actualizacion de conteos

Los indicadores del menu e Inicio pueden actualizarse con un breve retraso (del orden de menos de un minuto) por cache de metricas. Si un aviso no baja al instante tras resolver un caso, refrescar la pagina o esperar un momento.

---

## 16.4 Calendario

En Inicio, el calendario concentra fechas relevantes de tickets (referencia de SLA), proximos checks y mantenimientos. El alcance de lo mostrado depende del rol.
