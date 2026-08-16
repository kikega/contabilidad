"""Formularios de autenticación y gestión de usuarios."""

from typing import Any
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from usuarios.models import Usuario


class LoginForm(AuthenticationForm):
    """Formulario de inicio de sesión con correo electrónico y contraseña."""

    username = forms.EmailField(
        label=_("Correo Electrónico"),
        widget=forms.EmailInput(
            attrs={
                "class": "w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-cyan-500 focus:outline-none transition-all placeholder:text-slate-400",
                "placeholder": "ejemplo@familia.com",
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label=_("Contraseña"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-cyan-500 focus:outline-none transition-all placeholder:text-slate-400",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )

    error_messages = {
        "invalid_login": _(
            "Por favor, introduce un correo electrónico y una contraseña correctos."
        ),
        "inactive": _("Esta cuenta está inactiva. Contacta con el administrador."),
    }
