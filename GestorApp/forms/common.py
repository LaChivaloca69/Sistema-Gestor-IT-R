"""Helpers compartidos de formularios."""
from datetime import datetime
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .. import document_engine
from ..cobertura import operativo_user_choices
from ..models import (
    AccionHistorial,
    AgendaMantenimiento,
    Answer,
    Area,
    AsignacionEquipo,
    Bitacora,
    CategoriaEquipo,
    CoberturaTickets,
    DetalleOrdenCompra,
    Edificio,
    Equipo,
    EstadoAsignacion,
    EstadoEquipo,
    EstadoMantenimiento,
    EstadoOrdenCompra,
    EstadoSolicitudEquipo,
    EstadoSupport,
    IvaOpcion,
    Mantenimiento,
    MovimientoEquipo,
    OrdenCompra,
    OrigenAltaEquipo,
    Personal,
    PlantillaDocumento,
    Proveedor,
    Puesto,
    SeguimientoTicket,
    SolicitudEquipo,
    TicketIT,
    TipoPlantillaDocumento,
    TipoProveedor,
    Ubicacion,
    UrgenciaSolicitudEquipo,
    ZonaEdificio,
)
from ..roles import (
    ROLE_ADMIN,
    ROLE_CHOICES,
    ROLE_TECNICO,
    ROLE_USUARIO,
    get_user_role,
    is_admin_user,
    is_operativo,
    operativo_users_queryset,
    set_user_role,
)



