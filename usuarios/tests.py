"""Pruebas unitarias para el modelo de Usuario y su Manager."""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

Usuario = get_user_model()


class UsuarioModelTests(TestCase):
    """Conjunto de pruebas para validar el comportamiento del modelo Usuario."""

    def test_crear_usuario_exitoso(self) -> None:
        """Verifica la creación correcta de un usuario estándar con email y contraseña."""
        email = "usuario@ejemplo.com"
        password = "PasswordSeguro123!"
        user = Usuario.objects.create_user(
            email=email,
            password=password,
            first_name="Juan",
            last_name="Pérez",
        )

        self.assertEqual(user.email, email.lower())
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.get_full_name(), "Juan Pérez")
        self.assertEqual(str(user), f"Juan Pérez ({email.lower()})")

    def test_crear_usuario_sin_email_lanza_error(self) -> None:
        """Verifica que intentar crear un usuario sin correo lance un ValueError."""
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(email="", password="Password123!")

    def test_crear_superuser_exitoso(self) -> None:
        """Verifica la creación correcta de un superusuario con permisos."""
        admin_email = "admin@ejemplo.com"
        admin_pass = "AdminPass123!"
        admin_user = Usuario.objects.create_superuser(
            email=admin_email,
            password=admin_pass,
        )

        self.assertEqual(admin_user.email, admin_email.lower())
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_crear_superuser_sin_staff_lanza_error(self) -> None:
        """Verifica que un superusuario con is_staff=False lance ValueError."""
        with self.assertRaises(ValueError):
            Usuario.objects.create_superuser(
                email="admin_invalido@ejemplo.com",
                password="Password123!",
                is_staff=False,
            )

    def test_crear_superuser_sin_superuser_lanza_error(self) -> None:
        """Verifica que un superusuario con is_superuser=False lance ValueError."""
        with self.assertRaises(ValueError):
            Usuario.objects.create_superuser(
                email="admin_invalido2@ejemplo.com",
                password="Password123!",
                is_superuser=False,
            )


class LoginRateLimitSecurityTests(TestCase):
    """Pruebas de seguridad contra ataques de fuerza bruta en el endpoint de autenticación."""

    def setUp(self) -> None:
        from django.core.cache import cache
        cache.clear()
        self.email = "seguro@familia.com"
        self.password = "PasswordSeguro123!"
        self.user = Usuario.objects.create_user(
            email=self.email,
            password=self.password,
        )

    def tearDown(self) -> None:
        from django.core.cache import cache
        cache.clear()

    def test_login_exitoso(self) -> None:
        """Verifica que las credenciales correctas permitan iniciar sesión normalmente."""
        from django.urls import reverse
        response = self.client.post(
            reverse("usuarios:login"),
            {"username": self.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("finanzas:dashboard"))

    def test_bloqueo_por_fuerza_bruta_tras_multiples_fallos(self) -> None:
        """Verifica que tras 5 intentos fallidos consecutivos se bloquee temporalmente el acceso."""
        from django.urls import reverse
        from usuarios.views import MAX_LOGIN_ATTEMPTS

        # Realizar 5 intentos fallidos
        for i in range(MAX_LOGIN_ATTEMPTS):
            res = self.client.post(
                reverse("usuarios:login"),
                {"username": self.email, "password": "PasswordIncorrecta!"},
            )
            self.assertEqual(res.status_code, 200)

        # El 6º intento (incluso con contraseña correcta) debe ser bloqueado por rate limit
        res_bloqueado = self.client.post(
            reverse("usuarios:login"),
            {"username": self.email, "password": self.password},
        )
        self.assertEqual(res_bloqueado.status_code, 200)
        self.assertContains(res_bloqueado, "Demasiados intentos fallidos")
        self.assertContains(res_bloqueado, "bloqueado temporalmente")

    def test_login_exitoso_limpia_intentos_fallidos(self) -> None:
        """Verifica que un login válido tras un fallo limpie el contador en caché."""
        from django.urls import reverse

        # 1 intento fallido
        self.client.post(
            reverse("usuarios:login"),
            {"username": self.email, "password": "PasswordIncorrecta!"},
        )

        # Login correcto
        res_ok = self.client.post(
            reverse("usuarios:login"),
            {"username": self.email, "password": self.password},
        )
        self.assertEqual(res_ok.status_code, 302)

