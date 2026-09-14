# 3. Roles en codigo

---

## 3.1 Proposito

Centralizar la identidad de negocio (Usuario, Tecnico IT, Administrador) sin depender de `is_staff` como unico criterio de la aplicacion web.

Archivo principal: `GestorApp/roles.py`.

---

## 3.2 Representacion

| Concepto | Implementacion |
|----------|----------------|
| Rol | Group de Django con nombre exacto |
| Constantes | `ROLE_USUARIO`, `ROLE_TECNICO`, `ROLE_ADMIN` |
| Precedencia | Admin > Tecnico IT > Usuario |
| Superusuario | Siempre se trata como Administrador |

---

## 3.3 Resolucion del rol (`get_user_role`)

1. Sin autenticacion: sin rol.  
2. `is_superuser`: Administrador.  
3. Primer grupo de negocio segun precedencia.  
4. Sin grupo: se asume **Usuario**.

**Regla critica:** `user.is_staff=True` **sin** grupo Administrador **no** convierte al usuario en Administrador de la app.

---

## 3.4 Asignacion (`set_user_role`)

1. Asegura que existan los tres groups.  
2. Quita los tres groups de rol y agrega exactamente uno.  
3. Sincroniza `is_staff`:
   - `True` si Administrador o superusuario (acceso potencial a `/admin/`).
   - `False` para Tecnico IT y Usuario.  
4. Invalida cache interna de nombres de grupo en el objeto user.

---

## 3.5 Helpers

| Funcion | Significado |
|---------|-------------|
| `is_administrador` | Solo Admin (o superuser) |
| `is_tecnico` | Solo Tecnico IT |
| `is_operativo` | Tecnico IT o Administrador |
| `is_admin_user` | Alias de `is_administrador` |
| `operativo_users_queryset` | Usuarios elegibles como tecnicos (tickets, coberturas, etc.) |

---

## 3.6 Decoradores

| Decorador | Efecto si falla |
|-----------|-----------------|
| `admin_required` | Mensaje y redirect a `home` |
| `operativo_required` | Mensaje y redirect a `home` |

Se reexportan desde `GestorApp.views` para usarlos en `GestorIT/urls.py`.

---

## 3.7 Templates

`GestorApp/context_processors.py` expone:

| Variable | Uso |
|----------|-----|
| `user_role` | Texto del rol |
| `is_admin_role` | Flags de menu Admin |
| `is_tecnico_role` | Flags de tecnico |
| `is_operativo_role` | Menu operativo |
| `signup_enabled` | Mostrar enlaces de registro |

---

## 3.8 Donde se asigna el rol en la UI

- Formulario / vista de **Personal** (Administrador).  
- Alta publica (`signup`) solo si `SIGNUP_ENABLED=True`; crea rol Usuario.  
- Pantalla **Quitar roles** baja tecnicos/admins a Usuario.

---

## 3.9 Permisos finos (mas alla del decorador)

Muchas vistas usan helpers en `views/helpers.py`, por ejemplo:

- `user_can_view_ticket` / `user_can_edit_ticket` / `user_can_delete_ticket`
- `user_can_view_equipo`
- `user_can_manage_orden` / `user_can_terminar_orden` / `user_can_delete_orden`
- `user_can_manage_cobertura`
- `user_can_comment_ticket` / `user_can_delete_comentario`

El decorador abre la puerta del modulo; el helper decide el objeto concreto.

---

## 3.10 Como probar

- `GestorApp.tests.UserFailureHardeningTests.test_is_staff_sin_grupo_no_es_administrador`
- Flujos de seguridad en `SecurityAndUIFixesTests`
- Asignacion de roles en pruebas que usan `set_user_role`
