"""Vistas de autenticación y gestión de sesiones."""

from typing import Any
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as BaseLoginView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View

from usuarios.forms import LoginForm


class CustomLoginView(BaseLoginView):
    """Vista de inicio de sesión personalizada."""

    form_class = LoginForm
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        return reverse_lazy("finanzas:dashboard")


class CustomLogoutView(View):
    """Vista para cierre seguro de sesión."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        logout(request)
        return redirect("usuarios:login")

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        logout(request)
        return redirect("usuarios:login")