def get_subtipo_ticket_choices(tipo_ticket):
    opciones_por_tipo = {
        # "HELPDESK": [("SUBTIPO_1", "Subtipo 1"), ("SUBTIPO_2", "Subtipo 2")],
        "ADMINISTRACION": [("AAF Compartir Archivos", "AAF COMPARTIR ARCHIVOS"), ("Intranet", "INTRANET"), ("Backup/Restore", "BACKUP/RESTORE"), ("Barracuda SPAM FIREWALL", "BARRACUDA SPAM FIREWALL"), 
                           ("Cadency", "CADENCY"), ("CER", "CER"), ("Impresoras Kónica", "IMPRESORAS KONICA"), ("Administracion LAN", "ADMINISTRACION LAN"), ("Microsoft 365", "MICROSOFT 365"), 
                           ("Microsoft Teams", "MICROSOFT TEAMS"), ("Mitel", "MITEL"), ("Problemas de Password", "PROBLEMAS DE PASSWORD (DESBLOQUEAR)"), ("Aplicaciones del Teléfono", "APLICACIONES DEL TELEFONO"), 
                           ("Solicitud de Proyecto", "SOLICITUD DE PROYECTO"), ("Petición de Compra", "PETICION DE COMPRA (HARDWARE/SOFTWARE)"), ("QlikView", "QLICKVIEW"), 
                           ("DAIKIN CORNERSTONE", "DAIKIN CORNERSTONE"), ("SAP", "SAP"), ("SAP GUIXT", "SAP GUIXT"), ("Seguridad", "SEGURIDAD"), ("Servidores", "SERVIDORES"), ("SharePoint", "SHAREPOINT"), 
                           ("Trustwave", "TRUSTWAVE"), ("Videoconferencia", "VIDEOCONFERENCIA"), ("Correo de Voz", "CORREO DE VOZ"), ("VPN", "VPN"), ("WINDOWS 10", "WINDOWS 10"), ("WINDOWS SERVER", "WINDOWS SERVER"), 
                           ("WIRELESS ACCESS POINTS", "WIRELESS ACCES POINTS"), ("Otro", "OTRO")],
        "BPCS": [("BPCS SEGURIDAD", "BPCS SEGURIDAD"), ("BPCS CAMBIOS", "BPCS CAMBIOS"), ("BPCS PROBLEMAS CON ORDENES", "BPCS PROBLEMAS CON ORDENES"), ("BPCS PROBLEMAS CON IMPRESIONES", "BPCS PROBLEMAS CON IMPRESIONES"), ("OTRO", "OTRO")],
        "HARDWARE": [("Alarma de seguridad", "ALARMA DE SEGURIDAD"), ("Camaras de Seguridad", "CAMARAS DE SEGURIDAD"), ("Telefono de escritorio", "TELEFONO DE ESCRITORIO"), ("Desktop", "DESKTOP"), 
                           ("Laptop", "LAPTOP"), ("Mantenimiento", "MANTENIMIENTO"), ("Monitor", "MONITOR"), ("Impresora", "IMPRESORA"), ("Petición de Compra", "PETICION DE COMPRA (HARDWARE/SOFTWARE)"), 
                           ("Escaner RF", "ESCANER RF"), ("Escaner 1D/2D", "ESCANER 1D/2D"), ("Tablet", "TABLET"), ("Checador", "CHECADOR"), 
                           ("Reloj", "RELOJ"), ("WIRELESS ACCESS POINTS", "WIRELESS ACCES POINTS"), ("Problemas con equipo", "PROBLEMAS CON EQUIPO"), ("Otro", "OTRO")],
        "HELPDESK": [("Alarma de seguridad", "ALARMA DE SEGURIDAD"), ("AAF Compartir Archivos", "AAF COMPARTIR ARCHIVOS"), ("ADOBE", "ADOBE"), ("AUTOCAD Software", "AUTOCAD SOFTWARE"), 
                           ("TRESS Software", "TRESS SOFTWARE"), ("CONTRAQ Software", "CONTRAQ SOFTWARE"), ("Backup/Restore", "BACKUP/RESTORE"), ("Import Software", "IXPORT SOFTWARE"), ("Barracuda SPAM FIREWALL", "BARRACUDA SPAM FIREWALL"), 
                           ("Copiadora/Equipo Multifuncional", "COPIADORA/EQUIPO MULTIFUNCIONAL"), ("Desktop", "DESKTOP"), ("Hard Drive", "HARD DRIVE"), ("Teclado/Mouse", "TECLADO/MOUSE"), 
                           ("Laptop", "LAPTOP"), ("Problemas de Password", "PROBLEMAS DE PASSWORD (DESBLOQUEAR)"), ("Impresora", "IMPRESORA"), ("Impresiones", "IMPRESIONES"), 
                           ("Escaner RF", "ESCANER RF"), ("Escaner 1D/2D", "ESCANER 1D/2D"), ("Videoconferencia", "VIDEO CONFERENCIA"), ("Windows 10", "WINDOWS 10"), ("Internet", "INTERNET"), 
                           ("Otro", "OTRO")],
        "TELEFONIA": [("Configuracion", "CONFIGURACION (NUEVO/TERMINACION/CAMBIO)"), ("Telefono Celular", "TELEFONO CELULAR"), ("Tarjeta AT&T", "TARJETA AT&T"), ("Telefono De Escritorio", "TELEFONO DE ESCRITORIO"), 
                      ("FAX", "FAX"), ("Comunicacion Mitel", "COMUNICACION MITEL"), ("Actualizacion Directorio Telefonico", "ACTUALIZACION DIRECTORIO TELEFONICO"), ("Reemplazo de telefono", "REEMPLAZO DE TELEFONO"), ("Problemas con llamadas", "PROBLEMAS CON LLAMADAS"), 
                      ("Correo de Voz", "CORREO DE VOZ"), ("Otro", "OTRO")],
        "SOFTWARE": [("Tienda Web para Empleados", "TIENDA WEB PARA EMPLEADOS"), ("AAF Compartir Archivos", "AAF COMPARTIR ARCHIVOS"), ("Adobe", "ADOBE"), ("Bug/Error en Aplicacion", "BUG/ERROR EN APLICACION"), 
                           ("Problemas de Datos Aplicacion", "PROBLEMAS DE DATOS APLICACION"), ("AS/400", "AS/400"), ("AUTOCAD Software", "AUTOCAD SOFTWARE"), ("TRESS Software", "TRESS SOFTWARE"), ("CONTRAQ Software", "CONTRAQ SOFTWARE"), 
                           ("IXPORT SOFTWARE", "IXPORT SOFTWARE"), ("BARRACUDA SPAM FIREWALL", "BARRACUDA SPAM FIREWALL"), ("BPCS ACCESO A CLIENTES", "BPCS ACCESO A CLIENTES"), ("Cadency", "CADENCY"), 
                           ("CONFIGIT", "CONFIGIT"), ("Portal de Clientes", "PORTAL DE CLIENTES"), ("BPCS", "BPCS"), ("Servicios de Ingenieria", "SERVICIOS DE INGENIERIA"), 
                           ("FEDEX SHIP MANAGER", "FEDEX SHIP MANAGER"), ("JAVA", "JAVA"), ("Mantenimiento", "MANTENIMIENTO"), ("Microsoft 365", "MICROSOFT 365"), ("Microsoft Excel", "MICROSOFT EXCEL"), ("Microsoft Office", "MICROSOFT OFFICE"), 
                           ("Microsoft One Note", "MICROSOFT ONE NOTE"), ("Microsoft Power Point", "MICROSOFT POWER POINT"), ("Microsoft Outlook", "MICROSOFT OUTLOOK"), ("Microsoft Project", "MICROSOFT PROJECT"), ("Microsoft Teams", "MICROSOFT TEAMS"), 
                           ("Microsoft Visio", "MICROSOFT VISIO"), ("Microsoft Word", "MICROSOFT WORD"),("Minitab", "MINITAB"), ("Nueva Aplicacion/Otro", "NUEVA APLICACION/OTRO"), ("Aplicaciones del Telefono", "APLICACIONES DEL TELEFONO"), ("Policies Tech", "POLICIES TECH"), 
                           ("Impresiones", "IMPRESIONES"), ("QLICKVIEW", "QLICKVIEW"), ("Daikin Cornerstone", "DAIKIN CORNERSTONE"), ("SAP", "SAP"), ("SAP Seguridad", "SAP SEGURIDAD"), ("SAP Mantenimiento de Datos", "SAP MANTENIMIENTO DE DATOS"), ("SAP Forms", "SAP FORMS"), 
                           ("SAP GUIXT", "SAP GUIXT"), ("SAP Interfaces", "SAP INTERFACES"), ("SAP Reports", "SAP REPORTS"), ("Camaras de Seguridad", "CAMARAS DE SEGURIDAD"), ("SHAREPOINT", "SHAREPOINT"), ("SMOTHIE MAMBO", "SMOPTHIE MAMBO"), 
                           ("Trustwave", "TRUSTWAVE"), ("Ups Worldship", "UPS WORLDSHIP"), ("FTP", "FTP"), ("VPN", "VPN"), ("Otro", "OTRO")],
        "MANTENIMIENTO": [
            ("Preventivo", "PREVENTIVO"),
            ("Correctivo", "CORRECTIVO"),
            ("Equipo asignado", "EQUIPO ASIGNADO"),
            ("Solicitud general", "SOLICITUD GENERAL"),
            ("Otro", "OTRO"),
        ],
    }
    opciones = opciones_por_tipo.get(tipo_ticket, [])
    return [("", "---------")] + list(opciones)



def get_tipo_equipo_queryset(current_value=None):
    qs = CategoriaEquipo.objects.filter(activo=True).order_by("nombre_categoria")
    if current_value and current_value.pk:
        qs = (CategoriaEquipo.objects.filter(pk=current_value.pk) | qs).distinct()
    return qs



def _get_user_personal(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.personal_profile
    except Personal.DoesNotExist:
        return None



def _get_personal_active_assignments(personal):
    if not personal:
        return AsignacionEquipo.objects.none()
    return (
        AsignacionEquipo.objects.select_related("equipo__categoria")
        .filter(personal=personal, estado_asignacion=EstadoAsignacion.ACTIVA)
        .order_by("-fecha_asignacion")
    )


def _get_personal_active_assignment(personal):
    return _get_personal_active_assignments(personal).first()


def _get_personal_active_equipos(personal):
    return Equipo.objects.filter(
        pk__in=_get_personal_active_assignments(personal).values("equipo_id")
    ).order_by("codigo_inventario")

