"""Vistas de autenticación y gestión de sesiones con protección de fuerza bruta."""

from typing import List, Optional
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.views import LogoutView
from django.core.cache import cache
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy

from usuarios.forms import LoginForm


MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIMEOUT = 300  # 5 minutos en segundos


def _get_client_ip(request: HttpRequest) -> str:
    """Obtiene la dirección IP real del cliente considerando proxies y balanceadores."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def _get_rate_limit_keys(request: HttpRequest, email: Optional[str] = None) -> List[str]:
    """Genera las claves de caché para el seguimiento de intentos fallidos por IP y por cuenta."""
    ip = _get_client_ip(request)
    keys = [f"login_fail_ip_{ip}"]
    if email:
        clean_email = email.lower().strip()
        keys.append(f"login_fail_email_{clean_email}")
    return keys


class CustomLoginView(BaseLoginView):
    """Vista de inicio de sesión con protección contra ataques de fuerza bruta y rate-limiting."""

    form_class = LoginForm
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        return reverse_lazy("finanzas:dashboard")

    def _is_rate_limited(self, request: HttpRequest, email: Optional[str] = None) -> bool:
        """Comprueba si la IP o la cuenta han superado el número máximo de intentos permitidos."""
        keys = _get_rate_limit_keys(request, email)
        for key in keys:
            attempts = cache.get(key, 0)
            if attempts >= MAX_LOGIN_ATTEMPTS:
                return True
        return False

    def post(self, request: HttpRequest, *args: str, **kwargs: str) -> HttpResponse:
        email = request.POST.get("username", "").strip()
        if self._is_rate_limited(request, email):
            form = self.get_form()
            form.add_error(
                None,
                "Demasiados intentos fallidos de inicio de sesión. "
                "Por motivos de seguridad, tu acceso ha sido bloqueado temporalmente durante 5 minutos.",
            )
            return self.form_invalid(form)

        return super().post(request, *args, **kwargs)

    def form_valid(self, form: Form) -> HttpResponse:
        """En caso de login exitoso, limpia los contadores de intentos fallidos."""
        email = form.cleaned_data.get("username", "")
        keys = _get_rate_limit_keys(self.request, email)
        for key in keys:
            cache.delete(key)
        return super().form_valid(form)

    def form_invalid(self, form: Form) -> HttpResponse:
        """En caso de login fallido, incrementa el contador de intentos y aplica TTL."""
        email = self.request.POST.get("username", "").strip()
        keys = _get_rate_limit_keys(self.request, email)
        for key in keys:
            current = cache.get(key, 0)
            cache.set(key, current + 1, timeout=LOGIN_LOCKOUT_TIMEOUT)

        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """Cierre de sesión seguro: únicamente acepta POST (evita logout CSRF)."""

