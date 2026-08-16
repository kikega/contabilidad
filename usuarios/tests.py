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
