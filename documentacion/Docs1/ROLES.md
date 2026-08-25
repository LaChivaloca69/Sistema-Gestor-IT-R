# Roles — Guía de funcionamiento

Sistema de roles del **Gestor IT**: Usuario, Técnico IT y Administrador.

**Última revisión:** agosto 2026.

---

## 1. Resumen

Antes el sistema era binario (`is_staff` = admin / resto = usuario). Ahora hay **tres roles de negocio** basados en **Groups de Django**.

| Rol | Propósito |
|-----|-----------|
| **Usuario** | Autoservicio: tickets propios, sus equipos, sus órdenes de compra |
| **Tecnico IT** | Operación diaria del área IT (casi todo, sin gobierno del sistema) |
| **Administrador** | Gobierno: roles, personal, borrados críticos, plantillas, retención |

Archivos clave:

| Archivo | Uso |
|---------|-----|
| `GestorApp/roles.py` | Constantes, helpers, decoradores |
| `GestorApp/context_processors.py` | Flags en templates (`is_admin_role`, etc.) |
| `GestorApp/views/helpers.py` | Permisos de tickets y órdenes |
| `GestorApp/permissions_matrix.py` | Matriz documentada (`/Gobierno/permisos/`) |
| `GestorApp/migrations/0032_roles_groups_y_tipo_mantenimiento.py` | Grupos + migración de usuarios + tipo ticket MANTENIMIENTO |
| `GestorIT/urls.py` | Rutas con `operativo_required` / `admin_required` |

---

## 2. Cómo se representan los roles

### Groups de Django

| Nombre del grupo | Rol |
|------------------|-----|
| `Usuario` | Usuario |
| `Tecnico IT` | Técnico IT |
| `Administrador` | Administrador |

Un usuario debe pertenecer a **un solo** grupo de rol de negocio. Al asignar un rol se quitan los otros dos.

### Precedencia

Al resolver el rol efectivo (`get_user_role`):

1. `is_superuser` → **Administrador**
2. Grupo `Administrador`
3. Grupo `Tecnico IT`
4. Grupo `Usuario`
5. Compatibilidad: si aún tiene `is_staff` sin grupo → se trata como Administrador

### Sincronización con `is_staff`

| Rol | `is_staff` |
|-----|------------|
| Administrador | `True` (acceso potencial a `/admin/` de Django) |
| Tecnico IT | `False` |
| Usuario | `False` |
| Superusuario | siempre `True` |

**Importante:** en la app web ya no se usa `is_staff` como único criterio. Se usan los helpers de `roles.py`.

---

## 3. Cómo se asigna un rol

### Registro (signup)

1. Cualquiera puede crear cuenta en `/signup/`.
2. Se crea el `User` + perfil `Personal`.
3. Se asigna automáticamente el rol **Usuario**.
4. Ya no existe el checkbox “Solicitar admin”.

### Elevación / cambio (solo Administrador)

1. Ir a **Personal** → editar el registro.
2. Campo **Rol del sistema**: Usuario / Tecnico IT / Administrador.
3. Requiere que el personal tenga **usuario vinculado**.

Atajo Admin: menú **Admin → Bajar roles** baja Técnicos/Admins a Usuario (no aplica a superusuarios ni a uno mismo).

### Migración inicial

La migración `0032` creó los grupos y:

- Usuarios con `is_staff` o `is_superuser` → grupo **Administrador**
- Resto → grupo **Usuario**

Quien deba ser Técnico IT hay que asignarlo manualmente desde Personal.

---

## 4. Helpers y decoradores

```python
from GestorApp.roles import (
    is_administrador,   # solo Admin (o superuser)
    is_tecnico,         # solo Tecnico IT
    is_operativo,       # Tecnico IT o Administrador
    is_admin_user,      # alias de is_administrador
    admin_required,     # solo Admin
    operativo_required, # Tecnico + Admin
    set_user_role,      # asigna grupo + sincroniza is_staff
    get_user_role,      # etiqueta del rol efectivo
)
```

En templates (context processor):

| Variable | Significado |
|----------|-------------|
| `user_role` | Texto del rol (`Usuario`, `Tecnico IT`, `Administrador`) |
| `is_admin_role` | Es Administrador |
| `is_tecnico_role` | Es Tecnico IT |
| `is_operativo_role` | Es Tecnico IT o Administrador |

El chip del topbar muestra `usuario · Rol`.

---

## 5. Matriz de permisos por módulo

Leyenda: **Sí** · **No** · **Propias** (solo lo del usuario)

### Tickets

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| Crear / ver / editar tickets propios | Sí | Sí | Sí |
| Ver todos / asignar / revisión / reabrir | No | Sí | Sí |
| Seguimientos (crear / editar) | No | Sí | Sí |
| Borrar seguimientos | No | No | Sí |
| Borrar ticket (sin checks) | No | No | Sí |
| Tipo **MANTENIMIENTO** (solicitar mant.) | Sí | Sí | Sí |

