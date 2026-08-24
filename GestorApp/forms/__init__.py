"""
Formularios de GestorApp (paquete).

Compatibilidad: `from GestorApp.forms import TicketITForm` sigue funcionando.
"""

from .auth import LoginForm, UserRegisterForm
from .common import (
    get_subtipo_ticket_choices,
    get_tipo_equipo_queryset,
)
from .organizacion import AreaForm, PersonalForm, ProveedorForm, PuestoForm
from .ubicaciones import (
    CategoriaEquipoForm,
    EdificioForm,
    UbicacionForm,
    ZonaEdificioForm,
)
from .equipo import EquipoAsignarForm, EquipoBajaForm, EquipoForm, EquipoUbicacionForm
from .movimiento import MovimientoEquipoForm
from .asignacion import AsignacionEquipoForm
from .mantenimiento import AgendaMantenimientoForm, MantenimientoForm
from .tickets import AnswerForm, BitacoraForm, SeguimientoTicketForm, TicketITForm
from .compras import (
    DetalleOrdenCompraCapturaForm,
    DetalleOrdenCompraCapturaFormSet,
    DetalleOrdenCompraForm,
    DetalleOrdenCompraFormSet,
    OrdenCompraCrearForm,
    OrdenCompraSubirForm,
    PlantillaDocumentoForm,
)
from .gobierno import (
    CoberturaTicketsForm,
    SeguimientoSolicitudEquipoForm,
    SolicitudEquipoForm,
    SolicitudEquipoRevisionForm,
)

__all__ = [
    "AgendaMantenimientoForm",
    "AnswerForm",
    "AreaForm",
    "AsignacionEquipoForm",
    "BitacoraForm",
    "CategoriaEquipoForm",
    "CoberturaTicketsForm",
    "DetalleOrdenCompraCapturaForm",
    "DetalleOrdenCompraCapturaFormSet",
    "DetalleOrdenCompraForm",
    "DetalleOrdenCompraFormSet",
    "EdificioForm",
    "EquipoAsignarForm",
    "EquipoBajaForm",
    "EquipoForm",
    "EquipoUbicacionForm",
    "MantenimientoForm",
    "MovimientoEquipoForm",
    "OrdenCompraCrearForm",
    "OrdenCompraSubirForm",
    "PersonalForm",
    "PlantillaDocumentoForm",
    "ProveedorForm",
    "PuestoForm",
    "SeguimientoSolicitudEquipoForm",
    "SeguimientoTicketForm",
    "SolicitudEquipoForm",
    "SolicitudEquipoRevisionForm",
    "TicketITForm",
    "UbicacionForm",
    "LoginForm",
    "UserRegisterForm",
    "ZonaEdificioForm",
    "get_subtipo_ticket_choices",
    "get_tipo_equipo_queryset",
]
