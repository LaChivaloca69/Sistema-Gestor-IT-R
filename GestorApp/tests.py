from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from GestorApp.models import (
    Answer,
    AsignacionEquipo,
    Bitacora,
    CategoriaEquipo,
    Equipo,
    EstadoAsignacion,
    EstadoEquipo,
    EstadoSolicitudEquipo,
    HistorialActividad,
    ModuloHistorial,
    Personal,
    SeguimientoSolicitudEquipo,
    SolicitudEquipo,
    TicketIT,
)
from GestorApp.roles import ROLE_ADMIN, ROLE_TECNICO, ROLE_USUARIO, ensure_role_groups, set_user_role
from GestorApp import historial as historial_mod


User = get_user_model()


class AuthFlowTests(TestCase):
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

        # Alta minima de equipo (legado, sin OC)
        create = self.client.post(
            reverse("equipo_create"),
            {
                "codigo_inventario": "SMOKE-EQ-001",
                "categoria": self.categoria.pk,
                "origen_alta": "Legado",
                "estado_equipo": "En Stock",
                "fecha_alta": "2026-01-15",
                "activo": "on",
            },
        )
        self.assertEqual(create.status_code, 302)


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
        response = self.client.get(reverse("ticketit_create"))
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

    def test_solicitante_sees_followups_but_cannot_add(self):
        SeguimientoSolicitudEquipo.objects.create(
            solicitud=self.solicitud,
            usuario=self.tech,
            avance_realizado="Se reviso inventario.",
        )
        self.client.login(username="sol_user", password=self.password)
        response = self.client.get(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se reviso inventario.")
        self.assertContains(response, "Revision IT")
        self.assertNotContains(response, "Guardar revision")
        self.assertNotContains(response, "Cerrar solicitud")

        response = self.client.post(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk]),
            {
                "form_type": "revision",
                "avance_realizado": "Intento del solicitante",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            SeguimientoSolicitudEquipo.objects.filter(
                avance_realizado="Intento del solicitante"
            ).exists()
        )

    def test_tecnico_can_add_seguimiento_and_moves_to_en_revision(self):
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.PENDIENTE)
        self.client.login(username="sol_tech", password=self.password)
        response = self.client.get(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk])
        )
        self.assertContains(response, "Guardar revision")
        self.assertContains(response, "Cerrar solicitud")
        self.assertContains(response, "Revision IT")
        self.assertNotContains(response, "Agregar seguimiento")
        self.assertNotContains(response, "Completar (asignado)")

        response = self.client.post(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk]),
            {
                "form_type": "revision",
                "avance_realizado": "Buscando equipo compatible",
                "usuario": str(self.tech.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.EN_REVISION)
        self.assertTrue(
            self.solicitud.seguimientos.filter(
                avance_realizado="Buscando equipo compatible"
            ).exists()
        )

    def test_admin_can_close_solicitud(self):
        self.client.login(username="sol_admin", password=self.password)
        response = self.client.post(
            reverse("solicitud_equipo_revisar", args=[self.solicitud.pk]),
            {"estado": EstadoSolicitudEquipo.COMPLETADA},
        )
        self.assertEqual(response.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.COMPLETADA)

    def test_tecnico_unified_revision_can_add_avance_and_close(self):
        self.client.login(username="sol_tech", password=self.password)
        response = self.client.post(
            reverse("solicitud_equipo_detail", args=[self.solicitud.pk]),
            {
                "form_type": "revision",
                "avance_realizado": "Equipo entregado",
                "usuario": str(self.tech.pk),
                "estado": EstadoSolicitudEquipo.COMPLETADA,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, EstadoSolicitudEquipo.COMPLETADA)
        self.assertTrue(
            self.solicitud.seguimientos.filter(
                avance_realizado="Equipo entregado"
            ).exists()
        )


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
