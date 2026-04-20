# Documentacion de Views - Sistema Gestor IT

## Descripcion general

Este documento describe las vistas implementadas en la app GestorITapps para manejar CRUD generico de los modelos del sistema.

Las vistas estan construidas con class-based views de Django y funcionan de forma dinamica segun el modelo recibido en la URL.

## Archivo principal

- Vistas: GestorIT/GestorITapps/views.py
- Rutas de app: GestorIT/GestorITapps/urls.py
- Templates usados: GestorIT/Templates/home.html, GestorIT/Templates/crud/list.html, GestorIT/Templates/crud/form.html, GestorIT/Templates/crud/confirm_delete.html

## Arquitectura de vistas

### 1) Registro central de modelos

Se usa MODEL_REGISTRY para mapear un slug (nombre tecnico del modelo) hacia la clase del modelo en Django.

Esto permite reutilizar las mismas vistas para todos los modelos registrados, sin duplicar codigo.

Modelos incluidos:
- area
- puesto
- personal
- proveedor
- edificio
- zonaedificio
- ubicacion
- categoriaequipo
- equipo
- movimientoequipo
- asignacionequipo
- mantenimiento
- agendamantenimiento
- ticketit
- seguimientoticket
- presupuesto
- detallepresupuesto
- compramaterial
- detallecompramaterial

### 2) Resolucion de modelo por URL

La funcion get_model_by_slug(model_slug) obtiene la clase del modelo desde MODEL_REGISTRY.

Si el slug no existe, lanza Http404 con el mensaje Modelo no encontrado.

### 3) Mixin compartido para CRUD

ModelContextMixin concentra la logica comun para Create, Update, Delete y List:

- dispatch:
  - Lee model_slug desde la URL.
  - Resuelve y guarda el modelo actual en self.model.

- get_form_class:
  - Construye un ModelForm dinamico con todos los campos del modelo (fields = __all__).

- get_success_url:
  - Redirige al listado del mismo modelo despues de crear/editar/eliminar.

- get_context_data:
  - Inyecta model_slug y modelo_nombre para los templates.

### 4) HomeView

Tipo: TemplateView
Template: home.html

Responsabilidad:
- Mostrar el panel principal con los modelos disponibles.
- Envia un arreglo llamado modelos con:
  - slug
  - nombre (verbose_name_plural en formato titulo)

### 5) ModelListView

Tipo: ListView + ModelContextMixin
Template: crud/list.html
Contexto:
- objetos: queryset de registros del modelo (ordenado por pk)
- fields: lista de campos del modelo
- rows: lista de filas preprocesadas para renderizar tabla

Responsabilidad:
- Mostrar tabla con todos los registros del modelo.
- Mostrar acciones Editar y Eliminar por fila.
- Mostrar boton Nuevo registro.

Notas:
- paginate_by esta configurado en 25.

### 6) ModelCreateView

Tipo: CreateView + ModelContextMixin
Template: crud/form.html

Responsabilidad:
- Crear registros nuevos para el modelo seleccionado.
- Usa formulario dinamico con todos los campos.

### 7) ModelUpdateView

Tipo: UpdateView + ModelContextMixin
Template: crud/form.html

Responsabilidad:
- Editar un registro existente por pk.

### 8) ModelDeleteView

Tipo: DeleteView + ModelContextMixin
Template: crud/confirm_delete.html

Responsabilidad:
- Confirmar y eliminar un registro por pk.

## Rutas disponibles

Definidas en GestorIT/GestorITapps/urls.py:

- /
  - Nombre: home
  - Vista: HomeView

- /<model_slug>/
  - Nombre: modelo-list
  - Vista: ModelListView

- /<model_slug>/nuevo/
  - Nombre: modelo-create
  - Vista: ModelCreateView

- /<model_slug>/<pk>/editar/
  - Nombre: modelo-update
  - Vista: ModelUpdateView

- /<model_slug>/<pk>/eliminar/
  - Nombre: modelo-delete
  - Vista: ModelDeleteView

## Flujo CRUD esperado

1. El usuario entra a la pagina principal (/).
2. Selecciona el modelo desde el panel.
3. Ve el listado de registros del modelo.
4. Puede crear, editar o eliminar registros.
5. Al completar una accion, vuelve al listado del mismo modelo.

## Templates y datos de contexto

### home.html
Recibe:
- modelos

Renderiza:
- Lista de tarjetas/enlaces por modelo.

### crud/list.html
Recibe:
- modelo_nombre
- model_slug
- objetos
- fields
- rows

Renderiza:
- Tabla dinamica con todos los campos.
- Botones de CRUD por registro.

### crud/form.html
Recibe:
- form
- modelo_nombre
- model_slug

Renderiza:
- Formulario de alta/edicion.

### crud/confirm_delete.html
Recibe:
- object
- modelo_nombre
- model_slug

Renderiza:
- Confirmacion de borrado.

## Cambios faltantes

- Limitar campos expuestos por modelo (en lugar de __all__).
- Agregar filtros de busqueda en listados.
- Agregar permisos por rol para crear/editar/eliminar.
- Agregar validaciones personalizadas en formularios.
- Agregar pruebas unitarias para cada vista.
