from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import (
    Answer,
    CategoriaEquipo,
    EstadoSupport,
    SeguimientoTicket,
    TicketIT,
    Ubicacion,
    ZonaEdificio,
)


def get_subtipo_ticket_choices(tipo_ticket):
    opciones_por_tipo = {
        # "HELPDESK": [("SUBTIPO_1", "Subtipo 1"), ("SUBTIPO_2", "Subtipo 2")],
        "ADMINISTRACION": [("Subtipo_1", "AAF COMPARTIR ARCHIVOS"), ("Subtipo_2", "INTRANET"), ("subtipo_3", "BACKUP/RESTORE"), ("Subtipo_4", "BARRACUDA SPAM FIREWALL"), 
                           ("Subtipo_5", "CADENCY"), ("Subtipo_6", "CER"), ("Subtipo_7", "IMPRESORAS KONICA"), ("Subtipo_8", "ADMINISTRACION LAN"), ("Subtipo_9", "MICROSOFT 365"), 
                           ("Subtipo_10", "MICROSOFT TEAMS"), ("Subtipo_11", "MITEL"), ("Subtipo_12", "PROBLEMAS DE PASSWORD (DESBLOQUEAR)"), ("Subtipo_13", "APLICACIONES DEL TELEFONO"), 
                           ("Subtipo_14", "SOLICITUD DE PROYECTO"), ("Subtipo_15", "PETICION DE COMPRA (HARDWARE/SOFTWARE)"), ("Subtipo_16", "QLICKVIEW"), 
                           ("Subtipo_17", "DAIKIN CORNERSTONE"), ("Subtipo_18", "SAP"), ("Subtipo_19", "SAP GUIXT"), ("Subtipo_20", "SEGURIDAD"), ("Subtipo_21", "SERVIDORES"), ("Subtipo_22", "SHAREPOINT"), 
                           ("Subtipo_23", "TRUSTWAVE"), ("Subtipo_24", "VIDEOCONFERENCIA"), ("Subtipo_25", "CORREO DE VOZ"), ("Subtipo_26", "VPN"), ("Subtipo_27", "WINDOWS 10"), ("Subtipo_28", "WINDOWS SERVER"), 
                           ("Subtipo_29", "WIRELESS ACCES POINTS"), ("Subtipo_30", "OTRO")],
        "BPCS": [("Subtipo_1", "BPCS SEGURIDAD"), ("Subtipo_2", "BPCS CAMBIOS"), ("Subtipo_3", "BPCS PROBLEMAS CON ORDENES"), ("Subtipo_5", "BPCS PROBLEMAS CON IMPRESIONES"), ("Subtipo_7", "OTRO")],
        "HARDWARE": [("Subtipo_1", "ALARMA DE SEGURIDAD"), ("Subtipo_2", "CAMARAS DE SEGURIDAD"), ("subtipo_3", "TELEFONO DE ESCRITORIO"), ("Subtipo_4", "DESKTOP"), 
                           ("Subtipo_5", "LAPTOP"), ("Subtipo_6", "MANTENIMIENTO"), ("Subtipo_7", "MONITOR"), ("Subtipo_8", "IMPRESORA"), ("Subtipo_9", "PETICIPON DE COMPRA (HARDWARE/SOFTWARE)"), 
                           ("Subtipo_10", "ESCANER RF"), ("Subtipo_11", "ESCANER 1D/2D"), ("Subtipo_12", "TABLET"), ("Subtipo_13", "CHECADOR"), 
                           ("Subtipo_14", "RELOJ"), ("Subtipo_15", "WIRELESS ACCES POINTS"), ("Subtipo_16", "PROBLEMAS CON EQUIPO"), ("Subtipo_17", "OTRO")],
        "HELPDESK": [("Subtipo_1", "ALARMA DE SEGURIDAD"), ("Subtipo_2", "AAF COMPARTIR ARCHIVOS"), ("subtipo_3", "ADOBE"), ("Subtipo_4", "AUTOCAD SOFTWARE"), 
                           ("Subtipo_5", "TRESS SOFTWARE"), ("Subtipo_6", "CONTRAQ SOFTWARE"), ("Subtipo_7", "BACKUP/RESTORE"), ("Subtipo_8", "IXPORT SOFTWARE"), ("Subtipo_9", "BARRACUDA SPAM FIREWALL"), 
                           ("Subtipo_10", "COPIADORA/EQUIPO MULTIFUNCIONAL"), ("Subtipo_11", "DESKTOP"), ("Subtipo_12", "HARD DRIVE"), ("Subtipo_13", "TECLADO/MOUSE"), 
                           ("Subtipo_14", "LAPTOP"), ("Subtipo_15", "PROBLEMAS DE PASSWORD (DESBLOQUEAR)"), ("Subtipo_16", "IMPRESORA"), ("Subtipo_17", "IMPRESIONES"), 
                           ("Subtipo_18", "ESCANER RF"), ("Subtipo_19", "ESCANER 1D/2D"), ("Subtipo_20", "VIDEO CONFERENCIA"), ("Subtipo_21", "WINDOWS 10"), ("Subtipo_22", "INTERNET"), 
                           ("Subtipo_23", "OTRO")],
        "TELEFONIA": [("Subtipo_1", "CONFIGURACION (NUEVO/TERMINACION/CAMBIO)"), ("Subtipo_2", "TELEFONO CELULAR"), ("Subtipo_3", "TARJETA AT&T"), ("Subtipo_4", "TELEFONO DE ESCRITORIO"), 
                      ("Subtipo_5", "FAX"), ("Subtipo_6", "COMUNICACION MITEL"), ("Subtipo_7", "ACTUALIZACION DIRECTORIO TELEFONICO"), ("Subtipo_8", "REEMPLAZO DE TELEFONO"), ("Subtipo_9", "PROBLEMAS CON LLAMADAS"), 
                      ("Subtipo_10", "CORREO DE VOZ"), ("Subtipo_11", "OTRO")],
        "SOFTWARE": [("Subtipo_1", "TIENDA WEB PARA EMPLEADOS"), ("Subtipo_2", "AAF COMPARTIR ARCHIVOS"), ("subtipo_3", "ADOBE"), ("Subtipo_4", "BUG/ERROR EN APLICACION"), 
                           ("Subtipo_5", "PROBLEMAS DE DATOS APLICACION"), ("Subtipo_6", "AS/400"), ("Subtipo_7", "AUTOCAD SOFTWARE"), ("Subtipo_8", "TRESS SOFTWARE"), ("Subtipo_9", "CONTRAQ SOFTWARE"), 
                           ("Subtipo_10", "IXPORT SOFTWARE"), ("Subtipo_11", "BARRACUDA SPAM FIREWALL"), ("Subtipo_12", "BPCS ACCESO A CLIENTES"), ("Subtipo_13", "CADENCY"), 
                           ("Subtipo_14", "CONFIGIT"), ("Subtipo_15", "PORTAL DE CLIENTES"), ("Subtipo_16", "BPCS"), ("Subtipo_17", "SERVICIOS DE INGENIERIA"), 
                           ("Subtipo_18", "FEDEX SHIP MANAGER"), ("Subtipo_19", "JAVA"), ("Subtipo_20", "MANTENIMIENTO"), ("Subtipo_21", "MICROSOFT 365"), ("Subtipo_22", "MICROSOFT EXCEL"), ("Subtipo_23", "MICROSOFT OFFICE"), 
                           ("Subtipo_24", "MICROSOFT ONE NOTE"), ("Subtipo_25", "MICROSOFT POWER POINT"), ("Subtipo_26", "MICROSOFT OUTLOOK"), ("Subtipo_27", "MICROSOFT PROJECT"), ("Subtipo_28", "MICROSOFT TEAMS"), ("Subtipo_29", "MICROSOFT VISIO"), 
                           ("Subtipo_30", "MICROSOFT WORD"),("Subtipo_31", "MINITAB"), ("Subtipo_32", "NUEVA APLICACION/OTRO"), ("Subtipo_33", "APLICACIONES DEL TELEFONO"), ("Subtipo_34", "POLICIES TECH"), ("Subtipo_35", "IMPRESIONES"), 
                           ("Subtipo_36", "QLICKVIEW"), ("Subtipo_37", "DAIKIN CORNERSTONE"), ("Subtipo_38", "SAP"), ("Subtipo_39", "SAP SEGURIDAD"), ("Subtipo_40", "SAP MANTENIMIENTO DE DATOS"), ("Subtipo_41", "SAP FORMS"), 
                           ("Subtipo_42", "SAP GUIXT"), ("Subtipo_43", "SAP INTERFACES"), ("Subtipo_44", "SAP REPORTS"), ("Subtipo_45", "CAMARAS DE SEGURIDAD"), ("Subtipo_46", "SHAREPOINT"), ("Subtipo_47", "SMOPTHIE MAMBO"), 
                           ("Subtipo_48", "TRUSTWAVE"), ("Subtipo_49", "UPS WORLDSHIP"), ("Subtipo_50", "FTP"), ("Subtipo_51", "VPN"), 
                           ("Subtipo_52", "OTRO")],
    }
    opciones = opciones_por_tipo.get(tipo_ticket, [])
    return [("", "---------")] + list(opciones)


