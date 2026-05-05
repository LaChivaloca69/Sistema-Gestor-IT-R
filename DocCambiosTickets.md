# Documentacion de cambios: Support, Check, Bitacora y Answer

## Resumen

Se realizo una reorganizacion del modulo de tickets para pasar de un esquema general de TicketIT/SeguimientoTicket a una estructura operativa con 4 bloques:

- Support
- Check
- Bitacora
- Answer

La implementacion ya incluye cambios en modelos, vistas, templates, navegacion y migraciones.

## 1) Cambios de modelo de datos

Archivo principal modificado:

- GestorIT/GestorITapps/models.py

### TicketIT ahora representa Support

Se redefinio TicketIT para funcionar como Support con estos campos principales:

- folio_ticket (debe iniciar con SPRT-)
- fecha_support
- requerimiento
- departamento
- tipo_ticket
- sub_tipo_ticket
- equipo
- tipo_equipo
- otro_tipo_equipo
- identificador_reporte (ID)
- detalle
- descripcion
- imagen_url
- status

Reglas importantes:

- Validacion de prefijo SPRT- en folio_ticket.
- Si tipo_equipo es Otro, se exige otro_tipo_equipo.
- Se normaliza folio_ticket a mayusculas en save.

### SeguimientoTicket ahora representa Check

Se redefinio SeguimientoTicket para funcionar como Check con estos campos:

- ticket (relacion con Support)
- folio_check (acepta SPRT-)
- fecha_check
- usuario
- solucion
- observacion
- ya_terminado

Reglas importantes:

- Validacion de prefijo SPRT- en folio_check cuando se captura.
- Meta en singular/plural como Check.

### Nuevo modelo Bitacora

Se agrego un nuevo modelo para registrar situaciones:

- folio_bitacora (debe iniciar con BIT-)
- fecha_bitacora
- situacion
- descripcion_situacion

Reglas importantes:

- Validacion de prefijo BIT-.
- Folio normalizado a mayusculas.

### Nuevo modelo Answer

Se agrego un nuevo modelo para registrar soluciones de Bitacora:

- bitacora (FK)
- folio_answer (debe iniciar con BIT-)
- fecha_answer
- solucion
- descripcion_solucion

Reglas importantes:

- Validacion de prefijo BIT-.
- Validacion de consistencia entre folio_answer y folio_bitacora seleccionada.

## 2) Cambios en vistas y navegacion

Archivo principal modificado:

- GestorIT/GestorITapps/views.py

Cambios aplicados:

- Se agregaron Bitacora y Answer al MODEL_REGISTRY.
- Se actualizo la seccion de Soporte en HOME_MODEL_SECTIONS para incluir:
  - ticketit (Support)
  - seguimientoticket (Check)
  - bitacora
  - answer

## 3) Cambios en interfaz (templates)

### Sidebar global

Archivo modificado:

- GestorIT/Templates/base.html

Cambios:

- Sidebar lateral con accesos rapidos.
- Seccion Soporte actualizada con enlaces a Support, Check, Bitacora y Answer.

### Templates de Support (ticketit)

Archivos modificados:

- GestorIT/Templates/crud/ticketit/list.html
- GestorIT/Templates/crud/ticketit/form.html
- GestorIT/Templates/crud/ticketit/confirm_delete.html

Cambios:

- Etiquetas y textos de Tickets IT a Support.
- Campos de tabla y formulario alineados al nuevo modelo.
- Vista de eliminacion adaptada a nuevos campos.

### Templates de Check (seguimientoticket)

Archivos modificados:

- GestorIT/Templates/crud/seguimientoticket/list.html
- GestorIT/Templates/crud/seguimientoticket/form.html
- GestorIT/Templates/crud/seguimientoticket/confirm_delete.html

Cambios:

- Etiquetas y textos a Check.
- Tabla y formulario alineados a nuevo esquema.
- Confirmacion de eliminacion personalizada.

### Templates nuevos para Bitacora y Answer

Archivos creados:

- GestorIT/Templates/crud/bitacora/list.html
- GestorIT/Templates/crud/bitacora/form.html
- GestorIT/Templates/crud/bitacora/confirm_delete.html
- GestorIT/Templates/crud/answer/list.html
- GestorIT/Templates/crud/answer/form.html
- GestorIT/Templates/crud/answer/confirm_delete.html

## 4) Migraciones

Archivo de migracion generado:

- GestorIT/GestorITapps/migrations/0003_bitacora_alter_seguimientoticket_options_and_more.py

Acciones principales de la migracion:

- Crea modelo Bitacora.
- Crea modelo Answer.
- Reestructura TicketIT con nuevos campos Support.
- Reestructura SeguimientoTicket con nuevos campos Check.
- Ajusta metadatos verbose_name y verbose_name_plural.

Estado de aplicacion:

- Migracion aplicada correctamente en entorno SQLite de prueba.

## 5) Nota sobre datos de prueba

Para destrabar el flujo de migraciones se ejecuto la estrategia sin conservar datos anteriores de prueba.

Esto implica que:

- El objetivo fue dejar claro el nuevo esquema funcional.
- Se priorizo consistencia estructural sobre mapeo historico de campos antiguos.

## 6) Pendiente opcional recomendado

Actualmente sub_tipo_ticket esta como texto libre.

Siguiente mejora sugerida:

- Crear catalogo controlado Tipo/Subtipo para que el formulario de Support filtre subtipos por tipo y evite capturas inconsistentes.

## 7) Comando de referencia para migrar

Desde la carpeta GestorIT:

- python manage.py makemigrations GestorITapps --settings=GestorIT.settings_sqlite --noinput
- python manage.py migrate --settings=GestorIT.settings_sqlite
