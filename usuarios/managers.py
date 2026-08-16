"""Gestores de modelos personalizados para la aplicación de usuarios."""

from typing import Any, Optional
from django.contrib.auth.models import BaseUserManager


class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario donde el email es el identificador único."""

    def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        **extra_fields: Any
    ) -> Any:
        """Crea y guarda un Usuario con el email y contraseña dados.

        Args:
            email: Dirección de correo electrónico única del usuario.
            password: Clave de acceso en texto plano que será hasheada.
            **extra_fields: Campos adicionales del modelo.

        Returns:
            Instancia del modelo Usuario creada.

        Raises:
            ValueError: Si no se proporciona un correo electrónico válido.
        """
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")

        email = self.normalize_email(email).lower()
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: Optional[str] = None,
        **extra_fields: Any
    ) -> Any:
        """Crea y guarda un Superusuario con permisos administrativos.

        Args:
            email: Dirección de correo electrónico única del usuario.
            password: Clave de acceso del superusuario.
            **extra_fields: Campos adicionales del modelo.

        Returns:
            Instancia del modelo Usuario configurada como superusuario.

        Raises:
            ValueError: Si is_staff o is_superuser no son True.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
