# Renombres de menú y módulos

Documentación de la auditoría de nombres (secciones e ítems del menú lateral) y de los cambios de etiquetas UI aplicados.

**Fecha:** agosto 2026  
**Alcance:** solo etiquetas visibles (menú, breadcrumbs, títulos de página, matriz de permisos, badges y textos relacionados).  
**Fuera de alcance:** renombrar modelos Django, URLs, migraciones o nombres de código interno.

Relacionado: `ORGANIZACION_Y_MAPA_SEDES.md`, `MODULOS.md`, `TICKETS.md`, `MANTENIMIENTO.md`.

Archivos principales tocados:

- `GestorApp/Templates/base.html` — menú lateral
- `GestorApp/breadcrumbs.py` — migas de pan
- Templates de listado/detalle afectados (headers y `{% block title %}`)
- `GestorApp/permissions_matrix.py`
- `GestorApp/nav_badges.py`
- `GestorApp/Templates/home.html` (calendario / avisos)

---

## 1. Criterios de la auditoría

| Criterio | Qué se buscó |
|----------|----------------|
| Claridad | Que el nombre diga *qué* es sin depender del color o de la sección |
| Redundancia | Evitar dos entradas que parezcan lo mismo |
| Consistencia menú ↔ breadcrumb | Misma sección y mismo rótulo |
| Alineación con el calendario | Mismos términos (p. ej. Checks, movimientos de equipo) |
| Sin jerga interna | Evitar nombres solo entendibles por quien implementó el módulo |

---

## 2. Secciones del menú (sin cambio de nombre)

Las **secciones** se mantienen:

| Sección | Contenido |
|---------|-----------|
| **General** | Inicio, Calendario, Mis equipos, Solicitudes de equipo |
| **Soporte** | Tickets, paneles y flujo operativo de soporte |
| **Compras** | Ordenes, Plantillas |
| **Inventario** | Catálogo de activos y stock |
| **Operaciones** | Mantenimiento, asignaciones, historial |
| **Organizacion** | Departamentos, Puestos, Personal |
| **Espacios fisicos** | Mapa de sedes |
| **Admin** | Roles, retención, matriz de permisos |

---

## 3. Tabla de renombres (ítems)

| Antes | Después | Motivo |
|-------|---------|--------|
| Solicitudes | **Solicitudes de equipo** | Evitar confusión con tickets de soporte |
| Seguimiento | **Checks** | Alinear con calendario y folios de check |
| Dashboard (Soporte) | **Panel tickets** | Distinguir de otros paneles |
| Dashboard (Inventario) | **Panel inventario** | Idem |
| Dashboard (Mantenimientos)* | **Panel mantenimientos** | Idem (*breadcrumb / título de página; no es ítem propio del menú) |
| Movimientos | **Movimientos de equipo** | Distinguir del kardex de consumibles y del filtro del calendario |
| Cierres | **Cierres de mantenimiento** | Evitar leer “cierre” como cierre de ticket o de caja |
| Auditoria | **Historial de actividad** | Describe el listado real (caja negra del sistema) |
| Coberturas | **Cobertura de tickets** | Deja claro que es suplencia de tickets |
| Bajar roles | **Quitar roles** | Menos informal / menos agresivo |
| Archivar | **Archivar historial** | Indica *qué* se archiva |

### Nombres que se mantuvieron (claros)

Inicio, Calendario, Mis equipos, Tickets, Bitacora, Respuestas, Ordenes, Plantillas, Equipos, Perifericos, Herramientas, Consumibles, Categorias, Proveedores, Mantenimientos, Asignaciones, Departamentos, Puestos, Personal, Mapa de sedes, Matriz permisos.

---

## 4. Menú actual (mapa)

```
General
  ├── Inicio
  ├── Calendario
  ├── Mis equipos
  └── Solicitudes de equipo

Soporte
  ├── Tickets
  ├── Panel tickets
  ├── Checks
  ├── Bitacora
  ├── Respuestas
  └── Cobertura de tickets

Compras
  ├── Ordenes
  └── Plantillas

Inventario
  ├── Equipos
  ├── Perifericos
  ├── Herramientas
  ├── Consumibles
  ├── Panel inventario
  ├── Categorias
  ├── Proveedores
  └── Movimientos de equipo

Operaciones
  ├── Mantenimientos
  ├── Cierres de mantenimiento
  ├── Asignaciones
  └── Historial de actividad

Organizacion
  ├── Departamentos
  ├── Puestos
  └── Personal

Espacios fisicos
  └── Mapa de sedes

Admin
  ├── Quitar roles
  ├── Archivar historial
  └── Matriz permisos
```

