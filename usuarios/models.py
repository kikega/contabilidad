"""Modelos de datos para el módulo de usuarios y autenticación."""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from usuarios.managers import UsuarioManager


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Modelo personalizado de Usuario que utiliza el correo electrónico como identificador único."""

    email = models.EmailField(
        _("correo electrónico"),
        unique=True,
        max_length=255,
        error_messages={
            "unique": _("Ya existe un usuario registrado con este correo electrónico."),
        },
        db_index=True,
    )
    first_name = models.CharField(_("nombre"), max_length=150, blank=True)
    last_name = models.CharField(_("apellidos"), max_length=150, blank=True)
    
    is_staff = models.BooleanField(
        _("es staff"),
        default=False,
        help_text=_("Indica si el usuario puede iniciar sesión en el panel de administración."),
    )
    is_active = models.BooleanField(
        _("activo"),
        default=True,
        help_text=_("Indica si esta cuenta debe considerarse activa. Desmarque en lugar de borrar cuentas."),
    )
    date_joined = models.DateTimeField(_("fecha de registro"), default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        """Representación en cadena legible del usuario."""
        if self.first_name or self.last_name:
            return f"{self.get_full_name()} ({self.email})"
        return self.email

    def get_full_name(self) -> str:
        """Devuelve el nombre completo del usuario."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self) -> str:
        """Devuelve el nombre corto o primer nombre."""
        return self.first_name or self.email.split("@")[0]
