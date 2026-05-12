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
    path('Areas/', login_required(views.area_list), name='area_list'),
    path('Areas/create/', login_required(views.area_create), name='area_create'),
    path('Areas/update/<int:pk>/', login_required(views.area_update), name='area_update'),
    path('Areas/delete/<int:pk>/', login_required(views.area_delete), name='area_delete'),

    # --------- Puesto Urls -------------
    path('Puestos/', login_required(views.puesto_list), name='puesto_list'),
    path('Puestos/create/', login_required(views.puesto_create), name='puesto_create'),
    path('Puestos/update/<int:pk>/', login_required(views.puesto_update), name='puesto_update'),
    path('Puestos/delete/<int:pk>/', login_required(views.puesto_delete), name='puesto_delete'),

    # --------- Personal Urls -------------
    path('Personal/', login_required(views.personal_list), name='personal_list'),
    path('Personal/create/', login_required(views.personal_create), name='personal_create'),
    path('Personal/update/<int:pk>/', login_required(views.personal_update), name='personal_update'),
    path('Personal/delete/<int:pk>/', login_required(views.personal_delete), name='personal_delete'),


    # ----------- Proveedor Urls -------------
    path('Proveedores/', login_required(views.proveedor_list), name='proveedor_list'),
    path('Proveedores/create/', login_required(views.proveedor_create), name='proveedor_create'),
    path('Proveedores/update/<int:pk>/', login_required(views.proveedor_update), name='proveedor_update'),
    path('Proveedores/delete/<int:pk>/', login_required(views.proveedor_delete), name='proveedor_delete'),


    # ----------- Edificio Urls -------------
    path('Edificios/', login_required(views.edificio_list), name='edificio_list'),
    path('Edificios/create/', login_required(views.edificio_create), name='edificio_create'),
    path('Edificios/update/<int:pk>/', login_required(views.edificio_update), name='edificio_update'),
    path('Edificios/delete/<int:pk>/', login_required(views.edificio_delete), name='edificio_delete'),

    # ------------ Zona Edificios Urls -------------
    path('ZonaEdificios/', login_required(views.zonaedificio_list), name='zonaedificio_list'),
    path('ZonaEdificios/create/', login_required(views.zonaedificio_create), name='zonaedificio_create'), 
    path('ZonaEdificios/update/<int:pk>/', login_required(views.zonaedificio_update), name='zonaedificio_update'),
    path('ZonaEdificios/delete/<int:pk>/', login_required(views.zonaedificio_delete), name='zonaedificio_delete'),


    # ------------ Ubicacion Urls -------------
    path('Ubicacion/', login_required(views.ubicacion_list), name='ubicacion_list'),
    path('Ubicacion/create/', login_required(views.ubicacion_create), name='ubicacion_create'),
    path('Ubicacion/update/<int:pk>/', login_required(views.ubicacion_update), name='ubicacion_update'),
    path('Ubicacion/delete/<int:pk>/', login_required(views.ubicacion_delete), name='ubicacion_delete'),


    # ------------ Categoria Equipo Urls -------------
    path('CategoriaEquipo/', login_required(views.categoriaequipo_list), name='categoriaequipo_list'),
    path('CategoriaEquipo/create/', login_required(views.categoriaequipo_create), name='categoriaequipo_create'),
    path('CategoriaEquipo/update/<int:pk>/', login_required(views.categoriaequipo_update), name='categoriaequipo_update'),
    path('CategoriaEquipo/delete/<int:pk>/', login_required(views.categoriaequipo_delete), name='categoriaequipo_delete'),

    # ------------ Equipo views --------------
    path('Equipos/', login_required(views.equipo_list), name='equipo_list'),
    path('Equipos/create/', login_required(views.equipo_create), name='equipo_create'),
    path('Equipos/update/<int:pk>/', login_required(views.equipo_update), name='equipo_update'),
    path('Equipos/delete/<int:pk>/', login_required(views.equipo_delete), name='equipo_delete'),


    # ------------- Movimiento de equipos Urls -------------
    path('MovimientoEquipos/', login_required(views.movimientoequipo_list), name='movimientoequipo_list'),
    path('MovimientoEquipos/create/', login_required(views.movimientoequipo_create), name='movimientoequipo_create'),
    path('MovimientoEquipos/update/<int:pk>/', login_required(views.movimientoequipo_update), name='movimientoequipo_update'),
    path('MovimientoEquipos/delete/<int:pk>/', login_required(views.movimientoequipo_delete), name='movimientoequipo_delete'),


    # ------------- Asignacion de equipos Urls -------------
    path('AsignacionEquipos/', login_required(views.asignacionequipo_list), name='asignacionequipo_list'),
    path('AsignacionEquipos/create/', login_required(views.asignacionequipo_create), name='asignacionequipo_create'),
    path('AsignacionEquipos/update/<int:pk>/', login_required(views.asignacionequipo_update), name='asignacionequipo_update'),
    path('AsignacionEquipos/delete/<int:pk>/', login_required(views.asignacionequipo_delete), name='asignacionequipo_delete'),


    # -------------- Mantenimiento de equipos Urls -------------
    path('MantenimientoEquipos/', login_required(views.mantenimiento_list), name='mantenimiento_list'),
    path('MantenimientoEquipos/create/', login_required(views.mantenimiento_create), name='mantenimiento_create'),
    path('MantenimientoEquipos/update/<int:pk>/', login_required(views.mantenimiento_update), name='mantenimiento_update'),
    path('MantenimientoEquipos/delete/<int:pk>/', login_required(views.mantenimiento_delete), name='mantenimiento_delete'),


    # -------------- Agenda de mantenimiento Urls -------------
    path('AgendaMantenimiento/', login_required(views.agendamantenimiento_list), name='agendamantenimiento_list'),
    path('AgendaMantenimiento/create/', login_required(views.agendamantenimiento_create), name='agendamantenimiento_create'),
    path('AgendaMantenimiento/update/<int:pk>/', login_required(views.agendamantenimiento_update), name='agendamantenimiento_update'),
    path('AgendaMantenimiento/delete/<int:pk>/', login_required(views.agendamantenimiento_delete), name='agendamantenimiento_delete'),


    # -------------- Ticket de soporte Urls -------------
    path('Ticketit/', login_required(views.ticketit_list), name='ticketit_list'),
    path('Ticketit/create/', login_required(views.ticketit_create), name='ticketit_create'),
    path('Ticketit/update/<int:pk>/', login_required(views.ticketit_update), name='ticketit_update'),
    path('Ticketit/delete/<int:pk>/', login_required(views.ticketit_delete), name='ticketit_delete'),
    path(
        'Ticketit/subtipos/',
        login_required(views.ticketit_subtipo_choices),
        name='ticketit_subtipo_choices',
    ),


    # -------------- Seguimiento de tickets Urls -------------
    path('SeguimientoTickets/', login_required(views.seguimientoticket_list), name='seguimientoticket_list'),
    path('SeguimientoTickets/create/', login_required(views.seguimientoticket_create), name='seguimientoticket_create'),
    path('SeguimientoTickets/update/<int:pk>/', login_required(views.seguimientoticket_update), name='seguimientoticket_update'),
    path('SeguimientoTickets/delete/<int:pk>/', login_required(views.seguimientoticket_delete), name='seguimientoticket_delete'),


    # -------------- Bitacora de actividades Urls -------------
    path('Bitacora/', login_required(views.bitacora_list), name='bitacora_list'),
    path('Bitacora/create/', login_required(views.bitacora_create), name='bitacora_create'),
    path('Bitacora/update/<int:pk>/', login_required(views.bitacora_update), name='bitacora_update'),
    path('Bitacora/delete/<int:pk>/', login_required(views.bitacora_delete), name='bitacora_delete'),

    # -------------- Anwser de tickets Urls -------------
    path('Answer/', login_required(views.answer_list), name='answer_list'),
    path('Answer/create/', login_required(views.answer_create), name='answer_create'),
    path('Answer/update/<int:pk>/', login_required(views.answer_update), name='answer_update'),
    path('Answer/delete/<int:pk>/', login_required(views.answer_delete), name='answer_delete'),

    # -------------- Presupuesto urls -------------
    path('Presupuestos/', login_required(views.presupuesto_list), name='presupuesto_list'),
    path('Presupuestos/create/', login_required(views.presupuesto_create), name='presupuesto_create'),
    path('Presupuestos/update/<int:pk>/', login_required(views.presupuesto_update), name='presupuesto_update'),
    path('Presupuestos/delete/<int:pk>/', login_required(views.presupuesto_delete), name='presupuesto_delete'),


    # -------------- DetallePresupuesto urls -------------
    path('DetallePresupuestos/', login_required(views.Detallepresupuesto_list), name='detallepresupuesto_list'),
    path('DetallePresupuestos/create/', login_required(views.Detallepresupuesto_create), name='detallepresupuesto_create'),
    path('DetallePresupuestos/update/<int:pk>/', login_required(views.Detallepresupuesto_update), name='detallepresupuesto_update'),
    path('DetallePresupuestos/delete/<int:pk>/', login_required(views.Detallepresupuesto_delete), name='detallepresupuesto_delete'),


    # -------------- CompraMaterial urls -------------
    path('CompraMaterial/', login_required(views.compramaterial_list), name='compramaterial_list'),
    path('CompraMaterial/create/', login_required(views.compramaterial_create), name='compramaterial_create'),
    path('CompraMaterial/update/<int:pk>/', login_required(views.compramaterial_update), name='compramaterial_update'),
    path('CompraMaterial/delete/<int:pk>/', login_required(views.compramaterial_delete), name='compramaterial_delete'),


    # -------------- Detalle Compra Material urls -------------
    path('DetalleCompraMaterial/', login_required(views.detallecompramaterial_list), name='detallecompramaterial_list'),
    path('DetalleCompraMaterial/create/', login_required(views.detallecompramaterial_create), name='detallecompramaterial_create'),
    path('DetalleCompraMaterial/update/<int:pk>/', login_required(views.detallecompramaterial_update), name='detallecompramaterial_update'),
    path('DetalleCompraMaterial/delete/<int:pk>/', login_required(views.detallecompramaterial_delete), name='detallecompramaterial_delete'),





    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
