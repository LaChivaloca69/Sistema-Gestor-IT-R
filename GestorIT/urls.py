"""
URL configuration for GestorIT project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path

from GestorApp import views
from GestorApp import gobierno_views
from GestorApp.forms import LoginForm

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', login_required(views.home), name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='login.html',
            redirect_authenticated_user=True,
            authentication_form=LoginForm,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),

    # -------- Area URLS-----------------
    path('Areas/', views.operativo_required(views.area_list), name='area_list'),
    path('Areas/create/', views.operativo_required(views.area_create), name='area_create'),
    path('Areas/update/<int:pk>/', views.operativo_required(views.area_update), name='area_update'),
    path('Areas/delete/<int:pk>/', views.admin_required(views.area_delete), name='area_delete'),

    # --------- Puesto Urls -------------
    path('Puestos/', views.operativo_required(views.puesto_list), name='puesto_list'),
    path('Puestos/create/', views.operativo_required(views.puesto_create), name='puesto_create'),
    path('Puestos/update/<int:pk>/', views.operativo_required(views.puesto_update), name='puesto_update'),
    path('Puestos/delete/<int:pk>/', views.admin_required(views.puesto_delete), name='puesto_delete'),

    # --------- Personal Urls -------------
    path('Personal/', views.operativo_required(views.personal_list), name='personal_list'),
    path('Personal/<int:pk>/', views.operativo_required(views.personal_detail), name='personal_detail'),
    path('Personal/solicitudes-admin/', views.admin_required(views.personal_admin_requests), name='personal_admin_requests'),
    path('Personal/quitar-admin/', views.admin_required(views.personal_admin_remove), name='personal_admin_remove'),
    path('Admin/historial-retencion/', views.admin_required(views.historial_retencion_admin), name='historial_retencion_admin'),
    path('Personal/create/', views.admin_required(views.personal_create), name='personal_create'),
    path('Personal/update/<int:pk>/', views.admin_required(views.personal_update), name='personal_update'),
    path('Personal/delete/<int:pk>/', views.admin_required(views.personal_delete), name='personal_delete'),

    # ----------- Proveedor Urls -------------
    path('Proveedores/', views.operativo_required(views.proveedor_list), name='proveedor_list'),
    path('Proveedores/create/', views.operativo_required(views.proveedor_create), name='proveedor_create'),
    path('Proveedores/update/<int:pk>/', views.operativo_required(views.proveedor_update), name='proveedor_update'),
    path('Proveedores/delete/<int:pk>/', views.admin_required(views.proveedor_delete), name='proveedor_delete'),

    # ----------- Edificio Urls -------------
    path('Edificios/', views.operativo_required(views.edificio_list), name='edificio_list'),
    path('Edificios/create/', views.operativo_required(views.edificio_create), name='edificio_create'),
    path('Edificios/update/<int:pk>/', views.operativo_required(views.edificio_update), name='edificio_update'),
    path('Edificios/delete/<int:pk>/', views.admin_required(views.edificio_delete), name='edificio_delete'),

    # ------------ Zona Edificios Urls -------------
    path('ZonaEdificios/', views.operativo_required(views.zonaedificio_list), name='zonaedificio_list'),
    path('ZonaEdificios/create/', views.operativo_required(views.zonaedificio_create), name='zonaedificio_create'),
    path('ZonaEdificios/update/<int:pk>/', views.operativo_required(views.zonaedificio_update), name='zonaedificio_update'),
    path('ZonaEdificios/delete/<int:pk>/', views.admin_required(views.zonaedificio_delete), name='zonaedificio_delete'),

    # ------------ Ubicacion Urls -------------
    path('Ubicacion/', views.operativo_required(views.ubicacion_list), name='ubicacion_list'),
    path('Ubicacion/create/', views.operativo_required(views.ubicacion_create), name='ubicacion_create'),
    path('Ubicacion/update/<int:pk>/', views.operativo_required(views.ubicacion_update), name='ubicacion_update'),
    path('Ubicacion/delete/<int:pk>/', views.admin_required(views.ubicacion_delete), name='ubicacion_delete'),
    path(
        'Ubicacion/zonas/',
        views.operativo_required(views.ubicacion_zona_choices),
        name='ubicacion_zona_choices',
    ),

    # ------------ Categoria Equipo Urls -------------
    path('CategoriaEquipo/', views.operativo_required(views.categoriaequipo_list), name='categoriaequipo_list'),
    path('CategoriaEquipo/create/', views.operativo_required(views.categoriaequipo_create), name='categoriaequipo_create'),
    path('CategoriaEquipo/update/<int:pk>/', views.operativo_required(views.categoriaequipo_update), name='categoriaequipo_update'),
    path('CategoriaEquipo/delete/<int:pk>/', views.admin_required(views.categoriaequipo_delete), name='categoriaequipo_delete'),

    # ------------ Equipo views --------------
    path('Equipos/mis/', login_required(views.mis_equipos), name='mis_equipos'),
    path('Equipos/', views.operativo_required(views.equipo_list), name='equipo_list'),
    path('Equipos/dashboard/', views.operativo_required(views.equipo_dashboard), name='equipo_dashboard'),
    path('Equipos/create/', views.operativo_required(views.equipo_create), name='equipo_create'),
    path(
        'Equipos/detalle-orden-choices/',
        views.operativo_required(views.equipo_detalle_orden_choices),
        name='equipo_detalle_orden_choices',
    ),
    path('Equipos/<int:pk>/', views.operativo_required(views.equipo_detail), name='equipo_detail'),
    path('Equipos/update/<int:pk>/', views.operativo_required(views.equipo_update), name='equipo_update'),
    path('Equipos/delete/<int:pk>/', views.admin_required(views.equipo_delete), name='equipo_delete'),
    path('Equipos/<int:pk>/baja/', views.admin_required(views.equipo_dar_baja), name='equipo_dar_baja'),
    path('Equipos/<int:pk>/reactivar/', views.admin_required(views.equipo_reactivar), name='equipo_reactivar'),
    path('Equipos/<int:pk>/asignar/', views.operativo_required(views.equipo_asignar), name='equipo_asignar'),
    path('Equipos/<int:pk>/devolver/', views.operativo_required(views.equipo_devolver), name='equipo_devolver'),
    path(
        'Equipos/<int:pk>/ubicacion/',
        views.operativo_required(views.equipo_cambiar_ubicacion),
        name='equipo_cambiar_ubicacion',
    ),

    # ------------- Movimiento de equipos Urls -------------
    path('MovimientoEquipos/', views.operativo_required(views.movimientoequipo_list), name='movimientoequipo_list'),
    path(
        'Auditoria/<int:pk>/',
        views.operativo_required(views.historial_actividad_detail),
        name='historial_actividad_detail',
    ),
    path('MovimientoEquipos/registros/', views.operativo_required(views.movimientoequipo_registros), name='movimientoequipo_registros'),
    path('MovimientoEquipos/create/', views.operativo_required(views.movimientoequipo_create), name='movimientoequipo_create'),
    path(
        'MovimientoEquipos/equipo-info/',
        views.operativo_required(views.movimientoequipo_equipo_info),
        name='movimientoequipo_equipo_info',
    ),
    path('MovimientoEquipos/<int:pk>/', views.operativo_required(views.movimientoequipo_detail), name='movimientoequipo_detail'),
    path('MovimientoEquipos/update/<int:pk>/', views.operativo_required(views.movimientoequipo_update), name='movimientoequipo_update'),
    path('MovimientoEquipos/delete/<int:pk>/', views.admin_required(views.movimientoequipo_delete), name='movimientoequipo_delete'),

    # ------------- Asignacion de equipos Urls -------------
    path('AsignacionEquipos/', views.operativo_required(views.asignacionequipo_list), name='asignacionequipo_list'),
    path('AsignacionEquipos/create/', views.operativo_required(views.asignacionequipo_create), name='asignacionequipo_create'),
    path('AsignacionEquipos/update/<int:pk>/', views.operativo_required(views.asignacionequipo_update), name='asignacionequipo_update'),
    path('AsignacionEquipos/delete/<int:pk>/', views.admin_required(views.asignacionequipo_delete), name='asignacionequipo_delete'),

    # -------------- Mantenimiento de equipos Urls -------------
    path('MantenimientoEquipos/', views.operativo_required(views.mantenimiento_list), name='mantenimiento_list'),
    path('MantenimientoEquipos/dashboard/', views.operativo_required(views.mantenimiento_dashboard), name='mantenimiento_dashboard'),
    path('MantenimientoEquipos/create/', views.operativo_required(views.mantenimiento_create), name='mantenimiento_create'),
    path('MantenimientoEquipos/<int:pk>/', views.operativo_required(views.mantenimiento_detail), name='mantenimiento_detail'),
    path('MantenimientoEquipos/update/<int:pk>/', views.operativo_required(views.mantenimiento_update), name='mantenimiento_update'),
    path('MantenimientoEquipos/delete/<int:pk>/', views.admin_required(views.mantenimiento_delete), name='mantenimiento_delete'),
    path(
        'MantenimientoEquipos/<int:pk>/iniciar/',
        views.operativo_required(views.mantenimiento_iniciar),
        name='mantenimiento_iniciar',
    ),
    path(
        'MantenimientoEquipos/<int:pk>/cancelar/',
        views.operativo_required(views.mantenimiento_cancelar),
        name='mantenimiento_cancelar',
    ),
    path(
        'MantenimientoEquipos/<int:pk>/reabrir/',
        views.operativo_required(views.mantenimiento_reabrir),
        name='mantenimiento_reabrir',
    ),

    # -------------- Agenda de mantenimiento Urls -------------
    path('AgendaMantenimiento/', views.operativo_required(views.agendamantenimiento_list), name='agendamantenimiento_list'),
    path('AgendaMantenimiento/create/', views.operativo_required(views.agendamantenimiento_create), name='agendamantenimiento_create'),
    path('AgendaMantenimiento/update/<int:pk>/', views.operativo_required(views.agendamantenimiento_update), name='agendamantenimiento_update'),
    path('AgendaMantenimiento/delete/<int:pk>/', views.admin_required(views.agendamantenimiento_delete), name='agendamantenimiento_delete'),

    # -------------- Ticket de soporte Urls -------------
    path('Ticketit/', login_required(views.ticketit_list), name='ticketit_list'),
    path('Ticketit/dashboard/', login_required(views.ticketit_dashboard), name='ticketit_dashboard'),
    path('Ticketit/create/', login_required(views.ticketit_create), name='ticketit_create'),
    path('Ticketit/<int:pk>/', login_required(views.ticketit_detail), name='ticketit_detail'),
    path('Ticketit/update/<int:pk>/', login_required(views.ticketit_update), name='ticketit_update'),
    path('Ticketit/delete/<int:pk>/', login_required(views.ticketit_delete), name='ticketit_delete'),
    path(
        'Ticketit/<int:pk>/marcar-revision/',
        views.operativo_required(views.ticketit_marcar_revision),
        name='ticketit_marcar_revision',
    ),
    path(
        'Ticketit/<int:pk>/reabrir/',
        views.operativo_required(views.ticketit_reabrir),
        name='ticketit_reabrir',
    ),
    path(
        'Ticketit/<int:pk>/comentarios/',
        login_required(views.ticketit_comentario_create),
        name='ticketit_comentario_create',
    ),
    path(
        'Ticketit/<int:pk>/comentarios/<int:comentario_id>/delete/',
        login_required(views.ticketit_comentario_delete),
        name='ticketit_comentario_delete',
    ),
    path(
        'Ticketit/subtipos/',
        login_required(views.ticketit_subtipo_choices),
        name='ticketit_subtipo_choices',
    ),

    # -------------- Seguimiento de tickets Urls -------------
    path('SeguimientoTickets/', views.operativo_required(views.seguimientoticket_list), name='seguimientoticket_list'),
    path('SeguimientoTickets/create/', views.operativo_required(views.seguimientoticket_create), name='seguimientoticket_create'),
    path('SeguimientoTickets/update/<int:pk>/', views.operativo_required(views.seguimientoticket_update), name='seguimientoticket_update'),
    path('SeguimientoTickets/delete/<int:pk>/', views.admin_required(views.seguimientoticket_delete), name='seguimientoticket_delete'),

    # -------------- Bitacora de actividades Urls -------------
    path('Bitacora/', views.operativo_required(views.bitacora_list), name='bitacora_list'),
    path('Bitacora/create/', views.operativo_required(views.bitacora_create), name='bitacora_create'),
    path('Bitacora/<int:pk>/', views.operativo_required(views.bitacora_detail), name='bitacora_detail'),
    path('Bitacora/update/<int:pk>/', views.operativo_required(views.bitacora_update), name='bitacora_update'),
    path('Bitacora/delete/<int:pk>/', views.admin_required(views.bitacora_delete), name='bitacora_delete'),

    # -------------- Anwser de tickets Urls -------------
    path('Answer/', views.operativo_required(views.answer_list), name='answer_list'),
    path('Answer/create/', views.operativo_required(views.answer_create), name='answer_create'),
    path('Answer/update/<int:pk>/', views.operativo_required(views.answer_update), name='answer_update'),
    path('Answer/delete/<int:pk>/', views.admin_required(views.answer_delete), name='answer_delete'),

    # -------------- Plantillas de documentos urls -------------
    path('Plantillas/', views.admin_required(views.plantilla_list), name='plantilla_list'),
    path('Plantillas/create/', views.admin_required(views.plantilla_create), name='plantilla_create'),
    path('Plantillas/update/<int:pk>/', views.admin_required(views.plantilla_update), name='plantilla_update'),
    path('Plantillas/delete/<int:pk>/', views.admin_required(views.plantilla_delete), name='plantilla_delete'),

    # -------------- Ordenes de compra urls -------------
    path('OrdenesCompra/', login_required(views.ordencompra_list), name='ordencompra_list'),
    path('OrdenesCompra/nueva/', login_required(views.ordencompra_choose), name='ordencompra_choose'),
    path('OrdenesCompra/crear/', login_required(views.ordencompra_create), name='ordencompra_create'),
    path('OrdenesCompra/subir/', login_required(views.ordencompra_upload), name='ordencompra_upload'),
    path('OrdenesCompra/update/<int:pk>/', login_required(views.ordencompra_update), name='ordencompra_update'),
    path('OrdenesCompra/<int:pk>/terminar/', login_required(views.ordencompra_terminar), name='ordencompra_terminar'),
    path('OrdenesCompra/delete/<int:pk>/', login_required(views.ordencompra_delete), name='ordencompra_delete'),
    path('OrdenesCompra/preview/', login_required(views.ordencompra_preview), name='ordencompra_preview'),

    # -------------- Gobierno / roles --------------
    path('Gobierno/permisos/', views.admin_required(gobierno_views.permisos_matriz), name='permisos_matriz'),
    path('Gobierno/coberturas/', views.operativo_required(gobierno_views.cobertura_list), name='cobertura_list'),
    path('Gobierno/coberturas/create/', views.operativo_required(gobierno_views.cobertura_create), name='cobertura_create'),
    path('Gobierno/coberturas/update/<int:pk>/', views.operativo_required(gobierno_views.cobertura_update), name='cobertura_update'),
    path('Gobierno/coberturas/delete/<int:pk>/', views.operativo_required(gobierno_views.cobertura_delete), name='cobertura_delete'),
    path('SolicitudesEquipo/', login_required(gobierno_views.solicitud_equipo_list), name='solicitud_equipo_list'),
    path('SolicitudesEquipo/create/', login_required(gobierno_views.solicitud_equipo_create), name='solicitud_equipo_create'),
    path('SolicitudesEquipo/<int:pk>/', login_required(gobierno_views.solicitud_equipo_detail), name='solicitud_equipo_detail'),
    path(
        'SolicitudesEquipo/<int:pk>/revisar/',
        views.operativo_required(gobierno_views.solicitud_equipo_revisar),
        name='solicitud_equipo_revisar',
    ),
    path(
        'SolicitudesEquipo/<int:pk>/cancelar/',
        login_required(gobierno_views.solicitud_equipo_cancelar),
        name='solicitud_equipo_cancelar',
    ),
    path(
        'SolicitudesEquipo/seguimiento/update/<int:pk>/',
        views.operativo_required(gobierno_views.seguimiento_solicitud_update),
        name='seguimiento_solicitud_update',
    ),
    path(
        'SolicitudesEquipo/seguimiento/delete/<int:pk>/',
        views.admin_required(gobierno_views.seguimiento_solicitud_delete),
        name='seguimiento_solicitud_delete',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
