"""Rutas de URLs para autenticación de usuarios."""

from django.urls import path
from usuarios.views import CustomLoginView, CustomLogoutView

app_name = "usuarios"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
]