def get_tipo_equipo_queryset(current_value=None):
    qs = CategoriaEquipo.objects.filter(activo=True).order_by("nombre_categoria")
    if current_value and current_value.pk:
        qs = (CategoriaEquipo.objects.filter(pk=current_value.pk) | qs).distinct()
    return qs


class TicketITForm(forms.ModelForm):
    sub_tipo_ticket = forms.ChoiceField(required=False, choices=[])

    class Meta:
        model = TicketIT
        exclude = ["folio_ticket"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tipo_ticket = None
        if self.data.get("tipo_ticket"):
            tipo_ticket = self.data.get("tipo_ticket")
        elif self.instance and self.instance.pk:
            tipo_ticket = self.instance.tipo_ticket

        self.fields["sub_tipo_ticket"].choices = get_subtipo_ticket_choices(tipo_ticket)
        current_tipo_equipo = None
        if self.instance and self.instance.pk:
            current_tipo_equipo = self.instance.tipo_equipo
        self.fields["tipo_equipo"].queryset = get_tipo_equipo_queryset(current_tipo_equipo)


class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        edificio_id = None
        if self.data.get("edificio"):
            edificio_id = self.data.get("edificio")
        elif self.instance and self.instance.pk:
            edificio_id = self.instance.edificio_id

        if edificio_id:
            self.fields["zona"].queryset = ZonaEdificio.objects.filter(
                edificio_id=edificio_id,
                activo=True,
            ).order_by("nombre_zona")
        else:
            self.fields["zona"].queryset = ZonaEdificio.objects.none()


class SeguimientoTicketForm(forms.ModelForm):
    class Meta:
        model = SeguimientoTicket
        fields = [
            "ticket",
            "fecha_check",
            "usuario",
            "solucion",
            "observacion",
            "ya_terminado",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TicketIT.objects.filter(
            status=EstadoSupport.ABIERTO,
            ticket_check__isnull=True,
        )
        if self.instance and self.instance.ticket_id:
            qs = TicketIT.objects.filter(
                Q(status=EstadoSupport.ABIERTO, ticket_check__isnull=True)
                | Q(pk=self.instance.ticket_id)
            )
        self.fields["ticket"].queryset = qs.order_by("folio_ticket")


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = [
            "bitacora",
            "fecha_answer",
            "solucion",
            "descripcion_solucion",
        ]


class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "password1", "password2"]
