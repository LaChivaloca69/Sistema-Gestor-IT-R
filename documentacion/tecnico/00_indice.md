# Manual tecnico — Indice

**Sistema:** Sistema Web para la gestion de inventario y Mesa de ayuda TI  
**Nivel de detalle:** A (mapa de archivos, flujos y reglas; no recorrido linea por linea)  
**Ultima revision:** septiembre 2026

---

## Publico

Quien mantiene o modifica el sistema: desarrolladores, administradores tecnicos y personal de TI que necesite ubicar codigo.

No sustituye el manual de negocio (`documentacion/negocio/`).

---

## Contenido

| Archivo | Tema |
|---------|------|
| `01_arquitectura.md` | Capas, stack y flujo de una peticion |
| `02_mapa_carpetas.md` | Estructura del repositorio y paquetes |
| `03_roles_en_codigo.md` | Groups, helpers y decoradores |
| `04_modulo_organizacion.md` | Areas, puestos, personal, proveedores |
| `05_modulo_ubicaciones.md` | Edificios, zonas, ubicaciones, categorias, mapa |
| `06_modulo_inventario.md` | Equipos, perifericos, herramientas, asignaciones, movimientos, importacion |
| `07_modulo_consumibles.md` | Productos y kardex de stock |
| `08_modulo_tickets.md` | Tickets, checks, comentarios, bitacora |
| `09_modulo_mantenimiento.md` | Ordenes y cierres |
| `10_modulo_compras.md` | Ordenes de compra, plantillas, motor documental |
| `11_modulo_gobierno.md` | Coberturas, solicitudes, matriz, guia SLA |
| `12_historial_auditoria.md` | HistorialActividad y retencion |
| `13_jobs_y_qcluster.md` | django-q2, schedules y tareas |
| `14_formularios_y_permisos.md` | Forms, helpers de permiso y media |
| `15_plantillas_y_estaticos.md` | Templates HTML, CSS/JS, static/media |
| `16_tests_y_calidad.md` | Suites de prueba y puntos de regresion |

---

## Plantilla usada en cada modulo

1. Proposito  
2. Conceptos  
3. Donde esta en el codigo (tabla)  
4. Flujo principal  
5. Reglas de negocio implementadas  
6. Permisos en vistas  
7. Integraciones  
8. Puntos delicados  
9. Como probar  

---

## Relacion con el manual de negocio

| Negocio | Tecnico |
|---------|---------|
| Que hace el usuario en pantalla | Que archivos y reglas lo implementan |
| Casos de uso CU-xx | Referencia cruzada cuando aplica |
