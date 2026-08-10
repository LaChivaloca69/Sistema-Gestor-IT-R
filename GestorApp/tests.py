from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from GestorApp.models import CategoriaEquipo, HistorialActividad, ModuloHistorial, TicketIT
from GestorApp.roles import ROLE_ADMIN, ROLE_TECNICO, ensure_role_groups, set_user_role
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