---

## 5. Ajustes de breadcrumbs (sección)

Antes había desalineación menú ↔ migas:

| Módulo | Breadcrumb antes | Breadcrumb después |
|--------|------------------|--------------------|
| Solicitudes de equipo | Inventario | **General** |
| Cobertura de tickets | Gobierno | **Soporte** |
| Checks | Soporte / “Seguimiento” | Soporte / **Checks** |
| Movimientos de equipo | Inventario / “Movimientos” | Inventario / **Movimientos de equipo** |
| Historial de actividad | Operaciones / “Auditoria” | Operaciones / **Historial de actividad** |
| Cierres de mantenimiento | Operaciones / “Cierres” | Operaciones / **Cierres de mantenimiento** |
| Quitar roles / Archivar historial | Admin (rótulos viejos) | Admin (rótulos nuevos) |

También se actualizaron rótulos de create/update/delete asociados (p. ej. “Nuevo check”, “Editar check”).

---

## 6. Pantallas y textos relacionados

Además del menú, se alinearon títulos y cabeceras donde el usuario veía el nombre antiguo:

| Pantalla / zona | Cambio relevante |
|-----------------|------------------|
| Panel de tickets | Título y header |
| Checks de tickets | Título, empty state, paginación |
| Cobertura de tickets | Título y header de listado |
| Panel de inventario | Título y header |
| Historial de actividad | Listado y detalle |
| Archivar historial | Título y header de retención |
| Quitar roles | Título y header |
| Cierres / panel de mantenimientos | Enlaces y títulos |
| Movimientos de equipo | Enlace cruzado hacia historial |
| Calendario (home) | Chip “Movimientos de equipo”; “Checks por atender”; texto de cobertura |
| Lista de tickets | Filtro “Sin check” |
| Badges de navegación | “ticket(s) sin check”, “check(s) por atender” |
| Matriz de permisos | Acciones y módulos renombrados (Cobertura en Soporte; Admin para roles/historial) |

---

## 7. Decisiones conscientes (sin cambio de ubicación)

Estos puntos se evaluaron y **no** se movieron de sección en esta iteración:

| Caso | Decisión |
|------|----------|
| Espacios fisicos con un solo ítem | Se mantiene la sección (eje físico importante) |
| Asignaciones vs Mis equipos vs asignar desde equipo | Se mantienen las tres entradas; roles distintos |
| Proveedores en Inventario | Se dejan en Inventario (también sirven a compras, pero el catálogo es de activos) |
| Bitacora vs Respuestas | Se mantienen ambos (flujos distintos); unificación pendiente si se decide más adelante |

---

## 8. Entidades de dominio (UI vs código)

Los nombres de **entidades** en pantallas de organización/espacios ya estaban alineados; no se renombraron modelos:

| En la interfaz | Modelo / código | Notas |
|----------------|-----------------|-------|
| Departamento | `Area` | Sin cambio |
| Sector | `ZonaEdificio` | Sin cambio |
| Espacio físico | `Ubicacion` | Sin cambio |
| Check | `SeguimientoTicket` | Menú y UI usan **Checks**; el modelo conserva el nombre técnico |
| Cierre de mantenimiento | `AgendaMantenimiento` | UI: cierre; el modelo sigue llamándose Agenda |

---

## 9. Qué no se hizo a propósito

- No se cambiaron `url_name`, paths (`/Areas/`, etc.) ni `data-nav-id` salvo donde el texto visible lo requería.
- No hay migración de base de datos por estos renombres.
- No se unificaron Bitacora y Respuestas en un solo módulo.
- No se movió Proveedores a Compras.

---

## 10. Checklist de verificación manual

- [ ] Menú lateral muestra los rótulos de la sección 4
- [ ] Breadcrumb de una solicitud de equipo empieza en **General**
- [ ] Breadcrumb de cobertura empieza en **Soporte**
- [ ] Calendario: filtros Checks / Movimientos de equipo coherentes
- [ ] Matriz de permisos refleja Soporte / Admin según la sección 6
- [ ] Favoritos/recientes del sidebar (si usan `data-nav-label`) siguen encontrando los módulos

---

## 11. Resumen ejecutivo

Se aclararon **10 rótulos** del menú que eran ambiguos o chocaban entre sí, se alinearon breadcrumbs con el menú, y se extendió el mismo vocabulario a paneles, calendario, badges y matriz de permisos. El código interno y las URLs permanecen estables.
