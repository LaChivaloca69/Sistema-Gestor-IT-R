# Documentacion de Templates - Sistema Gestor IT

## Descripcion general

Este documento explica como funciona el sistema de templates en el proyecto Gestor IT.

La implementacion usa templates de Django con herencia (base + hijos) y vistas genericas para construir un CRUD dinamico por modelo.

## Ubicacion de templates

La carpeta principal de templates esta en:

- GestorIT/Templates/

Configuracion en Django (settings):

- Archivo: GestorIT/GestorIT/settings.py
- Seccion: TEMPLATES
- Clave DIRS: BASE_DIR / 'Templates'

Esto permite que Django encuentre templates globales del proyecto en esa ruta.

## Estructura actual

Templates principales:

- GestorIT/Templates/base.html
- GestorIT/Templates/home.html
- GestorIT/Templates/Index.html

Templates de CRUD:

- GestorIT/Templates/crud/list.html
- GestorIT/Templates/crud/form.html
- GestorIT/Templates/crud/confirm_delete.html

Nota:

- Index.html existe, pero en el flujo actual de vistas no se esta utilizando.

## Patron de herencia de templates

El proyecto usa herencia de templates de Django para evitar duplicar estructura visual.

### Template base

- base.html define el esqueleto comun:
  - estructura HTML (head, body)
  - estilos CSS globales
  - header comun
  - contenedor principal

Tambien define bloques reutilizables:

- block title
- block content

### Templates hijos

Los templates de paginas especificas extienden base.html:

- home.html
- crud/list.html
- crud/form.html
- crud/confirm_delete.html

Cada uno sobreescribe los bloques title y content para su caso.

## Como se conectan con las vistas

Las vistas estan en:

- GestorIT/GestorITapps/views.py

Cada vista define el template_name que debe renderizar Django:

- HomeView -> home.html
- ModelListView -> crud/list.html
- ModelCreateView -> crud/form.html
- ModelUpdateView -> crud/form.html
- ModelDeleteView -> crud/confirm_delete.html

## Rutas que activan cada template

Rutas de app en:

- GestorIT/GestorITapps/urls.py

Mapeo actual:

- / -> HomeView -> home.html
- /<model_slug>/ -> ModelListView -> crud/list.html
- /<model_slug>/nuevo/ -> ModelCreateView -> crud/form.html
- /<model_slug>/<pk>/editar/ -> ModelUpdateView -> crud/form.html
- /<model_slug>/<pk>/eliminar/ -> ModelDeleteView -> crud/confirm_delete.html

Y estas rutas se incluyen desde el proyecto principal en:

- GestorIT/GestorIT/urls.py

## Contexto que recibe cada template

### 1) home.html

Lo renderiza HomeView.

Contexto principal:

- modelos: lista de modelos registrados con:
  - slug
  - nombre

Uso en template:

- genera una cuadricula de enlaces para entrar al CRUD de cada modelo.

### 2) crud/list.html

Lo renderiza ModelListView.

Contexto principal:

- modelo_nombre: nombre del modelo en formato legible
- model_slug: slug tecnico del modelo
- objetos: queryset paginado del modelo
- fields: campos del modelo para cabecera de tabla
- rows: filas preprocesadas con valores por objeto

Uso en template:

- construye una tabla dinamica con todos los campos del modelo
- agrega acciones por fila (Editar, Eliminar)
- muestra boton para crear nuevo registro

### 3) crud/form.html

Lo usan ModelCreateView y ModelUpdateView.

Contexto principal:

- form: formulario generado dinamicamente
- modelo_nombre
- model_slug

Uso en template:

- renderiza formulario con form.as_p
- incluye proteccion CSRF
- boton Guardar y enlace Cancelar

### 4) crud/confirm_delete.html

Lo usa ModelDeleteView.

Contexto principal:

- object: registro a eliminar
- modelo_nombre
- model_slug

Uso en template:

- muestra confirmacion
- envia POST para eliminar
- ofrece boton de cancelar

## Flujo completo de renderizado

1. El usuario entra a la URL.
2. Django resuelve la ruta en urls.py.
3. La vista correspondiente prepara datos de contexto.
4. La vista renderiza el template indicado por template_name.
5. El template hijo extiende base.html y llena bloques title/content.
6. El navegador recibe HTML final.

## Reutilizacion del CRUD por modelo

El sistema evita crear un template distinto por cada tabla gracias a:

- MODEL_REGISTRY en views.py
- URL dinamica con model_slug
- vistas genericas (ListView, CreateView, UpdateView, DeleteView)
- templates CRUD comunes en carpeta crud/

Resultado:

- un solo conjunto de templates para multiples modelos
- menos codigo duplicado
- mantenimiento mas simple

## Buenas practicas aplicadas

- Herencia de templates (base + hijos)
- URL nombradas con {% url %}
- Proteccion CSRF en formularios POST
- Plantillas reutilizables para CRUD
- Separacion clara entre:
  - vistas (logica)
  - templates (presentacion)

## Mejoras recomendadas

- Agregar mensajes de exito/error con framework de messages en base.html.
- Incluir paginacion visible en crud/list.html (actualmente paginate_by=25 en vista).
- Crear un template de errores (404/500) personalizado.
- Definir un bloque extra para scripts por pagina si se requiere JS futuro.

## Resumen

El sistema de templates esta implementado de forma modular y escalable:

- base.html centraliza estructura y estilos
- templates hijos definen contenido de cada pagina
- CRUD dinamico reutiliza vistas y templates para todos los modelos registrados

Esto facilita crecer el sistema sin duplicar codigo de interfaz.
