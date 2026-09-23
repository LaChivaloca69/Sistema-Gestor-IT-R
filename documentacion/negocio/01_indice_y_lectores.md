# 1. Indice y lectores

**Sistema:** Sistema Web para la gestion de inventario y Mesa de ayuda TI  
**Tipo de documento:** Manual de negocio y uso  
**Ultima revision:** septiembre 2026

---

## 1.1 Proposito de este manual

Este manual describe **que hace el sistema**, **quien puede hacer cada cosa** y **como se realizan las tareas habituales** desde la interfaz web.

No explica el codigo fuente. Esa informacion se documentara en el manual tecnico.

---

## 1.2 A quien va dirigido

| Lector | Que debe leer |
|--------|----------------|
| Empleado final (rol Usuario) | Capítulos 2, 3, 4 y 5; procesos de tickets, solicitudes, ordenes propias y FAQ |
| Personal de TI (rol Tecnico IT) | Todo el manual de negocio, con enfasis en guias de tecnico y procesos operativos |
| Responsable de gobierno (rol Administrador) | Todo el manual, con enfasis en guia de administrador, gobierno y casos de uso |
| Direccion o jefatura | Capitulos 2, 3 y resumen de casos de uso |

---

## 1.3 Contenido del manual de negocio

| Archivo | Tema |
|---------|------|
| `01_indice_y_lectores.md` | Este indice |
| `02_que_es_el_sistema.md` | Vision, alcance y limites |
| `03_glosario.md` | Terminos usados en pantallas y procesos |
| `04_roles_y_permisos.md` | Roles y matriz de capacidades |
| `05_guia_usuario.md` | Tareas del empleado final |
| `06_guia_tecnico_it.md` | Operacion diaria de TI |
| `07_guia_administrador.md` | Gobierno del sistema |
| `08_procesos_soporte.md` | Tickets, checks, bitacora, comentarios |
| `09_procesos_inventario.md` | Equipos, perifericos, herramientas, asignaciones |
| `10_procesos_consumibles.md` | Stock por cantidad |
| `11_procesos_mantenimiento.md` | Ordenes y cierres de mantenimiento |
| `12_procesos_compras.md` | Ordenes de compra y plantillas |
| `13_procesos_organizacion_ubicaciones.md` | Personal, departamentos, mapa de sedes |
| `14_procesos_gobierno_auditoria.md` | Coberturas, matriz, historial |
| `15_casos_de_uso.md` | Catalogo formal CU-01 en adelante |
| `16_avisos_y_tableros.md` | Inicio, campana y paneles |
| `17_faq.md` | Preguntas frecuentes |

---

## 1.4 Como esta organizado el menu (referencia)

Las secciones del menu lateral dependen del rol. De forma general:

| Seccion del menu | Contenido tipico |
|------------------|------------------|
| General | Inicio, Calendario, Mis equipos, Solicitudes de equipo |
| Soporte | Tickets, Panel tickets, Checks, Bitacora, Respuestas, Cobertura |
| Compras | Ordenes, Plantillas (solo Administrador) |
| Inventario | Equipos, Perifericos, Herramientas, Consumibles, paneles y catalogos |
| Operaciones | Mantenimientos, Cierres, Asignaciones, Historial de actividad |
| Organizacion | Departamentos, Puestos, Personal |
| Ubicaciones | Mapa de sedes |
| Admin | Quitar roles, Archivar historial, Matriz de permisos, Guia SLA |

El Usuario ve un subconjunto (autoservicio). El Tecnico IT ve la operacion. El Administrador ve ademas gobierno.

---

## 1.5 Temas pendientes fuera de este manual

- Compartir la aplicacion en la red local desde una PC (se documentara mas adelante).

El manual tecnico vive en `documentacion/tecnico/`. Este manual de negocio en Word: `documentacion/Manual_negocio_GestorIT.docx`.
