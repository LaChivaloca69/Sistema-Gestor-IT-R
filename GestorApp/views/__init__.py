"""
Vistas de GestorApp (paquete).

Compatibilidad: `from GestorApp import views` y `views.area_list` siguen igual.
Los decoradores de rol se reexportan porque urls.py usa `views.admin_required`.

Nota: `import *` no reexporta nombres con `_`; esos helpers se listan abajo
porque nav_badges, tasks y gobierno_views los importan desde `.views`.
"""

from ..roles import admin_required, operativo_required

from .helpers import (  # noqa: F401
    _apply_date_filters,
    _cerrar_asignaciones_activas,
    _crear_movimiento,
    _deny_ticket_access,
    _end_of_month,
    _get_equipo_asignacion_activa,
    _get_equipo_responsable,
    _month_bounds,
    _ordenes_for_user,
    _parse_date,
    _quick_range_bounds,
    _reconciliar_estado_equipo,
    _ticket_dashboard_context,
    _ticket_has_seguimientos,
    _tickets_abiertos_qs,
    _tickets_for_user,
    _tickets_sla_por_vencer_q,
    _tickets_sla_vencidos_q,
    user_can_comment_ticket,
    user_can_delete_comentario,
    user_can_delete_ticket,
    user_can_edit_ticket,
    user_can_manage_orden,
    user_can_manage_ticket_flow,
    user_can_view_ticket,
)
from .organizacion import *  # noqa: F401,F403
from .ubicaciones import *  # noqa: F401,F403
from .equipo import *  # noqa: F401,F403
from .equipo import (  # noqa: F401
    _asignaciones_antiguas_qs,
    _equipo_dashboard_context,
    _equipo_queryset,
    _equipos_alerta_context,
    _equipos_mantenimiento_largo_qs,
    _equipos_sin_ubicacion_qs,
    _export_equipos_csv,
    _filtrar_equipos,
)
from .movimiento import *  # noqa: F401,F403
from .movimiento import (  # noqa: F401
    _export_movimientos_csv,
    _filtrar_movimientos,
    _movimiento_queryset,
)
from .asignacion import *  # noqa: F401,F403
from .mantenimiento import *  # noqa: F401,F403
from .mantenimiento import (  # noqa: F401
    _crear_proximo_mantenimiento_desde_cierre,
    _equipos_con_mantenimiento_activo_ids,
    _estado_equipo_tras_mantenimiento,
    _mantenimiento_dashboard_context,
    _mantenimiento_queryset,
    _mantenimientos_activos_qs,
    _mantenimientos_alerta_context,
    _mensaje_proximo_ciclo,
    _parse_date_param,
    _proximos_ciclos_mantenimiento_qs,
    _sync_equipo_fin_mantenimiento,
    _sync_equipo_inicio_mantenimiento,
)
from .tickets import *  # noqa: F401,F403
from .tickets import (  # noqa: F401
    _seguimientos_alerta_context,
    _seguimientos_base_qs,
    _seguimientos_pendientes_qs,
    _ticketit_queryset,
)
from .compras import *  # noqa: F401,F403
from .compras import (  # noqa: F401
    _intentar_generar_pdf,
    _proveedores_payload,
)
from .home import *  # noqa: F401,F403
from .home import (  # noqa: F401
    _build_home_calendar_events,
    _calendar_apply_urgency_color,
    _calendar_day,
    _calendar_event,
    _calendar_label,
    _calendar_urgency_from_date,
    _calendar_window,
    _ticket_calendar_urgency,
)