### Equipos / inventario

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| Ver **Mis equipos** (asignados a él) | Sí | Sí | Sí |
| Inventario completo, movimientos, asignar | No | Sí | Sí |
| Dar de baja / reactivar / borrar equipo | No | No | Sí |

### Mantenimiento operativo

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| Solicitar vía ticket tipo Mantenimiento | Sí | Sí | Sí |
| CRUD operativo / agenda / iniciar-cerrar | No | Sí | Sí |
| Borrar mantenimiento / cierre | No | No | Sí |

### Catálogos (Áreas, Puestos, Edificios, Zonas, Ubicaciones, Categorías, Proveedores)

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| Ver / crear / editar | No | Sí | Sí |
| Borrar | No | No | Sí |

### Personal y roles

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| Ver lista / detalle (lectura) | No | Sí | Sí |
| Crear / editar / borrar personal | No | No | Sí |
| Cambiar roles | No | No | Sí |

### Compras (órdenes)

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| Crear / ver / editar / borrar | **Propias** | Todas | Todas |
| Plantillas PDF | No | No | Sí |

Al borrar una orden, se registra en **Historial** (módulo órdenes de compra) con usuario, rol y folio. Si borra un no-admin, el nivel es **crítico** para que el Admin lo note.

### Sistema

| Acción | Usuario | Tecnico IT | Admin |
|--------|---------|------------|-------|
| Retención / archivar historial | No | No | Sí |
| Django `/admin/` | No | No | Si tiene `is_staff` / superuser |

---

## 6. Rutas: `operativo_required` vs `admin_required`

Patrón general en `GestorIT/urls.py`:

- **Listar / crear / editar** operación → `operativo_required`
- **Borrar**, bajas, personal escritura, plantillas, retención, roles → `admin_required`
- **Tickets y compras** (con reglas de ownership) → `login_required` + lógica en la vista
- **Mis equipos** → `login_required` en `/Equipos/mis/`

Si un Técnico intenta una URL de Admin, recibe mensaje de error y redirect a **home**.

---

## 7. Menú lateral

| Sección | Quién la ve |
|---------|-------------|
| General (Inicio, Calendario, Mis equipos, Solicitudes) | Todos |
| Soporte → Tickets / Dashboard | Todos |
| Soporte → Seguimiento / Bitácora / Respuestas / Coberturas | Operativo |
| Compras → Órdenes | Todos |
| Compras → Plantillas | Solo Admin |
| Organización, Ubicaciones, Inventario, Operaciones | Operativo |
| Admin (Bajar roles, Archivar, Matriz permisos) | Solo Admin |

---

## 8. Flujos típicos

### Nuevo empleado

1. Se registra en signup → rol **Usuario**.
2. Puede crear tickets (incl. Mantenimiento), ver Mis equipos y sus órdenes.
3. Un Admin lo eleva a **Tecnico IT** si entra al área IT.

### Técnico atiende ticket

1. Ve todos los tickets y el dashboard operativo.
2. Marca En Revisión, asigna, agrega seguimientos.
3. No puede borrar checks ni tickets con historial; eso es Admin.

### Usuario pide mantenimiento

1. **Tickets → Nuevo**.
2. Tipo de ticket: **MANTENIMIENTO** (+ subtipo).
3. El Técnico/Admin lo atiende como cualquier ticket.
4. El módulo formal de Mantenimientos (agenda, iniciar, cerrar) lo opera solo el personal operativo.

### Usuario borra su orden de compra

1. Solo puede borrar órdenes donde `elaborado_por` es él.
2. Queda registro en Historial para auditoría del Admin.

---

## 9. Checklist de prueba rápida

- [ ] Signup crea usuario con rol **Usuario** visible en el chip del topbar.
- [ ] Usuario no ve menús de inventario / personal / seguimientos.
- [ ] Usuario ve solo sus órdenes; no ve las ajenas.
- [ ] Admin edita Personal y asigna **Tecnico IT**.
- [ ] Técnico entra a equipos/mantenimiento/tickets globales.
- [ ] Técnico no puede borrar catálogo / baja de equipo / seguimientos.
- [ ] Técnico ve Personal en solo lectura (botón Ver, sin Editar/Eliminar).
- [ ] Ticket tipo **MANTENIMIENTO** aparece en el formulario.
- [ ] Borrar orden de un Usuario aparece en Historial.

---

## 10. Notas técnicas

- No se usa un campo `rol` en el modelo `Personal`; el rol vive en **Groups** del `User`.
- El campo legacy `Personal.admin_requested` ya no se usa en el registro (queda en BD por compatibilidad).
- `operativo_users_queryset()` alimenta combos de “asignado a” / técnico en tickets y seguimientos (Técnicos + Admins + superusers).
- Para crear un Técnico IT de prueba: Admin → Personal → editar → Rol = Tecnico IT → guardar.
