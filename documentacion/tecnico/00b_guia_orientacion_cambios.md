# Guia de orientacion: como cambiar algo en el codigo

Cuando ya sepas que archivo mirar, usa el [manual tecnico](00_indice.md) del modulo correspondiente.

---

## 1. Idea general (breve)

El sistema es una aplicacion web Django. Cada pantalla suele seguir este camino:

```text
URL  -->  Vista  -->  Formulario (si hay datos)  -->  Modelo (base de datos)  -->  Template (HTML)
```

| Pieza | Que es en palabras simples | Donde suele estar |
|-------|----------------------------|-------------------|
| URL | La direccion del navegador | `GestorIT/urls.py` |
| Vista | La funcion que decide que mostrar o guardar | `GestorApp/views/` |
| Formulario | Valida lo que el usuario escribe | `GestorApp/forms/` |
| Modelo | Tablas y reglas de datos | `GestorApp/models.py` |
| Template | El HTML de la pantalla | `GestorApp/Templates/` |
| Estilos / JS | Apariencia y comportamientos en el navegador | `static/GestorApp/` |
| Roles | Quien puede entrar (Usuario, Tecnico IT, Administrador) | `GestorApp/roles.py` |

Mapa mas detallado: [`02_mapa_carpetas.md`](02_mapa_carpetas.md).

---

## 2. Checklist antes de editar

Haz esto **antes** de cambiar codigo:

1. **Describe el cambio en una frase**  
   Ejemplo: “Quiero que el mensaje de error de contraseña diga otra cosa.”
2. **Abre la pantalla en el navegador** y anota la URL (barra de direcciones).
3. **Busca esa ruta** en `GestorIT/urls.py` (el `path(...)` y el `name=`).
4. **Abre la vista** que indica esa ruta (archivo en `GestorApp/views/` o `gobierno_views.py`).
5. **Preguntate:**  
   - Solo cambia texto o estilo? → template / CSS  
   - Valida o guarda datos? → formulario y/o modelo  
   - Quien puede usarlo? → decorador en la URL + `roles.py`
6. **Prueba con los tres roles** si el cambio afecta permisos o menus (Usuario, Tecnico IT, Administrador).
7. **Si dudas, mira el capitulo del modulo** en el indice tecnico antes de inventar una solucion.

---

## 3. Tabla “Quiero cambiar…”

| Quiero… | Empieza aqui | Luego mira | Cuidado con |
|---------|--------------|------------|------------|
| Un texto, titulo o boton en pantalla | Template en `GestorApp/Templates/` | Vista solo si el texto viene de una variable | No meter reglas de negocio en el HTML |
| Colores, tamaños, layout | `static/GestorApp/css/` | Template si falta una clase | No romper vistas movil/desktop |
| Un mensaje de error o etiqueta de campo | Form en `GestorApp/forms/` | Template que muestra `{{ form }}` | Validaciones en `clean()` / `clean_campo()` |
| Que un campo sea obligatorio u opcional | Form (`required=`) y a veces modelo | Migracion si cambias el modelo | Datos viejos en la base |
| Quien puede abrir una pantalla | Decorador en `GestorIT/urls.py` (`login_required`, `operativo_required`, `admin_required`) | `roles.py`, helpers en `views/helpers.py` | Probar con los 3 roles |
| Un filtro o listado | Vista del listado | Form de busqueda si existe | No filtrar de mas y ocultar datos validos |
| Una regla al guardar (estados, folios, stock) | `models.py` y/o form | Vista que llama `save()` | Efectos en otras pantallas |
| Agregar un campo nuevo a la base | Modelo → migracion → form → template | Admin si se usa | Crear migracion; no editar migraciones viejas a mano |
| Un aviso del menu o campana | `nav_badges.py` | Vista/home si el KPI sale de ahi | Cache de metricas (~45 s) |
| Una pantalla nueva (alta) | URL → vista → form → template → (modelo) | Permisos y breadcrumbs | Seguir el patron de un modulo parecido |
| Un PDF / plantilla de compra | `document_engine.py` + plantillas en media | Forms/vistas de compras | Probar con archivo real |
| Un job automatico (recordatorios, retencion) | `tasks.py`, `schedules.py`, `job_queue.py` | Que `qcluster` este corriendo | No romper la cola en produccion |

Si el cambio es de un dominio concreto (tickets, inventario, etc.), abre el capitulo de ese modulo en [`00_indice.md`](00_indice.md).

---

## 4. Ejemplo real: pantalla de Personal

