"""Matriz documentada de permisos por rol (solo lectura / documentacion)."""

from .roles import ROLE_ADMIN, ROLE_TECNICO, ROLE_USUARIO

# Cada fila: (modulo, accion, usuario, tecnico, admin, notas)
# Valores: True / False / "parcial"
PERMISSION_MATRIX = [
    (
        "Soporte",
        "Ver y crear tickets propios",
        True,
        True,
        True,
        "Usuario solo ve los que solicito.",
    ),
    (
        "Soporte",
        "Ver todos los tickets / dashboard SLA",
        False,
        True,
        True,
        "Tecnico y Admin operan el backlog completo.",
    ),
    (
        "Soporte",
        "Comentar y adjuntar en tickets",
        True,
        True,
        True,
        "Solicitante y IT en tickets abiertos. En cerrado, solo IT. Adjuntos: imagen o PDF.",
    ),
    (
        "Soporte",
        "Checks, bitacora y respuestas",
        False,
        True,
        True,
        "Bitacora con detalle y respuestas como checks. Solo IT.",
    ),
    (
        "Soporte",
        "Eliminar tickets",
        False,
        False,
        True,
        "Solo Admin y sin seguimientos asociados.",
    ),
    (
        "Inventario",
        "Mis equipos asignados",
        True,
        True,
        True,
        "Consulta de asignaciones propias.",
    ),
    (
        "Inventario",
        "Gestionar equipos, movimientos, proveedores",
        False,
        True,
        True,
        "Alta, edicion, ubicacion y movimientos de equipo.",
    ),
    (
        "Inventario",
        "Dar de baja / eliminar equipo",
        False,
        False,
        True,
        "Baja logica o borrado fisico con restricciones.",
    ),
    (
        "Inventario",
        "Solicitar equipo",
        True,
        True,
        True,
        "Flujo solicitud → decision IT. El solicitante solo consulta.",
    ),
    (
        "Inventario",
        "Aprobar / completar solicitudes de equipo",
        False,
        True,
        True,
        "IT decide: en revision, aprobar, rechazar o cerrar. Puede asignar equipo al aprobar/cerrar.",
    ),
    (
        "Operaciones",
        "Mantenimientos, cierres y asignaciones",
        False,
        True,
        True,
        "Programacion y ejecucion.",
    ),
    (
        "Operaciones",
        "Eliminar mantenimientos / cierres",
        False,
        False,
        True,
        "Borrado permanente.",
    ),
    (
        "Compras",
        "Ver y gestionar ordenes propias",
        True,
        True,
        True,
        "Usuario no operativo solo las elaboradas por el.",
    ),
    (
        "Compras",
        "Plantillas de documentos",
        False,
        False,
        True,
        "Solo Administrador.",
    ),
    (
        "Organizacion",
        "Departamentos, puestos, personal, espacios",
        False,
        True,
        True,
        "Catalogos operativos.",
    ),
    (
        "Organizacion",
        "Crear / editar / eliminar personal",
        False,
        False,
        True,
        "Admin gestiona cuentas y roles de negocio.",
    ),
    (
        "Soporte",
        "Cobertura de tickets (delegacion)",
        False,
        True,
        True,
        "Suplente atiende tickets del ausente en el periodo.",
    ),
    (
        "Admin",
        "Matriz de permisos",
        False,
        False,
        True,
        "Documentacion de quien puede que.",
    ),
    (
        "Admin",
        "Quitar roles / archivar historial",
        False,
        False,
        True,
        "Herramientas de administracion.",
    ),
    (
        "Django Admin",
        "Acceso a /admin/",
        False,
        False,
        True,
        "is_staff solo para Administrador y superuser.",
    ),
]


def matrix_for_template():
    """Agrupa filas por modulo para la plantilla."""
    groups = []
    current = None
    for modulo, accion, usuario, tecnico, admin, notas in PERMISSION_MATRIX:
        if current is None or current["modulo"] != modulo:
            current = {"modulo": modulo, "rows": []}
            groups.append(current)
        current["rows"].append(
            {
                "accion": accion,
                "usuario": usuario,
                "tecnico": tecnico,
                "admin": admin,
                "notas": notas,
            }
        )
    return {
        "groups": groups,
        "roles": [ROLE_USUARIO, ROLE_TECNICO, ROLE_ADMIN],
    }
