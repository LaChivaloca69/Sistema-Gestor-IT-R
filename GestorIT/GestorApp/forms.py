from datetime import datetime

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    Answer,
    CategoriaEquipo,
    EstadoSupport,
    Personal,
    SeguimientoTicket,
    TicketIT,
    Ubicacion,
    ZonaEdificio,
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
    fecha_support_client = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = TicketIT
        exclude = ["folio_ticket", "fecha_support"]

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
        if "equipo" in self.fields:
            self.fields["equipo"].label_from_instance = (
                lambda obj: f"{obj.codigo_inventario} - {obj.categoria}"
            )

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        if not imagen:
            return imagen

        max_size = 50 * 1024 * 1024
        if imagen.size > max_size:
            raise forms.ValidationError("La imagen debe pesar menos de 50 MB.")

        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        content_type = getattr(imagen, "content_type", None)
        if content_type and content_type not in allowed_types:
            raise forms.ValidationError("Formato no permitido. Usa JPG, JPEG, PNG, GIF o WEBP.")

        return imagen

    def _parse_client_datetime(self, value):
        if not value:
            return None

        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def save(self, commit=True):
        instance = super().save(commit=False)
        client_value = self.cleaned_data.get("fecha_support_client")
        client_datetime = self._parse_client_datetime(client_value)
        if client_datetime and not instance.pk:
            instance.fecha_support = client_datetime

        if commit:
            instance.save()
            self.save_m2m()
        return instance


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
    numero_empleado = forms.CharField(max_length=30, label="Numero de empleado")
    nombre = forms.CharField(max_length=100, label="Nombre")
    apellido_paterno = forms.CharField(max_length=100, label="Apellido paterno")
    apellido_materno = forms.CharField(max_length=100, label="Apellido materno", required=False)
    solicitar_admin = forms.BooleanField(
        required=False,
        label="Solicitar admin",
        help_text="Un admin debe aprobar la solicitud.",
    )

    class Meta:
        model = User
        fields = ["username", "password1", "password2"]

    def clean_numero_empleado(self):
        numero_empleado = self.cleaned_data.get("numero_empleado", "").strip()
        if Personal.objects.filter(numero_empleado__iexact=numero_empleado).exists():
            raise forms.ValidationError("El numero de empleado ya esta registrado.")
        return numero_empleado

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)

        with transaction.atomic():
            user = super().save(commit=True)
            Personal.objects.create(
                user=user,
                numero_empleado=self.cleaned_data["numero_empleado"],
                nombre=self.cleaned_data["nombre"],
                apellido_paterno=self.cleaned_data["apellido_paterno"],
                apellido_materno=self.cleaned_data.get("apellido_materno") or None,
                admin_requested=self.cleaned_data.get("solicitar_admin", False),
            )
        return user
