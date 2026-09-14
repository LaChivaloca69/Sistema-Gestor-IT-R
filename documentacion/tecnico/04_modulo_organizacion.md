# 4. Modulo organizacion

---

## 4.1 Proposito

Catalogos de estructura organizacional, personal con cuenta de acceso, y proveedores.

---

## 4.2 Conceptos

| Concepto | Modelo |
|----------|--------|
| Departamento | `Area` |
| Puesto | `Puesto` |
| Empleado / ficha | `Personal` (OneToOne opcional a `User`) |
| Proveedor | `Proveedor` (codigo interno automatico) |

Senal `post_delete` en Personal: desactiva el `User` vinculado (no lo borra).

---

## 4.3 Donde esta en el codigo

| Pieza | Ruta |
|-------|------|
| Modelos | `GestorApp/models.py` (`Area`, `Puesto`, `Personal`, `Proveedor`) |
| Vistas | `GestorApp/views/organizacion.py` |
| Forms | `GestorApp/forms/organizacion.py` |
| Templates | `GestorApp/Templates/area/`, `puesto/`, `personal/`, `proveedor/` |
| URLs | `area_*`, `puesto_*`, `personal_*`, `proveedor_*`, `personal_admin_remove` |
| Historial retencion UI | Misma vista module: `historial_retencion_admin` |

---

## 4.4 Flujo principal

1. Operativo mantiene areas y puestos.  
2. Administrador crea Personal, vincula User y asigna rol via `set_user_role`.  
3. Al eliminar Personal se liberan asignaciones activas de equipos y se desactiva el User.  
4. Proveedores se usan en inventario y compras; el codigo interno se genera con reintento ante colision.

---

## 4.5 Reglas

- Rol de negocio se guarda en Groups, no solo en un campo suelto.  
- Eliminar Personal no elimina fisicamente el User.  
- Quitar roles masivo no afecta superusuarios ni al ejecutor.

---

## 4.6 Permisos

| Accion | Quien |
|--------|-------|
| Listar areas/puestos/proveedores | Operativo |
| Eliminar catalogos | Admin |
| CRUD Personal y roles | Admin |
| Quitar roles | Admin |

---

## 4.7 Integraciones

- Tickets y solicitudes usan Personal / User.  
- Asignacion de equipos apunta a Personal.  
- Mis equipos resuelve `user.personal_profile`.

---

## 4.8 Puntos delicados

- Personal sin User no puede recibir rol de sistema.  
- Tests: `AltosMantenimientoPersonalComprasTests.test_personal_delete_libera_equipos_asignados`.

---

## 4.9 Como probar

Crear Personal con User, asignar Tecnico IT, asignar equipo, eliminar Personal y verificar User inactivo y equipo liberado.
