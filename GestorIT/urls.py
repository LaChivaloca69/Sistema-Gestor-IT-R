"""
URL configuration for GestorIT project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path

from GestorApp import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rutas para la aplicación GestorApp
    path('', login_required(views.home), name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),

    # -------- Area URLS-----------------
    path('Areas/', views.admin_required(views.area_list), name='area_list'),
    path('Areas/create/', views.admin_required(views.area_create), name='area_create'),
    path('Areas/update/<int:pk>/', views.admin_required(views.area_update), name='area_update'),
    path('Areas/delete/<int:pk>/', views.admin_required(views.area_delete), name='area_delete'),

    # --------- Puesto Urls -------------
    path('Puestos/', views.admin_required(views.puesto_list), name='puesto_list'),
    path('Puestos/create/', views.admin_required(views.puesto_create), name='puesto_create'),
    path('Puestos/update/<int:pk>/', views.admin_required(views.puesto_update), name='puesto_update'),
    path('Puestos/delete/<int:pk>/', views.admin_required(views.puesto_delete), name='puesto_delete'),

    # --------- Personal Urls -------------
    path('Personal/', views.admin_required(views.personal_list), name='personal_list'),
    path('Personal/solicitudes-admin/', views.admin_required(views.personal_admin_requests), name='personal_admin_requests'),
    path('Personal/quitar-admin/', views.admin_required(views.personal_admin_remove), name='personal_admin_remove'),
    path('Admin/historial-retencion/', views.admin_required(views.historial_retencion_admin), name='historial_retencion_admin'),
    path('Personal/create/', views.admin_required(views.personal_create), name='personal_create'),
    path('Personal/update/<int:pk>/', views.admin_required(views.personal_update), name='personal_update'),
    path('Personal/delete/<int:pk>/', views.admin_required(views.personal_delete), name='personal_delete'),


    # ----------- Proveedor Urls -------------
    path('Proveedores/', views.admin_required(views.proveedor_list), name='proveedor_list'),
    path('Proveedores/create/', views.admin_required(views.proveedor_create), name='proveedor_create'),
    path('Proveedores/update/<int:pk>/', views.admin_required(views.proveedor_update), name='proveedor_update'),
    path('Proveedores/delete/<int:pk>/', views.admin_required(views.proveedor_delete), name='proveedor_delete'),


    # ----------- Edificio Urls -------------
    path('Edificios/', views.admin_required(views.edificio_list), name='edificio_list'),
    path('Edificios/create/', views.admin_required(views.edificio_create), name='edificio_create'),
    path('Edificios/update/<int:pk>/', views.admin_required(views.edificio_update), name='edificio_update'),
    path('Edificios/delete/<int:pk>/', views.admin_required(views.edificio_delete), name='edificio_delete'),

    # ------------ Zona Edificios Urls -------------
    path('ZonaEdificios/', views.admin_required(views.zonaedificio_list), name='zonaedificio_list'),
    path('ZonaEdificios/create/', views.admin_required(views.zonaedificio_create), name='zonaedificio_create'), 
    path('ZonaEdificios/update/<int:pk>/', views.admin_required(views.zonaedificio_update), name='zonaedificio_update'),
    path('ZonaEdificios/delete/<int:pk>/', views.admin_required(views.zonaedificio_delete), name='zonaedificio_delete'),


    # ------------ Ubicacion Urls -------------
    path('Ubicacion/', views.admin_required(views.ubicacion_list), name='ubicacion_list'),
    path('Ubicacion/create/', views.admin_required(views.ubicacion_create), name='ubicacion_create'),
    path('Ubicacion/update/<int:pk>/', views.admin_required(views.ubicacion_update), name='ubicacion_update'),
    path('Ubicacion/delete/<int:pk>/', views.admin_required(views.ubicacion_delete), name='ubicacion_delete'),
    path(
        'Ubicacion/zonas/',
        views.admin_required(views.ubicacion_zona_choices),
        name='ubicacion_zona_choices',
    ),


    # ------------ Categoria Equipo Urls -------------
    path('CategoriaEquipo/', views.admin_required(views.categoriaequipo_list), name='categoriaequipo_list'),
    path('CategoriaEquipo/create/', views.admin_required(views.categoriaequipo_create), name='categoriaequipo_create'),
    path('CategoriaEquipo/update/<int:pk>/', views.admin_required(views.categoriaequipo_update), name='categoriaequipo_update'),
    path('CategoriaEquipo/delete/<int:pk>/', views.admin_required(views.categoriaequipo_delete), name='categoriaequipo_delete'),

    # ------------ Equipo views --------------
    path('Equipos/', views.admin_required(views.equipo_list), name='equipo_list'),
    path('Equipos/create/', views.admin_required(views.equipo_create), name='equipo_create'),
    path('Equipos/update/<int:pk>/', views.admin_required(views.equipo_update), name='equipo_update'),
    path('Equipos/delete/<int:pk>/', views.admin_required(views.equipo_delete), name='equipo_delete'),


    # ------------- Movimiento de equipos Urls -------------
    path('MovimientoEquipos/', views.admin_required(views.movimientoequipo_list), name='movimientoequipo_list'),
    path('MovimientoEquipos/registros/', views.admin_required(views.movimientoequipo_registros), name='movimientoequipo_registros'),
    path('MovimientoEquipos/create/', views.admin_required(views.movimientoequipo_create), name='movimientoequipo_create'),
    path('MovimientoEquipos/update/<int:pk>/', views.admin_required(views.movimientoequipo_update), name='movimientoequipo_update'),
    path('MovimientoEquipos/delete/<int:pk>/', views.admin_required(views.movimientoequipo_delete), name='movimientoequipo_delete'),
    path(
        'MovimientoEquipos/equipo-info/',
        views.admin_required(views.movimientoequipo_equipo_info),
        name='movimientoequipo_equipo_info',
    ),


    # ------------- Asignacion de equipos Urls -------------
    path('AsignacionEquipos/', views.admin_required(views.asignacionequipo_list), name='asignacionequipo_list'),
    path('AsignacionEquipos/create/', views.admin_required(views.asignacionequipo_create), name='asignacionequipo_create'),
    path('AsignacionEquipos/update/<int:pk>/', views.admin_required(views.asignacionequipo_update), name='asignacionequipo_update'),
    path('AsignacionEquipos/delete/<int:pk>/', views.admin_required(views.asignacionequipo_delete), name='asignacionequipo_delete'),


    # -------------- Mantenimiento de equipos Urls -------------
    path('MantenimientoEquipos/', views.admin_required(views.mantenimiento_list), name='mantenimiento_list'),
    path('MantenimientoEquipos/create/', views.admin_required(views.mantenimiento_create), name='mantenimiento_create'),
    path('MantenimientoEquipos/update/<int:pk>/', views.admin_required(views.mantenimiento_update), name='mantenimiento_update'),
    path('MantenimientoEquipos/delete/<int:pk>/', views.admin_required(views.mantenimiento_delete), name='mantenimiento_delete'),


    # -------------- Agenda de mantenimiento Urls -------------
    path('AgendaMantenimiento/', views.admin_required(views.agendamantenimiento_list), name='agendamantenimiento_list'),
    path('AgendaMantenimiento/create/', views.admin_required(views.agendamantenimiento_create), name='agendamantenimiento_create'),
    path('AgendaMantenimiento/update/<int:pk>/', views.admin_required(views.agendamantenimiento_update), name='agendamantenimiento_update'),
    path('AgendaMantenimiento/delete/<int:pk>/', views.admin_required(views.agendamantenimiento_delete), name='agendamantenimiento_delete'),


    # -------------- Ticket de soporte Urls -------------
    path('Ticketit/', login_required(views.ticketit_list), name='ticketit_list'),
    path('Ticketit/create/', login_required(views.ticketit_create), name='ticketit_create'),
    path('Ticketit/<int:pk>/', login_required(views.ticketit_detail), name='ticketit_detail'),
    path('Ticketit/update/<int:pk>/', login_required(views.ticketit_update), name='ticketit_update'),
    path('Ticketit/delete/<int:pk>/', login_required(views.ticketit_delete), name='ticketit_delete'),
    path(
        'Ticketit/<int:pk>/marcar-revision/',
        views.admin_required(views.ticketit_marcar_revision),
        name='ticketit_marcar_revision',
    ),
    path(
        'Ticketit/<int:pk>/reabrir/',
        views.admin_required(views.ticketit_reabrir),
        name='ticketit_reabrir',
    ),
    path(
        'Ticketit/subtipos/',
        login_required(views.ticketit_subtipo_choices),
        name='ticketit_subtipo_choices',
    ),


    # -------------- Seguimiento de tickets Urls -------------
    path('SeguimientoTickets/', views.admin_required(views.seguimientoticket_list), name='seguimientoticket_list'),
    path('SeguimientoTickets/create/', views.admin_required(views.seguimientoticket_create), name='seguimientoticket_create'),
    path('SeguimientoTickets/update/<int:pk>/', views.admin_required(views.seguimientoticket_update), name='seguimientoticket_update'),
    path('SeguimientoTickets/delete/<int:pk>/', views.admin_required(views.seguimientoticket_delete), name='seguimientoticket_delete'),


    # -------------- Bitacora de actividades Urls -------------
    path('Bitacora/', views.admin_required(views.bitacora_list), name='bitacora_list'),
    path('Bitacora/create/', views.admin_required(views.bitacora_create), name='bitacora_create'),
    path('Bitacora/update/<int:pk>/', views.admin_required(views.bitacora_update), name='bitacora_update'),
    path('Bitacora/delete/<int:pk>/', views.admin_required(views.bitacora_delete), name='bitacora_delete'),

    # -------------- Anwser de tickets Urls -------------
    path('Answer/', views.admin_required(views.answer_list), name='answer_list'),
    path('Answer/create/', views.admin_required(views.answer_create), name='answer_create'),
    path('Answer/update/<int:pk>/', views.admin_required(views.answer_update), name='answer_update'),
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
    path('OrdenesCompra/delete/<int:pk>/', login_required(views.ordencompra_delete), name='ordencompra_delete'),
    path('OrdenesCompra/preview/', login_required(views.ordencompra_preview), name='ordencompra_preview'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
