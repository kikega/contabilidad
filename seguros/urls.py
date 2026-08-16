"""Enrutamiento de URLs para el módulo de Seguros."""

from django.urls import path
from seguros.views import (
    HistorialRenovacionCreateView,
    SeguroCreateView,
    SeguroDeleteView,
    SeguroDetailView,
    SeguroListView,
    SeguroRegistrarPagoView,
    SeguroUpdateView,
)

app_name = "seguros"

urlpatterns = [
    path("", SeguroListView.as_view(), name="seguro_list"),
    path("nuevo/", SeguroCreateView.as_view(), name="seguro_create"),
    path("<int:pk>/", SeguroDetailView.as_view(), name="seguro_detail"),
    path("<int:pk>/editar/", SeguroUpdateView.as_view(), name="seguro_update"),
    path("<int:pk>/eliminar/", SeguroDeleteView.as_view(), name="seguro_delete"),
    path("<int:pk>/pago/nuevo/", SeguroRegistrarPagoView.as_view(), name="pago_create"),
    path("<int:pk>/historial/nuevo/", HistorialRenovacionCreateView.as_view(), name="historial_create"),
]
