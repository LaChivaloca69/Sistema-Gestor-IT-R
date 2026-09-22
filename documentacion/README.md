# Documentacion del sistema

**Nombre oficial:** Sistema Web para la gestion de inventario y Mesa de ayuda TI

Esta carpeta contiene la documentacion del proyecto en formato Markdown. Al final del trabajo se generara un documento Word a partir de estos archivos.

## Lectores

| Carpeta | Contenido | Publico |
|---------|-----------|---------|
| `negocio/` | Manual de negocio y uso | Usuarios, tecnicos de piso, administradores funcionales |
| `guia_usuario/` | Guia de uso de la pantalla (los tres roles) | Empleado, Tecnico IT y Administrador |
| `tecnico/` | Manual tecnico (nivel A: mapa, archivos clave y flujos) | Quien mantiene o modifica el sistema |

## Estado

| Parte | Estado |
|-------|--------|
| Manual de negocio (`negocio/`) | Disponible (17 capitulos) |
| Manual tecnico (`tecnico/`) | Disponible (indice + 16 capitulos) |
| Guia de usuario | Disponible: `guia_usuario/` (Markdown) y `Guia_de_usuario_GestorIT.docx` |
| Documento Word unificado | Pendiente (al cerrar revision de ambas partes) |
| Red local | Pendiente (no documentado aun) |

## Como leer

### Negocio

1. `negocio/01_indice_y_lectores.md`
2. Vision, glosario y roles
3. Guia del rol correspondiente
4. Procesos por dominio
5. `negocio/15_casos_de_uso.md`

### Guia de usuario

1. `guia_usuario/01_indice.md`
2. Capitulo del rol (tareas comunes, operacion de TI o gobierno)
3. El mismo texto en Word: `Guia_de_usuario_GestorIT.docx`

### Tecnico

1. `tecnico/00_indice.md`
2. Arquitectura, carpetas y roles en codigo
3. Capitulo del modulo a mantener
4. Jobs, forms/media y tests segun necesidad

## Convenciones

- Tono formal de manual.
- Solo texto y tablas (sin capturas de pantalla por ahora).
- Sin emojis ni flechas decorativas.
- La comparticion en red local queda pendiente.
