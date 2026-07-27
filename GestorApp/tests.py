from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
		self.assertTrue(
			get_user_model().objects.filter(username="testuser").exists()
		)
		self.assertTrue(response.wsgi_request.user.is_authenticated)

	def test_login_success_redirects_home(self):
		get_user_model().objects.create_user(
			username="testuser",
			password="StrongPass123!",
		)

		response = self.client.post(
			reverse("login"),
			{"username": "testuser", "password": "StrongPass123!"},
		)

		self.assertRedirects(response, reverse("home"))

	def test_login_failure_shows_error(self):
		get_user_model().objects.create_user(
			username="testuser",
			password="StrongPass123!",
		)

		response = self.client.post(
			reverse("login"),
			{"username": "testuser", "password": "BadPass123!"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.wsgi_request.user.is_authenticated)
		form = response.context.get("form")
		self.assertIsNotNone(form)
		self.assertTrue(form.errors)