Caso: quieres entender **Crear / editar personal** (incluye “Crear usuario nuevo” y validacion de contraseña).

### 4.1 Camino de archivos

```text
Navegador: /Personal/create/  o  /Personal/update/<id>/
        |
        v
GestorIT/urls.py
  name='personal_create' / 'personal_update'
  decorador: admin_required
        |
        v
GestorApp/views/organizacion.py
  personal_create / personal_update
        |
        v
GestorApp/forms/organizacion.py
  PersonalForm  (clean valida usuario y password)
        |
        v
GestorApp/models.py
  Personal  (+ User de Django si se crea cuenta)
        |
        v
GestorApp/Templates/personal/form.html  (o similar)
```

### 4.2 Que tocar segun el cambio

| Cambio tipico | Archivo |
|---------------|---------|
| Texto de la opcion “Crear usuario nuevo” | `PersonalForm` en `forms/organizacion.py` (choices de `account_action`) |
| Reglas de contraseña | Llamada a `validate_password` en `PersonalForm.clean()` + validadores en `GestorIT/settings.py` (`AUTH_PASSWORD_VALIDATORS`) |
| Quien puede crear personal | Decorador en `urls.py` (`admin_required`) |
| Campos del empleado (nombre, area…) | Modelo `Personal` + form + template |

Detalle del modulo: [`04_modulo_organizacion.md`](04_modulo_organizacion.md).

---

## 5. Zonas seguras vs delicadas

Usa esto como termometro de riesgo. No sustituye revisar el cambio con alguien mas experimentado cuando el riesgo sea alto.

### Mas seguro (buen lugar para practicar)

- Textos fijos en templates  
- Labels / help_texts / mensajes claros en forms  
- CSS y ajustes visuales menores  
- Comentarios en codigo (sin cambiar logica)

### Riesgo medio (haz el checklist y prueba bien)

- Vistas: filtros, mensajes `messages.*`, redirects  
- Formularios: `clean`, campos nuevos en el form (sin tocar el modelo)  
- Templates con variables y condiciones simples (`{% if %}`)

### Delicado (pide ayuda o lee el capitulo tecnico completo antes)

| Zona | Por que |
|------|---------|
| `GestorApp/models.py` | Afecta datos, estados y otras pantallas |
| `GestorApp/migrations/` | Cambia la base de datos; no reescribir migraciones ya aplicadas |
| `GestorApp/roles.py` y decoradores de URL | Puedes abrir o cerrar acceso sin darte cuenta |
| `GestorIT/settings.py` | Seguridad, BD, media, jobs |
| `document_engine.py`, compras / PDF | Archivos y plantillas sensibles |
| `media_security.py` | Subida de archivos |
| `tasks.py` / `schedules.py` / `job_queue.py` | Procesos en segundo plano |
| Borrar o renombrar `name=` de URLs | Rompe enlaces, historial y breadcrumbs |

---

## 6. Habitos utiles

1. **Cambia una sola cosa a la vez** y prueba esa pantalla.  
2. **Copia el patron** de un modulo parecido (list / create / update / delete) en vez de inventar estructura nueva.  
3. **Busca en el codigo** el nombre de la URL (`name='...'`) o el texto que ves en pantalla.  
4. **No subas secretos** (contraseñas, `.env`, claves) al repositorio.  
5. Si el proyecto tiene tests, despues de un cambio de logica mira [`16_tests_y_calidad.md`](16_tests_y_calidad.md).

---

## 7. Donde seguir leyendo

| Si necesitas… | Abre |
|---------------|------|
| Indice del manual tecnico | [`00_indice.md`](00_indice.md) |
| Capas y flujo de una peticion | [`01_arquitectura.md`](01_arquitectura.md) |
| Carpetas del repo | [`02_mapa_carpetas.md`](02_mapa_carpetas.md) |
| Roles y permisos en codigo | [`03_roles_en_codigo.md`](03_roles_en_codigo.md) |
| Forms y helpers de permiso | [`14_formularios_y_permisos.md`](14_formularios_y_permisos.md) |
| Templates y estaticos | [`15_plantillas_y_estaticos.md`](15_plantillas_y_estaticos.md) |
| Que hace el usuario en pantalla (negocio) | `documentacion/negocio/` o `documentacion/guia_usuario/` |

---

## 8. Resumen en una frase

**Primero ubica la URL, luego la vista, luego decide si el cambio es de pantalla (template), de validacion (form) o de datos/reglas (modelo); si toca permisos, base de datos o jobs, detente y pide ayuda.**
