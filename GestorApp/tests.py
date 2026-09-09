from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from GestorApp.models import (
    Answer,
    AsignacionEquipo,
    Bitacora,
    CategoriaEquipo,
    CoberturaTickets,
    ComentarioTicket,
    Edificio,
    Equipo,
    EstadoAsignacion,
    EstadoEquipo,
    EstadoMantenimiento,
    EstadoOrdenCompra,
    EstadoSolicitudEquipo,
    EstadoSupport,
    HistorialActividad,
    Mantenimiento,
    ModuloHistorial,
    OrdenCompra,
    OrigenOrdenCompra,
    Personal,
    ProductoConsumible,
    SeguimientoTicket,
    SolicitudEquipo,
    TicketIT,
    TipoCategoriaInventario,
    TipoMovimiento,
    TipoMovimientoStock,
    Ubicacion,
    ZonaEdificio,
)
from GestorApp.roles import ROLE_ADMIN, ROLE_TECNICO, ROLE_USUARIO, ensure_role_groups, set_user_role
from GestorApp import historial as historial_mod


User = get_user_model()


class AuthFlowTests(TestCase):
    @override_settings(SIGNUP_ENABLED=True)
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "testuser",
                "numero_empleado": "EMP-100",
                "nombre": "Test",
                "apellido_paterno": "User",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="testuser").exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_signup_desactivado_redirige_a_login(self):
        response = self.client.get(reverse("signup"))
        self.assertRedirects(response, reverse("login"))
        post = self.client.post(
            reverse("signup"),
            {
                "username": "blockeduser",
                "numero_empleado": "EMP-101",
                "nombre": "Blocked",
                "apellido_paterno": "User",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(post, reverse("login"))
        self.assertFalse(User.objects.filter(username="blockeduser").exists())

    def test_login_success_redirects_home(self):
        User.objects.create_user(username="testuser", password="StrongPass123!")

        response = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": "StrongPass123!"},
        )

        self.assertRedirects(response, reverse("home"))

    def test_login_failure_shows_error(self):
        User.objects.create_user(username="testuser", password="StrongPass123!")

        response = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": "BadPass123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        form = response.context.get("form")
        self.assertIsNotNone(form)
        self.assertTrue(form.errors)
        self.assertContains(response, "No se pudo iniciar sesion")
        self.assertContains(response, "Usuario o contraseña incorrectos")


class SmokeFlowTests(TestCase):
    """Camino critico: login → home → tickets → detalle → form crear equipo."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            username="smoke_tech",
            password=self.password,
            first_name="Smoke",
            last_name="Tech",
        )
        set_user_role(self.user, ROLE_TECNICO)
        self.ticket = TicketIT.objects.create(
            descripcion="Ticket de humo para pruebas",
            requerimiento="Prueba smoke",
            solicitado_por=self.user,
        )
        self.categoria = CategoriaEquipo.objects.create(nombre_categoria="Smoke Cat")

    def test_smoke_login_home_tickets_detail_equipo_form(self):
        login_ok = self.client.login(username="smoke_tech", password=self.password)
        self.assertTrue(login_ok)

        home = self.client.get(reverse("home"))
        self.assertEqual(home.status_code, 200)

        tickets = self.client.get(reverse("ticketit_list"))
        self.assertEqual(tickets.status_code, 200)
        self.assertContains(tickets, self.ticket.folio_ticket)

        detail = self.client.get(reverse("ticketit_detail", args=[self.ticket.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, self.ticket.folio_ticket)

        equipo_form = self.client.get(reverse("equipo_create"))
        self.assertEqual(equipo_form.status_code, 200)
        self.assertContains(equipo_form, "codigo_inventario")

        # Alta minima de equipo (legado, sin OC). Estado/activo salen del default del modelo.
        create = self.client.post(
            reverse("equipo_create"),
            {
                "codigo_inventario": "SMOKE-EQ-001",
                "categoria": self.categoria.pk,
                "origen_alta": "Legado",
                "fecha_alta": "2026-01-15",
            },
        )
        self.assertEqual(create.status_code, 302)
        creado = Equipo.objects.get(codigo_inventario="SMOKE-EQ-001")
        self.assertEqual(creado.estado_equipo, EstadoEquipo.DISPONIBLE)
        self.assertTrue(creado.activo)


class EquipoFormCriticosTests(TestCase):
    """Bypass de baja/reactivacion y numero_serie vacio."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.tech = User.objects.create_user(username="eq_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.admin = User.objects.create_user(username="eq_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)
        self.categoria = CategoriaEquipo.objects.create(nombre_categoria="Laptops Crit")
        self.equipo = Equipo.objects.create(
            codigo_inventario="CRIT-EQ-001",
            categoria=self.categoria,
            origen_alta="Legado",
            estado_equipo=EstadoEquipo.DISPONIBLE,
            activo=True,
        )

    def _update_payload(self, **overrides):
        data = {
            "codigo_inventario": self.equipo.codigo_inventario,
            "categoria": self.categoria.pk,
            "origen_alta": "Legado",
            "fecha_alta": "2026-01-15",
            "numero_serie": "",
            "marca": "",
            "modelo": "",
            "Numero_Pedimiento": "",
            "descripcion_equipo": "",
            "proveedor": "",
            "orden_compra": "",
            "detalle_orden": "",
            "ubicacion": "",
        }
        data.update(overrides)
        return data

    def test_update_ignora_estado_baja_en_post(self):
        self.client.login(username="eq_tech", password=self.password)
        response = self.client.post(
            reverse("equipo_update", args=[self.equipo.pk]),
            self._update_payload(estado_equipo="Baja", activo=""),
        )
        self.assertEqual(response.status_code, 302)
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_equipo, EstadoEquipo.DISPONIBLE)
        self.assertTrue(self.equipo.activo)

    def test_form_no_incluye_estado_ni_activo(self):
        from GestorApp.forms.equipo import EquipoForm

        form = EquipoForm(tipo=self.categoria.tipo)
        self.assertNotIn("estado_equipo", form.fields)
        self.assertNotIn("activo", form.fields)

    def test_varios_equipos_sin_serie_no_rompen_unique(self):
        self.client.login(username="eq_tech", password=self.password)
        for i in range(2):
            response = self.client.post(
                reverse("equipo_create"),
                {
                    "codigo_inventario": f"CRIT-SERIE-{i}",
                    "categoria": self.categoria.pk,
                    "origen_alta": "Legado",
                    "fecha_alta": "2026-01-15",
                    "numero_serie": "   ",
                },
            )
            self.assertEqual(response.status_code, 302, msg=response.content[:500] if response.status_code != 302 else "")
        equipos = Equipo.objects.filter(codigo_inventario__startswith="CRIT-SERIE-")
        self.assertEqual(equipos.count(), 2)
        self.assertTrue(all(e.numero_serie is None for e in equipos))

    def test_tags_opcionales_con_longitud_exacta(self):
        from GestorApp.forms.equipo import EquipoForm

        base = {
            "codigo_inventario": "CRIT-TAG-001",
            "categoria": self.categoria.pk,
            "origen_alta": "Legado",
            "fecha_alta": "2026-01-15",
            "numero_serie": "",
            "marca": "",
            "modelo": "",
            "Numero_Pedimiento": "",
            "descripcion_equipo": "",
            "proveedor": "",
            "orden_compra": "",
            "detalle_orden": "",
            "ubicacion": "",
        }
        ok = EquipoForm(
            {**base, "tag_1": "123456", "tag_2": "7890"},
            tipo=self.categoria.tipo,
        )
        self.assertTrue(ok.is_valid(), ok.errors)
        equipo = ok.save()
        self.assertEqual(equipo.tag_1, "123456")
        self.assertEqual(equipo.tag_2, "7890")

        vacio = EquipoForm(
            {**base, "codigo_inventario": "CRIT-TAG-002", "tag_1": "", "tag_2": ""},
            tipo=self.categoria.tipo,
        )
        self.assertTrue(vacio.is_valid(), vacio.errors)
        self.assertIsNone(vacio.save().tag_1)

        malo = EquipoForm(
            {**base, "codigo_inventario": "CRIT-TAG-003", "tag_1": "12345", "tag_2": "12"},
            tipo=self.categoria.tipo,
        )
        self.assertFalse(malo.is_valid())
        self.assertIn("tag_1", malo.errors)
        self.assertIn("tag_2", malo.errors)


class AltosMantenimientoPersonalComprasTests(TestCase):
    """Regresion altos #3-#7: iniciar, combo tecnico, personal delete, cancelar, OC PDF."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.admin = User.objects.create_user(username="alto_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)
        self.tech = User.objects.create_user(username="alto_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.categoria = CategoriaEquipo.objects.create(nombre_categoria="Alto Cat")

    def test_iniciar_mantenimiento_con_equipo_baja_no_deja_en_proceso(self):
        equipo = Equipo.objects.create(
            codigo_inventario="ALTO-BAJA-001",
            categoria=self.categoria,
            origen_alta="Legado",
            estado_equipo=EstadoEquipo.BAJA,
            activo=False,
        )
        man = Mantenimiento.objects.create(
            equipo=equipo,
            tipo_mantenimiento="Correctivo",
            fecha_programada=date.today(),
            estado_mantenimiento=EstadoMantenimiento.PROGRAMADO,
        )
        self.client.login(username="alto_tech", password=self.password)
        response = self.client.post(reverse("mantenimiento_iniciar", args=[man.pk]))
        self.assertEqual(response.status_code, 302)
        man.refresh_from_db()
        equipo.refresh_from_db()
        self.assertEqual(man.estado_mantenimiento, EstadoMantenimiento.PROGRAMADO)
        self.assertEqual(equipo.estado_equipo, EstadoEquipo.BAJA)

    def test_mantenimiento_form_incluye_tecnico_it(self):
        from GestorApp.forms.mantenimiento import MantenimientoForm

        form = MantenimientoForm()
        values = {value for value, _label in form.fields["tecnico_responsable"].choices}
        self.assertIn("alto_tech", values)
        self.assertIn("alto_admin", values)

    def test_personal_delete_libera_equipos_asignados(self):
        user = User.objects.create_user(username="alto_emp", password=self.password)
        set_user_role(user, ROLE_USUARIO)
        personal = Personal.objects.create(
            numero_empleado="EMP-ALTO-1",
            nombre="Empleado",
            apellido_paterno="Prueba",
            user=user,
            activo=True,
        )
        equipo = Equipo.objects.create(
            codigo_inventario="ALTO-ASIG-001",
            categoria=self.categoria,
            origen_alta="Legado",
            estado_equipo=EstadoEquipo.ASIGNADO,
            activo=True,
        )
        AsignacionEquipo.objects.create(
            equipo=equipo,
            personal=personal,
            estado_asignacion=EstadoAsignacion.ACTIVA,
        )
        self.client.login(username="alto_admin", password=self.password)
        response = self.client.post(reverse("personal_delete", args=[personal.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Personal.objects.filter(pk=personal.pk).exists())
        equipo.refresh_from_db()
        self.assertEqual(equipo.estado_equipo, EstadoEquipo.DISPONIBLE)
        self.assertFalse(
            AsignacionEquipo.objects.filter(
                equipo=equipo,
                estado_asignacion=EstadoAsignacion.ACTIVA,
            ).exists()
        )
        user.refresh_from_db()
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(user.is_active)

    def test_no_cancelar_solicitud_completada(self):
        solicitante = User.objects.create_user(username="alto_sol", password=self.password)
        set_user_role(solicitante, ROLE_USUARIO)
        solicitud = SolicitudEquipo.objects.create(
            solicitante=solicitante,
            titulo="Monitor",
            justificacion="Necesito monitor",
            estado=EstadoSolicitudEquipo.COMPLETADA,
        )
        self.client.login(username="alto_tech", password=self.password)
        response = self.client.post(
            reverse("solicitud_equipo_cancelar", args=[solicitud.pk])
        )
        self.assertEqual(response.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, EstadoSolicitudEquipo.COMPLETADA)

    def test_oc_subida_update_sin_reenviar_pdf(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from GestorApp.forms.compras import OrdenCompraSubirForm

        pdf = SimpleUploadedFile(
            "orden.pdf",
            b"%PDF-1.4 minimal",
            content_type="application/pdf",
        )
        orden = OrdenCompra.objects.create(
            origen=OrigenOrdenCompra.SUBIDO,
            folio_orden="OC-ALTO-001",
            notas="inicial",
        )
        orden.archivo_pdf.save("orden.pdf", pdf, save=True)
        form = OrdenCompraSubirForm(
            data={
                "folio_orden": orden.folio_orden,
                "estado": orden.estado,
                "notas": "actualizado sin pdf",
            },
            files={},
            instance=orden,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        orden.refresh_from_db()
        self.assertEqual(orden.notas, "actualizado sin pdf")
        self.assertTrue(orden.archivo_pdf)


class AuditoriaHistorialTests(TestCase):
    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.admin = User.objects.create_user(username="audit_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)
        self.other = User.objects.create_user(username="audit_other", password=self.password)
        set_user_role(self.other, ROLE_TECNICO)

        self.entry = historial_mod.registrar_historial(
            modulo=ModuloHistorial.TICKET,
            accion=historial_mod.AccionHistorial.CREACION,
            titulo="Evento de auditoria smoke",
            usuario=self.other,
            descripcion="Detalle de prueba",
        )

    def test_auditoria_list_filters_by_user_and_module(self):
        self.client.login(username="audit_admin", password=self.password)
        url = reverse("movimientoequipo_list")

        resp = self.client.get(url, {"usuario": str(self.other.pk), "modulo": "ticket"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Evento de auditoria smoke")

        resp_empty = self.client.get(url, {"usuario": str(self.admin.pk)})
        self.assertEqual(resp_empty.status_code, 200)
        self.assertNotContains(resp_empty, "Evento de auditoria smoke")

    def test_auditoria_detail(self):
        self.client.login(username="audit_admin", password=self.password)
        resp = self.client.get(reverse("historial_actividad_detail", args=[self.entry.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Evento de auditoria smoke")
        self.assertContains(resp, "audit_other")

    def test_auditoria_list_survives_list_url_with_pk(self):
        """Coberturas se guardaron con enlace_nombre=cobertura_list + pk; no debe 500."""
        historial_mod.registrar_historial(
            modulo=ModuloHistorial.GOBIERNO,
            accion=historial_mod.AccionHistorial.CREACION,
            titulo="Cobertura: suplente cubre a ausente",
            usuario=self.other,
            enlace_nombre="cobertura_list",
            enlace_pk=1,
        )
        self.client.login(username="audit_admin", password=self.password)
        resp = self.client.get(reverse("movimientoequipo_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cobertura: suplente cubre a ausente")
        self.assertContains(resp, reverse("cobertura_list"))


class MediaHardeningTests(TestCase):
    def test_rejects_exe_disguised_as_pdf(self):
        from django.core.exceptions import ValidationError
        from django.core.files.uploadedfile import SimpleUploadedFile

        from GestorApp.media_security import validate_pdf_upload

        fake = SimpleUploadedFile(
            "malware.pdf",
            b"MZ\x90\x00this-is-not-a-pdf",
            content_type="application/pdf",
        )
        with self.assertRaises(ValidationError):
            validate_pdf_upload(fake)

    def test_accepts_valid_png_and_renames(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from GestorApp.media_security import validate_image_upload

        png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        uploaded = SimpleUploadedFile(
            "../../evil name.PNG",
            png,
            content_type="image/png",
        )
        result = validate_image_upload(uploaded)
        self.assertTrue(result.name.endswith(".png"))
        self.assertNotIn("..", result.name)
        self.assertNotIn("evil", result.name.lower())

    def test_rejects_oversized_image(self):
        from django.core.exceptions import ValidationError
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings

        from GestorApp.media_security import validate_image_upload

        tiny_png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        uploaded = SimpleUploadedFile("big.png", tiny_png_header, content_type="image/png")
        with override_settings(MEDIA_UPLOAD={"image_max_bytes": 50}):
            with self.assertRaises(ValidationError):
                validate_image_upload(uploaded)


class TicketCreateEquipoChoicesTests(TestCase):
    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            username="ticket_user",
            password=self.password,
        )
        set_user_role(self.user, ROLE_USUARIO)
        self.personal = Personal.objects.create(
            numero_empleado="EMP-T01",
            user=self.user,
            nombre="Ticket",
            apellido_paterno="User",
        )
        self.categoria = CategoriaEquipo.objects.create(nombre_categoria="Laptop")
        self.equipo_asignado = Equipo.objects.create(
            codigo_inventario="INV-ASIG-001",
            categoria=self.categoria,
            estado_equipo=EstadoEquipo.ASIGNADO,
        )
        self.equipo_ajeno = Equipo.objects.create(
            codigo_inventario="INV-OTRO-002",
            categoria=self.categoria,
        )
        AsignacionEquipo.objects.create(
            equipo=self.equipo_asignado,
            personal=self.personal,
            estado_asignacion=EstadoAsignacion.ACTIVA,
        )

    def _payload(self, equipo=""):
        return {
            "requerimiento": "No enciende",
            "descripcion": "El equipo no responde al boton de encendido.",
            "tipo_ticket": "HELPDESK",
            "prioridad": "Media",
            "equipo": equipo,
        }

    def test_create_form_lists_only_assigned_equipment_and_otro(self):
        self.client.login(username="ticket_user", password=self.password)
        response = self.client.get(reverse("ticketit_create") + "?manual=1")
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        pks = set(form.fields["equipo"].queryset.values_list("pk", flat=True))
        self.assertEqual(pks, {self.equipo_asignado.pk})
        self.assertEqual(form.fields["equipo"].empty_label, "Otro equipo")
        self.assertContains(response, "Otro equipo")
        self.assertContains(response, "INV-ASIG-001")
        self.assertNotContains(response, "INV-OTRO-002")

    def test_create_ticket_with_assigned_equipment(self):
        self.client.login(username="ticket_user", password=self.password)
        response = self.client.post(
            reverse("ticketit_create"),
            self._payload(equipo=str(self.equipo_asignado.pk)),
        )
        self.assertEqual(response.status_code, 302)
        ticket = TicketIT.objects.get()
        self.assertEqual(ticket.equipo_id, self.equipo_asignado.pk)

    def test_create_ticket_with_otro_equipo(self):
        self.client.login(username="ticket_user", password=self.password)
        response = self.client.post(
            reverse("ticketit_create"),
            self._payload(equipo=""),
        )
        self.assertEqual(response.status_code, 302)
        ticket = TicketIT.objects.get()
        self.assertIsNone(ticket.equipo_id)

    def test_create_rejects_unassigned_equipment(self):
        self.client.login(username="ticket_user", password=self.password)
        response = self.client.post(
            reverse("ticketit_create"),
            self._payload(equipo=str(self.equipo_ajeno.pk)),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TicketIT.objects.exists())
        self.assertTrue(response.context["form"].errors.get("equipo"))

    def test_admin_create_form_lists_all_equipment(self):
        admin = User.objects.create_user(username="ticket_admin", password=self.password)
        set_user_role(admin, ROLE_ADMIN)
        self.client.login(username="ticket_admin", password=self.password)
        response = self.client.get(reverse("ticketit_create"))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        pks = set(form.fields["equipo"].queryset.values_list("pk", flat=True))
        self.assertEqual(pks, {self.equipo_asignado.pk, self.equipo_ajeno.pk})
        self.assertEqual(form.fields["equipo"].empty_label, "Otro equipo")
        self.assertContains(response, "INV-ASIG-001")
        self.assertContains(response, "INV-OTRO-002")
        self.assertContains(response, "Otro equipo")

    def test_admin_can_create_ticket_with_any_equipment(self):
        admin = User.objects.create_user(username="ticket_admin", password=self.password)
        set_user_role(admin, ROLE_ADMIN)
        self.client.login(username="ticket_admin", password=self.password)
        response = self.client.post(
            reverse("ticketit_create"),
            self._payload(equipo=str(self.equipo_ajeno.pk)),
        )
        self.assertEqual(response.status_code, 302)
        ticket = TicketIT.objects.get()
        self.assertEqual(ticket.equipo_id, self.equipo_ajeno.pk)

    def test_tecnico_create_form_lists_all_equipment(self):
        tecnico = User.objects.create_user(username="ticket_tech", password=self.password)
        set_user_role(tecnico, ROLE_TECNICO)
        self.client.login(username="ticket_tech", password=self.password)
        response = self.client.get(reverse("ticketit_create"))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        pks = set(form.fields["equipo"].queryset.values_list("pk", flat=True))
        self.assertEqual(pks, {self.equipo_asignado.pk, self.equipo_ajeno.pk})
        self.assertContains(response, "INV-OTRO-002")
        self.assertContains(response, "Otro equipo")

    def test_tecnico_can_create_ticket_with_any_equipment(self):
        tecnico = User.objects.create_user(username="ticket_tech", password=self.password)
        set_user_role(tecnico, ROLE_TECNICO)
        self.client.login(username="ticket_tech", password=self.password)
        response = self.client.post(
            reverse("ticketit_create"),
            self._payload(equipo=str(self.equipo_ajeno.pk)),
        )
        self.assertEqual(response.status_code, 302)
        ticket = TicketIT.objects.get()
        self.assertEqual(ticket.equipo_id, self.equipo_ajeno.pk)


class SolicitudEquipoSeguimientoTests(TestCase):
    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(username="sol_user", password=self.password)
        set_user_role(self.user, ROLE_USUARIO)
        self.tech = User.objects.create_user(username="sol_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.admin = User.objects.create_user(username="sol_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)
        self.solicitud = SolicitudEquipo.objects.create(
            solicitante=self.user,
            titulo="Laptop de reemplazo",
            justificacion="El equipo actual ya no enciende.",
        )

    def test_solicitante_sees_detail_but_cannot_decide(self):
        self.client.login(username="sol_user", password=self.password)
        response = self.client.get(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Decision")
        self.assertNotContains(response, "Guardar decision")
        self.assertNotContains(response, "Cerrar solicitud")
        self.assertNotContains(response, "Revision IT")

        response = self.client.post(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk]),
            {
                "form_type": "decision",
                "estado": EstadoSolicitudEquipo.APROBADA,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.PENDIENTE)

    def test_tecnico_can_mark_en_revision(self):
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.PENDIENTE)
        self.client.login(username="sol_tech", password=self.password)
        response = self.client.get(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk])
        )
        self.assertContains(response, "Guardar decision")
        self.assertContains(response, "Cerrar solicitud")
        self.assertContains(response, "Decision")
        self.assertNotContains(response, "Revision IT")
        self.assertNotContains(response, "Agregar seguimiento")

        response = self.client.post(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk]),
            {
                "form_type": "decision",
                "estado": EstadoSolicitudEquipo.EN_REVISION,
                "notas_it": "Buscando equipo compatible",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.EN_REVISION)
        self.assertEqual(self.solicitud.notas_it, "Buscando equipo compatible")

    def test_admin_can_close_solicitud(self):
        self.client.login(username="sol_admin", password=self.password)
        response = self.client.post(
            reverse("solicitud_equipo_revisar", args=[self.solicitud.pk]),
            {"estado": EstadoSolicitudEquipo.COMPLETADA},
        )
        self.assertEqual(response.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.COMPLETADA)

    def test_tecnico_can_close_from_detail(self):
        self.client.login(username="sol_tech", password=self.password)
        response = self.client.post(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk]),
            {
                "form_type": "decision",
                "estado": EstadoSolicitudEquipo.COMPLETADA,
                "notas_it": "Equipo entregado",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.COMPLETADA)
        self.assertEqual(self.solicitud.notas_it, "Equipo entregado")


class BitacoraAnswerFlowTests(TestCase):
    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.tech = User.objects.create_user(username="bit_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.admin = User.objects.create_user(username="bit_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)

    def test_create_bitacora_opens_detail_and_accepts_answer(self):
        self.client.login(username="bit_tech", password=self.password)
        create = self.client.post(
            reverse("bitacora_create"),
            {
                "situacion": "Falla de impresora en recepcion",
                "descripcion_situacion": "No imprime desde esta manana.",
            },
        )
        self.assertEqual(create.status_code, 302)
        bitacora = Bitacora.objects.get()
        self.assertTrue(bitacora.folio_bitacora.startswith("BIT-"))
        self.assertEqual(create.url, reverse("bitacora_detail", args=[bitacora.pk]))

        detail = self.client.get(reverse("bitacora_detail", args=[bitacora.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Agregar respuesta")
        self.assertContains(detail, bitacora.situacion)

        add = self.client.post(
            reverse("bitacora_detail", args=[bitacora.pk]),
            {
                "form_type": "answer",
                "solucion": "Se reinicio el spooler",
                "descripcion_solucion": "Quedo operativa.",
                "usuario": str(self.tech.pk),
            },
        )
        self.assertEqual(add.status_code, 302)
        self.assertTrue(Answer.objects.filter(bitacora=bitacora, solucion="Se reinicio el spooler").exists())

        answers = self.client.get(reverse("answer_list"))
        self.assertEqual(answers.status_code, 200)
        self.assertContains(answers, bitacora.folio_bitacora)
        self.assertContains(answers, "Se reinicio el spooler")

    def test_cannot_delete_bitacora_with_answers(self):
        bitacora = Bitacora.objects.create(
            situacion="Incidente de red",
            descripcion_situacion="Sin acceso a SAP.",
        )
        Answer.objects.create(
            bitacora=bitacora,
            solucion="Se restauro el enlace",
            descripcion_solucion="OK",
            usuario=self.tech,
        )
        self.client.login(username="bit_admin", password=self.password)
        response = self.client.post(reverse("bitacora_delete", args=[bitacora.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Bitacora.objects.filter(pk=bitacora.pk).exists())


class TicketCierreLimpiaPendientesTests(TestCase):
    """Al concluir un check, limpia fechas de proximo seguimiento de checks abiertos previos."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.tech = User.objects.create_user(username="chk_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.ticket = TicketIT.objects.create(
            descripcion="Impresora sin red",
            requerimiento="Revisar cableado",
            solicitado_por=self.tech,
        )

    def test_concluir_limpia_fecha_proximo_de_checks_abiertos(self):
        proxima = date.today() + timedelta(days=2)
        abierto = SeguimientoTicket.objects.create(
            ticket=self.ticket,
            usuario=self.tech,
            avance_realizado="Se reviso puerto",
            fecha_proximo_seguimiento=proxima,
            ya_terminado=False,
        )
        cierre = SeguimientoTicket.objects.create(
            ticket=self.ticket,
            usuario=self.tech,
            solucion="Se reemplazo el switch",
            fecha_proximo_seguimiento=proxima,
            ya_terminado=True,
        )

        abierto.refresh_from_db()
        cierre.refresh_from_db()
        self.ticket.refresh_from_db()

        self.assertEqual(self.ticket.status, EstadoSupport.CERRADO)
        self.assertIsNone(abierto.fecha_proximo_seguimiento)
        self.assertFalse(abierto.ya_terminado)
        self.assertIsNone(cierre.fecha_proximo_seguimiento)
        self.assertTrue(cierre.ya_terminado)


class TicketComentarioTests(TestCase):
    PNG = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(username="cmt_user", password=self.password)
        set_user_role(self.user, ROLE_USUARIO)
        self.tech = User.objects.create_user(username="cmt_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.otro = User.objects.create_user(username="cmt_otro", password=self.password)
        set_user_role(self.otro, ROLE_USUARIO)
        self.ticket = TicketIT.objects.create(
            descripcion="Pantalla en negro",
            requerimiento="No enciende el monitor",
            solicitado_por=self.user,
        )

    def _create_url(self):
        return reverse("ticketit_comentario_create", args=[self.ticket.pk])

    def test_solicitante_can_comment_on_own_ticket(self):
        self.client.login(username="cmt_user", password=self.password)
        detail = self.client.get(reverse("ticketit_detail", args=[self.ticket.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Comentarios")
        self.assertContains(detail, "Publicar")

        response = self.client.post(self._create_url(), {"mensaje": "Adjunto foto de la etiqueta."})
        self.assertEqual(response.status_code, 302)
        comentario = ComentarioTicket.objects.get(ticket=self.ticket)
        self.assertEqual(comentario.mensaje, "Adjunto foto de la etiqueta.")
        self.assertEqual(comentario.autor_id, self.user.id)
        self.assertFalse(comentario.es_interno)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "Abierto")

    def test_stranger_cannot_comment(self):
        self.client.login(username="cmt_otro", password=self.password)
        response = self.client.post(self._create_url(), {"mensaje": "No deberia verse"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ComentarioTicket.objects.filter(ticket=self.ticket).exists())

    def test_empty_comment_is_rejected(self):
        self.client.login(username="cmt_user", password=self.password)
        response = self.client.post(self._create_url(), {"mensaje": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ComentarioTicket.objects.exists())
        self.assertContains(response, "Escribe un comentario o adjunta un archivo")

    def test_comment_with_image_attachment(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(username="cmt_user", password=self.password)
        uploaded = SimpleUploadedFile("etiqueta.PNG", self.PNG, content_type="image/png")
        response = self.client.post(
            self._create_url(),
            {"mensaje": "Foto de la etiqueta", "adjuntos": uploaded},
        )
        self.assertEqual(response.status_code, 302)
        comentario = ComentarioTicket.objects.get()
        adjunto = comentario.adjuntos.get()
        self.assertTrue(adjunto.es_imagen)
        self.assertEqual(adjunto.nombre_original, "etiqueta.PNG")
        self.assertTrue(adjunto.archivo.name.endswith(".png"))
        self.assertNotIn("etiqueta", adjunto.archivo.name.lower())

    def test_rejects_exe_as_attachment(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(username="cmt_user", password=self.password)
        fake = SimpleUploadedFile(
            "malware.pdf",
            b"MZ\x90\x00this-is-not-a-pdf",
            content_type="application/pdf",
        )
        response = self.client.post(self._create_url(), {"adjuntos": fake})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ComentarioTicket.objects.exists())

    def test_solicitante_cannot_comment_when_closed(self):
        SeguimientoTicket.objects.create(
            ticket=self.ticket,
            usuario=self.tech,
            solucion="Se cambio el cable",
            ya_terminado=True,
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "Cerrado")

        self.client.login(username="cmt_user", password=self.password)
        detail = self.client.get(reverse("ticketit_detail", args=[self.ticket.pk]))
        self.assertContains(detail, "El ticket esta cerrado")
        self.assertNotContains(detail, "Publicar")

        response = self.client.post(self._create_url(), {"mensaje": "Sigue fallando"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ComentarioTicket.objects.exists())

    def test_tecnico_can_comment_when_closed(self):
        SeguimientoTicket.objects.create(
            ticket=self.ticket,
            usuario=self.tech,
            solucion="Se cambio el cable",
            ya_terminado=True,
        )
        self.client.login(username="cmt_tech", password=self.password)
        response = self.client.post(self._create_url(), {"mensaje": "Nota interna de cierre"})
        self.assertEqual(response.status_code, 302)
        comentario = ComentarioTicket.objects.get()
        self.assertTrue(comentario.es_interno)

    def test_author_can_delete_own_comment(self):
        comentario = ComentarioTicket.objects.create(
            ticket=self.ticket,
            autor=self.user,
            mensaje="Borrar esto",
        )
        self.client.login(username="cmt_user", password=self.password)
        response = self.client.post(
            reverse("ticketit_comentario_delete", args=[self.ticket.pk, comentario.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ComentarioTicket.objects.filter(pk=comentario.pk).exists())

    def test_other_user_cannot_delete_comment(self):
        comentario = ComentarioTicket.objects.create(
            ticket=self.ticket,
            autor=self.user,
            mensaje="No borrar",
        )
        self.client.login(username="cmt_otro", password=self.password)
        response = self.client.post(
            reverse("ticketit_comentario_delete", args=[self.ticket.pk, comentario.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ComentarioTicket.objects.filter(pk=comentario.pk).exists())


class PropagarCustodiaPersonalTests(TestCase):
    def setUp(self):
        self.edificio = Edificio.objects.create(nombre_edificio="Torre A")
        self.zona = ZonaEdificio.objects.create(
            edificio=self.edificio,
            nombre_zona="Piso 1",
        )
        self.ubicacion_a = Ubicacion.objects.create(
            edificio=self.edificio,
            zona=self.zona,
            referencia="Escritorio 101",
        )
        self.ubicacion_b = Ubicacion.objects.create(
            edificio=self.edificio,
            zona=self.zona,
            referencia="Escritorio 202",
        )
        self.personal = Personal.objects.create(
            numero_empleado="EMP-UBI-01",
            nombre="Ana",
            apellido_paterno="Lopez",
            ubicacion=self.ubicacion_a,
        )
        self.categoria = CategoriaEquipo.objects.create(nombre_categoria="Laptop")
        self.equipo = Equipo.objects.create(
            codigo_inventario="INV-UBI-001",
            categoria=self.categoria,
            estado_equipo=EstadoEquipo.ASIGNADO,
            ubicacion=self.ubicacion_a,
        )
        AsignacionEquipo.objects.create(
            equipo=self.equipo,
            personal=self.personal,
            estado_asignacion=EstadoAsignacion.ACTIVA,
        )

    def test_propaga_ubicacion_a_equipos_asignados(self):
        from GestorApp.models import MovimientoEquipo, TipoMovimiento
        from GestorApp.views.helpers import _propagar_custodia_personal_a_equipos

        self.personal.ubicacion = self.ubicacion_b
        self.personal.save(update_fields=["ubicacion"])

        actualizados = _propagar_custodia_personal_a_equipos(self.personal)
        self.equipo.refresh_from_db()

        self.assertEqual(actualizados, 1)
        self.assertEqual(self.equipo.ubicacion_id, self.ubicacion_b.pk)
        movimiento = MovimientoEquipo.objects.get(equipo=self.equipo)
        self.assertEqual(movimiento.tipo_movimiento, TipoMovimiento.CAMBIO_UBICACION)

    def test_no_propaga_sin_asignacion_activa(self):
        from GestorApp.views.helpers import _propagar_custodia_personal_a_equipos

        AsignacionEquipo.objects.filter(equipo=self.equipo).update(
            estado_asignacion=EstadoAsignacion.DEVUELTA
        )
        self.personal.ubicacion = self.ubicacion_b
        self.personal.save(update_fields=["ubicacion"])

        actualizados = _propagar_custodia_personal_a_equipos(self.personal)
        self.equipo.refresh_from_db()

        self.assertEqual(actualizados, 0)
        self.assertEqual(self.equipo.ubicacion_id, self.ubicacion_a.pk)


class InventarioImportTests(TestCase):
    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.admin = User.objects.create_user(username="import_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)

        self.edificio = Edificio.objects.create(nombre_edificio="Torre B")
        self.zona = ZonaEdificio.objects.create(edificio=self.edificio, nombre_zona="Piso 2")
        self.ubicacion = Ubicacion.objects.create(
            edificio=self.edificio,
            zona=self.zona,
            referencia="Almacen IT",
            es_stock_default=True,
        )
        self.categoria_equipo = CategoriaEquipo.objects.create(
            nombre_categoria="Laptop",
            tipo="Equipo",
        )
        self.categoria_periferico = CategoriaEquipo.objects.create(
            nombre_categoria="Monitor",
            tipo="Periferico",
        )
        self.personal = Personal.objects.create(
            numero_empleado="EMP-IMP-01",
            nombre="Luis",
            apellido_paterno="Ramos",
            ubicacion=self.ubicacion,
        )

    def _build_workbook_bytes(self):
        from io import BytesIO

        from openpyxl import Workbook

        from GestorApp.inventory_import import EQUIPOS_HEADERS, PERIFERICOS_HEADERS

        wb = Workbook()
        ws_eq = wb.active
        ws_eq.title = "Equipos"
        ws_eq.append(EQUIPOS_HEADERS)
        ws_eq.append(
            [
                "INV-IMP-001",
                "Laptop",
                "Dell",
                "Latitude",
                "SER-IMP-001",
                "Asignado",
                str(self.ubicacion),
                "EMP-IMP-01",
                "",
                "Import test",
                "Legado",
            ]
        )
        ws_per = wb.create_sheet("Perifericos")
        ws_per.append(PERIFERICOS_HEADERS)
        ws_per.append(
            [
                "PER-IMP-001",
                "Monitor",
                "LG",
                "24MK",
                "SER-PER-001",
                "En Stock",
                str(self.ubicacion),
                "Monitor importado",
            ]
        )
        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def test_parse_and_execute_import(self):
        from io import BytesIO

        from GestorApp.inventory_import import execute_import, parse_import_workbook

        rows, errors = parse_import_workbook(BytesIO(self._build_workbook_bytes()))
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.status in {"ok", "warning"} for r in rows))

        result = execute_import(rows)
        self.assertEqual(result["equipos_creados"], 1)
        self.assertEqual(result["perifericos_creados"], 1)
        self.assertEqual(result["asignaciones_creadas"], 1)

        equipo = Equipo.objects.get(codigo_inventario="INV-IMP-001")
        periferico = Equipo.objects.get(codigo_inventario="PER-IMP-001")
        self.assertEqual(equipo.estado_equipo, EstadoEquipo.ASIGNADO)
        self.assertIsNone(periferico.equipo_padre_id)
        self.assertTrue(
            AsignacionEquipo.objects.filter(
                equipo=equipo,
                personal=self.personal,
                estado_asignacion=EstadoAsignacion.ACTIVA,
            ).exists()
        )

    def test_import_view_requires_login(self):
        response = self.client.get(reverse("inventario_importar"))
        self.assertEqual(response.status_code, 302)

    def test_import_wizard_preview(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(username="import_admin", password=self.password)
        upload = SimpleUploadedFile(
            "inventario.xlsx",
            self._build_workbook_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = self.client.post(reverse("inventario_importar"), {"archivo": upload})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("inventario_importar_preview"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["importables"], 2)


class SlaGuiaAdminTests(TestCase):
    """Pantalla Admin de documentacion del SLA: solo lectura y solo Administrador."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.admin = User.objects.create_user(username="sla_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)
        self.tech = User.objects.create_user(username="sla_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)

    def test_admin_ve_guia_en_texto(self):
        self.client.login(username="sla_admin", password=self.password)
        response = self.client.get(reverse("sla_guia"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Service Level Agreement")
        self.assertContains(response, "Urgente")
        self.assertContains(response, "4 h")
        self.assertContains(response, "168")
        self.assertContains(response, "Por vencer")
        self.assertContains(response, "Esta pantalla solo documenta")
        self.assertNotContains(response, "SLA_HORAS_POR_PRIORIDAD")

    def test_tecnico_no_entra(self):
        self.client.login(username="sla_tech", password=self.password)
        response = self.client.get(reverse("sla_guia"))
        self.assertNotEqual(response.status_code, 200)


class TicketSelectorProblemaTests(TestCase):
    """Pantalla previa '¿Qué problema se te presenta?' para usuarios normales."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.usuario = User.objects.create_user(username="user_sel", password=self.password)
        set_user_role(self.usuario, ROLE_USUARIO)
        self.tecnico = User.objects.create_user(username="tech_sel", password=self.password)
        set_user_role(self.tecnico, ROLE_TECNICO)
        self.admin = User.objects.create_user(username="admin_sel", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)

    def test_usuario_ve_pantalla_previa_con_tarjetas(self):
        self.client.login(username="user_sel", password=self.password)
        response = self.client.get(reverse("ticketit_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ticketit/selector_problema.html")
        self.assertContains(response, "¿Qué problema se te presenta?")
        self.assertContains(response, "Contraseñas y accesos")
        self.assertContains(response, "Impresora o escáner")
        self.assertContains(response, "Sistemas de planta (SAP / BPCS)")
        self.assertContains(response, "Formulario detallado")

    def test_tecnico_y_admin_van_directo_al_formulario(self):
        # Tecnico va directo al formulario
        self.client.login(username="tech_sel", password=self.password)
        res_tech = self.client.get(reverse("ticketit_create"))
        self.assertEqual(res_tech.status_code, 200)
        self.assertTemplateUsed(res_tech, "ticketit/form.html")
        self.assertIn("form", res_tech.context)
        self.assertNotContains(res_tech, "¿Qué problema se te presenta?")

        # Admin va directo al formulario
        self.client.login(username="admin_sel", password=self.password)
        res_admin = self.client.get(reverse("ticketit_create"))
        self.assertEqual(res_admin.status_code, 200)
        self.assertTemplateUsed(res_admin, "ticketit/form.html")
        self.assertIn("form", res_admin.context)
        self.assertNotContains(res_admin, "¿Qué problema se te presenta?")

    def test_usuario_elige_problema_prellena_datos_y_permite_cambiar_prioridad(self):
        self.client.login(username="user_sel", password=self.password)
        # 1. El usuario selecciona la tarjeta 'impresora'
        response = self.client.get(reverse("ticketit_create") + "?problema=impresora")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ticketit/form.html")
        self.assertContains(response, "Impresora o escáner")
        self.assertContains(response, "Prioridad sugerida:")

        form = response.context["form"]
        self.assertEqual(form.initial.get("tipo_ticket"), "HELPDESK")
        self.assertEqual(form.initial.get("sub_tipo_ticket"), "Impresora")
        self.assertEqual(form.initial.get("prioridad"), "Baja")

        # 2. El usuario decide cambiar la prioridad de 'Baja' a 'Alta' y guarda
        post_data = {
            "requerimiento": "Impresora atascada en facturacion",
            "descripcion": "No salen las facturas para embarques urgentes.",
            "tipo_ticket": "HELPDESK",
            "sub_tipo_ticket": "Impresora",
            "prioridad": "Alta",  # Cambio manual de prioridad permitido
            "problema_id": "impresora",
        }
        res_post = self.client.post(reverse("ticketit_create"), post_data)
        self.assertEqual(res_post.status_code, 302)

        ticket = TicketIT.objects.filter(requerimiento="Impresora atascada en facturacion").first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.tipo_ticket, "HELPDESK")
        self.assertEqual(ticket.sub_tipo_ticket, "Impresora")
        self.assertEqual(ticket.prioridad, "Alta")  # Se respeto la prioridad cambiada por el usuario

    def test_usuario_modo_manual(self):
        self.client.login(username="user_sel", password=self.password)
        response = self.client.get(reverse("ticketit_create") + "?manual=1")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ticketit/form.html")
        self.assertIn("form", response.context)
        self.assertIsNone(response.context["problema_info"])


class MisEquiposViewTests(TestCase):
    """Pruebas para la vista 'Mis equipos'."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(username="me_user", password=self.password)
        set_user_role(self.user, ROLE_USUARIO)
        self.personal = Personal.objects.create(
            numero_empleado="EMP-ME01",
            user=self.user,
            nombre="Mis",
            apellido_paterno="Equipos",
        )

    def test_sin_equipos_asigna_boton_solicitar_equipo(self):
        self.client.login(username="me_user", password=self.password)
        response = self.client.get(reverse("mis_equipos"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("solicitud_equipo_create"))
        self.assertContains(response, "Solicitar equipo")
        # El empty state no debe enlazar a ticketit_create
        self.assertNotContains(response, "abre un ticket si necesitas soporte")


class QueryOptimizationTests(TestCase):
    """Verificación de optimizaciones N+1 y reducción de consultas a BD."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.admin = User.objects.create_user(username="perf_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)

    def test_equipo_puede_eliminar_fisico_annotated_in_queryset(self):
        cat = CategoriaEquipo.objects.create(nombre_categoria="Laptop Perf")
        eq1 = Equipo.objects.create(codigo_inventario="EQ-PERF-01", categoria=cat)

        from GestorApp.views.equipo import _equipo_queryset

        eq_from_qs = _equipo_queryset().get(pk=eq1.pk)
        self.assertTrue(hasattr(eq_from_qs, "puede_eliminar_fisico_annotated"))
        self.assertTrue(eq_from_qs.puede_eliminar_fisico)

        # Si agregamos un ticket al equipo, la anotación debe marcar False
        TicketIT.objects.create(
            equipo=eq1,
            solicitado_por=self.admin,
            requerimiento="Falla test",
            descripcion="Desc test",
        )
        eq_with_ticket = _equipo_queryset().get(pk=eq1.pk)
        self.assertFalse(eq_with_ticket.puede_eliminar_fisico_annotated)
        self.assertFalse(eq_with_ticket.puede_eliminar_fisico)

    def test_ticket_tiene_seguimientos_uses_annotated_count(self):
        ticket = TicketIT.objects.create(
            solicitado_por=self.admin,
            requerimiento="Ticket N1",
            descripcion="Prueba",
            status=EstadoSupport.ABIERTO,
        )
        # Sin anotación hace la consulta normal
        self.assertFalse(ticket.tiene_seguimientos)
        self.assertTrue(ticket.puede_marcar_en_revision)

        # Con anotación seguimientos_count=0
        ticket.seguimientos_count = 0
        self.assertFalse(ticket.tiene_seguimientos)
        self.assertTrue(ticket.puede_marcar_en_revision)

        # Con anotación seguimientos_count > 0
        ticket.seguimientos_count = 3
        self.assertTrue(ticket.tiene_seguimientos)
        self.assertFalse(ticket.puede_marcar_en_revision)

    def test_roles_group_names_uses_prefetched_groups(self):
        from GestorApp.roles import _group_names, get_user_role

        user = User.objects.create_user(username="perf_user", password=self.password)
        set_user_role(user, ROLE_TECNICO)

        # Recargar con prefetch
        user_prefetched = User.objects.prefetch_related("groups").get(pk=user.pk)
        # Al acceder a _group_names con prefetch, no debe realizar consultas SQL adicionales
        with self.assertNumQueries(0):
            names = _group_names(user_prefetched)
            self.assertIn(ROLE_TECNICO, names)
            role = get_user_role(user_prefetched)
            self.assertEqual(role, ROLE_TECNICO)

    def test_alert_contexts_support_include_lists_false(self):
        from GestorApp.views.consumibles import _consumibles_alerta_context
        from GestorApp.views.equipo import _equipos_alerta_context
        from GestorApp.views.mantenimiento import _mantenimientos_alerta_context
        from GestorApp.views.tickets import _seguimientos_alerta_context

        cons = _consumibles_alerta_context(include_lists=False)
        self.assertIn("consumibles_bajo_count", cons)
        self.assertEqual(cons["consumibles_bajo"], [])

        eq = _equipos_alerta_context(include_lists=False)
        self.assertIn("equipos_sin_ubicacion_count", eq)
        self.assertEqual(eq["equipos_sin_ubicacion"], [])

        mant = _mantenimientos_alerta_context(include_lists=False)
        self.assertIn("mantenimientos_vencidos_count", mant)
        self.assertEqual(mant["mantenimientos_vencidos"], [])

        seg = _seguimientos_alerta_context(include_lists=False)
        self.assertIn("seguimientos_vencidos_count", seg)
        self.assertEqual(seg["seguimientos_vencidos"], [])

    def test_parse_date_accepts_whitespace_and_iso(self):
        from datetime import date

        from GestorApp.views.helpers import _parse_date

        self.assertEqual(_parse_date("2026-09-09"), date(2026, 9, 9))
        self.assertEqual(_parse_date(" 2026-09-09 "), date(2026, 9, 9))
        self.assertIsNone(_parse_date(""))
        self.assertIsNone(_parse_date(None))
        self.assertIsNone(_parse_date("09/09/2026"))

    def test_get_user_personal_unified_helper(self):
        from GestorApp.forms.common import _get_user_personal

        user = User.objects.create_user(username="pers_helper", password=self.password)
        self.assertIsNone(_get_user_personal(user))
        personal = Personal.objects.create(
            numero_empleado="EMP-HELPER",
            user=user,
            nombre="Helper",
            apellido_paterno="Test",
        )
        self.assertEqual(_get_user_personal(user), personal)
        self.assertIsNone(_get_user_personal(None))


class SecurityAndUIFixesTests(TestCase):
    """Pruebas para los puntos 5 al 8 (seguridad, rutas y UI)."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.admin = User.objects.create_user(username="sec_admin", password=self.password)
        set_user_role(self.admin, ROLE_ADMIN)
        self.tech = User.objects.create_user(username="sec_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.user = User.objects.create_user(username="sec_user", password=self.password)
        set_user_role(self.user, ROLE_USUARIO)

        self.personal_user = Personal.objects.create(
            numero_empleado="EMP-SEC01",
            user=self.user,
            nombre="Sec",
            apellido_paterno="User",
        )
        self.ticket = TicketIT.objects.create(
            solicitado_por=self.user,
            requerimiento="Ticket prueba seguridad",
            descripcion="Detalle",
            status=EstadoSupport.ABIERTO,
        )

    def test_punto_5_ticketit_delete_requiere_admin(self):
        # Usuario normal no puede acceder a delete
        self.client.login(username="sec_user", password=self.password)
        res_user = self.client.get(reverse("ticketit_delete", args=[self.ticket.pk]))
        self.assertNotEqual(res_user.status_code, 200)

        # Técnico tampoco puede acceder a delete
        self.client.login(username="sec_tech", password=self.password)
        res_tech = self.client.get(reverse("ticketit_delete", args=[self.ticket.pk]))
        self.assertNotEqual(res_tech.status_code, 200)

        # Admin sí puede acceder
        self.client.login(username="sec_admin", password=self.password)
        res_admin = self.client.get(reverse("ticketit_delete", args=[self.ticket.pk]))
        self.assertEqual(res_admin.status_code, 200)
        self.assertTemplateUsed(res_admin, "ticketit/confirm_delete.html")

    def test_punto_6_gobierno_urls_protect_without_double_decoration(self):
        # Admin entra a permisos_matriz y sla_guia
        self.client.login(username="sec_admin", password=self.password)
        self.assertEqual(self.client.get(reverse("permisos_matriz")).status_code, 200)
        self.assertEqual(self.client.get(reverse("sla_guia")).status_code, 200)

        # Usuario normal no entra
        self.client.login(username="sec_user", password=self.password)
        self.assertNotEqual(self.client.get(reverse("permisos_matriz")).status_code, 200)
        self.assertNotEqual(self.client.get(reverse("sla_guia")).status_code, 200)

    def test_punto_7_solicitud_detail_form_action_uses_revisar_endpoint(self):
        cat = CategoriaEquipo.objects.create(nombre_categoria="Laptop Sec")
        sol = SolicitudEquipo.objects.create(
            solicitante=self.user,
            personal=self.personal_user,
            categoria=cat,
            titulo="Laptop adicional",
            justificacion="Requerida para soporte",
            estado=EstadoSolicitudEquipo.PENDIENTE,
        )
        self.client.login(username="sec_admin", password=self.password)
        res = self.client.get(reverse("solicitud_equipo_detail", args=[sol.pk]))
        self.assertEqual(res.status_code, 200)
        revisar_url = reverse("solicitud_equipo_revisar", args=[sol.pk])
        self.assertContains(res, f'action="{revisar_url}"')

    def test_punto_8_ticketit_detail_breadcrumb_resolves_ticket_folio(self):
        from GestorApp.breadcrumbs import _resolve_detail_label

        label = _resolve_detail_label("ticketit_detail", {"pk": self.ticket.pk})
        self.assertEqual(label, self.ticket.folio_ticket)
        self.assertNotEqual(label, "Detalle")

    def test_punto_9_consumibles_and_perifericos_breadcrumbs_resolve_labels(self):
        from GestorApp.breadcrumbs import _resolve_detail_label

        cat = CategoriaEquipo.objects.create(
            nombre_categoria="Toner",
            tipo=TipoCategoriaInventario.CONSUMIBLE,
        )
        prod = ProductoConsumible.objects.create(
            sku="CON-TEST-01",
            nombre="Toner Negro HP",
            categoria=cat,
        )
        self.assertEqual(
            _resolve_detail_label("producto_consumible_detail", {"pk": prod.pk}),
            "Toner Negro HP",
        )
        self.assertEqual(
            _resolve_detail_label("producto_consumible_update", {"pk": prod.pk}),
            "Toner Negro HP",
        )

        cat_eq = CategoriaEquipo.objects.create(
            nombre_categoria="Monitor",
            tipo=TipoCategoriaInventario.PERIFERICO,
        )
        eq = Equipo.objects.create(codigo_inventario="PER-TEST-01", categoria=cat_eq)
        self.assertEqual(
            _resolve_detail_label("equipo_vincular_periferico", {"pk": eq.pk}),
            "PER-TEST-01",
        )
        self.assertEqual(
            _resolve_detail_label("periferico_desvincular", {"pk": eq.pk}),
            "PER-TEST-01",
        )


class UserFailureHardeningTests(TestCase):
    """Regresiones de fallos provocables por un usuario autenticado."""

    def setUp(self):
        ensure_role_groups()
        self.password = "StrongPass123!"
        self.usuario = User.objects.create_user(username="fail_user", password=self.password)
        set_user_role(self.usuario, ROLE_USUARIO)
        self.tech = User.objects.create_user(username="fail_tech", password=self.password)
        set_user_role(self.tech, ROLE_TECNICO)
        self.personal_activo = Personal.objects.create(
            user=self.usuario,
            numero_empleado="FAIL-1",
            nombre="Activo",
            apellido_paterno="Uno",
            activo=True,
        )
        self.personal_inactivo = Personal.objects.create(
            numero_empleado="FAIL-2",
            nombre="Inactivo",
            apellido_paterno="Dos",
            activo=False,
        )
        self.categoria = CategoriaEquipo.objects.create(nombre_categoria="Laptop Fail")

    def test_fecha_support_client_no_falsea_sla(self):
        self.client.login(username="fail_user", password=self.password)
        pasado = (timezone.now() - timedelta(days=400)).isoformat()
        before = timezone.now()
        response = self.client.post(
            reverse("ticketit_create") + "?manual=1",
            {
                "requerimiento": "Pantalla negra",
                "descripcion": "No enciende desde ayer.",
                "tipo_ticket": "HELPDESK",
                "prioridad": "Media",
                "fecha_support_client": pasado,
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = TicketIT.objects.get(requerimiento="Pantalla negra")
        self.assertGreaterEqual(ticket.fecha_support, before - timedelta(seconds=5))

    def test_tipo_fijo_ignora_ajuste_forjado(self):
        from GestorApp.forms.consumibles import MovimientoStockForm

        cat = CategoriaEquipo.objects.create(
            nombre_categoria="Toner Fail",
            tipo=TipoCategoriaInventario.CONSUMIBLE,
        )
        producto = ProductoConsumible.objects.create(
            sku="FAIL-SKU-1",
            nombre="Toner",
            categoria=cat,
            stock_actual=10,
        )
        form = MovimientoStockForm(
            {
                "tipo_movimiento": TipoMovimientoStock.AJUSTE,
                "cantidad": 1,
                "motivo": "intento de ajuste",
            },
            producto=producto,
            tipo_fijo=TipoMovimientoStock.SALIDA,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["tipo_movimiento"], TipoMovimientoStock.SALIDA)

    def test_usuario_no_termina_ni_borra_oc_terminada(self):
        orden = OrdenCompra.objects.create(
            elaborado_por=self.usuario,
            origen=OrigenOrdenCompra.CREADO,
            estado=EstadoOrdenCompra.TERMINADO,
        )
        self.client.login(username="fail_user", password=self.password)
        terminar = self.client.post(reverse("ordencompra_terminar", args=[orden.pk]))
        self.assertEqual(terminar.status_code, 302)
        borrar = self.client.post(reverse("ordencompra_delete", args=[orden.pk]))
        self.assertEqual(borrar.status_code, 302)
        self.assertTrue(OrdenCompra.objects.filter(pk=orden.pk).exists())
        orden.refresh_from_db()
        self.assertEqual(orden.estado, EstadoOrdenCompra.TERMINADO)

    def test_solicitud_folio_unico_sin_vacio(self):
        s1 = SolicitudEquipo.objects.create(
            solicitante=self.usuario,
            titulo="Laptop nueva",
            justificacion="Necesito equipo",
        )
        s2 = SolicitudEquipo.objects.create(
            solicitante=self.usuario,
            titulo="Monitor",
            justificacion="Pantalla rota",
        )
        self.assertTrue(s1.folio.startswith("SOL-"))
        self.assertTrue(s2.folio.startswith("SOL-"))
        self.assertNotEqual(s1.folio, "")
        self.assertNotEqual(s1.folio, s2.folio)

    def test_una_sola_asignacion_activa_por_equipo(self):
        from django.db import transaction

        equipo = Equipo.objects.create(
            codigo_inventario="FAIL-EQ-1",
            categoria=self.categoria,
            estado_equipo=EstadoEquipo.DISPONIBLE,
        )
        AsignacionEquipo.objects.create(
            equipo=equipo,
            personal=self.personal_activo,
            estado_asignacion=EstadoAsignacion.ACTIVA,
        )
        extra = Personal.objects.create(
            numero_empleado="FAIL-3",
            nombre="Otro",
            apellido_paterno="Tres",
            activo=True,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AsignacionEquipo.objects.create(
                    equipo=equipo,
                    personal=extra,
                    estado_asignacion=EstadoAsignacion.ACTIVA,
                )

    def test_asignar_form_omite_personal_inactivo(self):
        from GestorApp.forms.equipo import EquipoAsignarForm

        form = EquipoAsignarForm()
        pks = set(form.fields["personal"].queryset.values_list("pk", flat=True))
        self.assertIn(self.personal_activo.pk, pks)
        self.assertNotIn(self.personal_inactivo.pk, pks)

    def test_is_staff_sin_grupo_no_es_administrador(self):
        from GestorApp.roles import get_user_role, is_administrador

        staff = User.objects.create_user(
            username="fail_staff",
            password=self.password,
            is_staff=True,
        )
        self.assertEqual(get_user_role(staff), ROLE_USUARIO)
        self.assertFalse(is_administrador(staff))

    def test_usuario_ve_detalle_de_equipo_asignado(self):
        asignado = Equipo.objects.create(
            codigo_inventario="FAIL-EQ-VIEW",
            categoria=self.categoria,
            estado_equipo=EstadoEquipo.ASIGNADO,
        )
        AsignacionEquipo.objects.create(
            equipo=asignado,
            personal=self.personal_activo,
            estado_asignacion=EstadoAsignacion.ACTIVA,
        )
        ajeno = Equipo.objects.create(
            codigo_inventario="FAIL-EQ-HIDE",
            categoria=self.categoria,
            estado_equipo=EstadoEquipo.DISPONIBLE,
        )
        self.client.login(username="fail_user", password=self.password)
        ok = self.client.get(reverse("equipo_detail", args=[asignado.pk]))
        self.assertEqual(ok.status_code, 200)
        denied = self.client.get(reverse("equipo_detail", args=[ajeno.pk]))
        self.assertEqual(denied.status_code, 302)

    def test_cierre_desde_programado_inicia_y_completa(self):
        equipo = Equipo.objects.create(
            codigo_inventario="FAIL-EQ-MANT",
            categoria=self.categoria,
            estado_equipo=EstadoEquipo.DISPONIBLE,
        )
        man = Mantenimiento.objects.create(
            equipo=equipo,
            tipo_mantenimiento="Correctivo",
            fecha_programada=date.today(),
            estado_mantenimiento=EstadoMantenimiento.PROGRAMADO,
        )
        self.client.login(username="fail_tech", password=self.password)
        fin = timezone.now().strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(
            reverse("agendamantenimiento_create") + f"?mantenimiento={man.pk}",
            {
                "fecha_fin": fin,
                "acciones_realizadas": "Se cambio el disco y se probo.",
            },
        )
        self.assertEqual(response.status_code, 302)
        man.refresh_from_db()
        equipo.refresh_from_db()
        self.assertEqual(man.estado_mantenimiento, EstadoMantenimiento.COMPLETADO)
        self.assertTrue(man.tiene_cierre)
        self.assertEqual(equipo.estado_equipo, EstadoEquipo.DISPONIBLE)
        self.assertTrue(
            equipo.movimientos.filter(tipo_movimiento=TipoMovimiento.MANTENIMIENTO).exists()
        )

    def test_cobertura_activa_no_permite_solape(self):
        tech2 = User.objects.create_user(username="fail_tech2", password=self.password)
        set_user_role(tech2, ROLE_TECNICO)
        primera = CoberturaTickets(
            ausente=self.tech,
            suplente=tech2,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=3),
            activa=True,
            creado_por=self.tech,
        )
        primera.full_clean()
        primera.save()
        solape = CoberturaTickets(
            ausente=self.tech,
            suplente=tech2,
            fecha_inicio=date.today() + timedelta(days=1),
            fecha_fin=date.today() + timedelta(days=5),
            activa=True,
            creado_por=self.tech,
        )
        with self.assertRaises(ValidationError):
            solape.full_clean()

    def test_tecnico_no_edita_cobertura_ajena(self):
        tech2 = User.objects.create_user(username="fail_tech2b", password=self.password)
        set_user_role(tech2, ROLE_TECNICO)
        ajeno = User.objects.create_user(username="fail_tech3", password=self.password)
        set_user_role(ajeno, ROLE_TECNICO)
        cobertura = CoberturaTickets.objects.create(
            ausente=self.tech,
            suplente=tech2,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=2),
            activa=True,
            creado_por=self.tech,
        )
        self.client.login(username="fail_tech3", password=self.password)
        response = self.client.get(reverse("cobertura_update", args=[cobertura.pk]))
        self.assertEqual(response.status_code, 404)








