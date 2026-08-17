"""Vistas de autenticación y gestión de sesiones."""

from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.views import LogoutView
from django.urls import reverse_lazy

from usuarios.forms import LoginForm


class CustomLoginView(BaseLoginView):
    """Vista de inicio de sesión personalizada."""

    form_class = LoginForm
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        return reverse_lazy("finanzas:dashboard")


class CustomLogoutView(LogoutView):
    """Cierre de sesión seguro: únicamente acepta POST (evita logout CSRF)."""
