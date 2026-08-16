"""Enrutamiento de URLs para el módulo de Finanzas."""

from django.urls import path
from finanzas.views import (
    AdministracionView,
    CategoriaCreateView,
    CategoriaDeleteView,
    CategoriaUpdateView,
    CuentasMesHtmxView,
    CuentasView,
    DashboardView,
    ElementoCreateView,
    ElementoDeleteView,
    ElementoUpdateView,
    GastoCreateView,
    GastoDeleteView,
    GastoEspecialTarjetaCreateView,
    GastoEspecialTarjetaDeleteView,
    GastoEspecialTarjetaListView,
    GastoUpdateView,
    GraficosDataApiView,
    IngresoCreateView,
    IngresoDeleteView,
    IngresoUpdateView,
    TransaccionesTablaHtmxView,
)

app_name = "finanzas"

urlpatterns = [
    # Dashboard principal
    path("", DashboardView.as_view(), name="dashboard"),
    path("cuentas/", CuentasView.as_view(), name="cuentas"),
    path("cuentas/mes-htmx/", CuentasMesHtmxView.as_view(), name="cuentas_mes_htmx"),
    path("administracion/", AdministracionView.as_view(), name="administracion"),
    
    # Categorías
    path("administracion/categorias/nueva/", CategoriaCreateView.as_view(), name="categoria_create"),
    path("administracion/categorias/<int:pk>/editar/", CategoriaUpdateView.as_view(), name="categoria_update"),
    path("administracion/categorias/<int:pk>/eliminar/", CategoriaDeleteView.as_view(), name="categoria_delete"),

    # Elementos / Subcategorías
    path("administracion/elementos/nuevo/", ElementoCreateView.as_view(), name="elemento_create"),
    path("administracion/elementos/<int:pk>/editar/", ElementoUpdateView.as_view(), name="elemento_update"),
    path("administracion/elementos/<int:pk>/eliminar/", ElementoDeleteView.as_view(), name="elemento_delete"),

    path("htmx/tabla-transacciones/", TransaccionesTablaHtmxView.as_view(), name="tabla_transacciones_htmx"),
    path("api/graficos-data/", GraficosDataApiView.as_view(), name="graficos_data_api"),

    # Ingresos
    path("ingresos/nuevo/", IngresoCreateView.as_view(), name="ingreso_create"),
    path("ingresos/<int:pk>/editar/", IngresoUpdateView.as_view(), name="ingreso_update"),
    path("ingresos/<int:pk>/eliminar/", IngresoDeleteView.as_view(), name="ingreso_delete"),

    # Gastos
    path("gastos/nuevo/", GastoCreateView.as_view(), name="gasto_create"),
    path("gastos/<int:pk>/editar/", GastoUpdateView.as_view(), name="gasto_update"),
    path("gastos/<int:pk>/eliminar/", GastoDeleteView.as_view(), name="gasto_delete"),

    # Tarjetas Especiales
    path("tarjetas/", GastoEspecialTarjetaListView.as_view(), name="tarjetas_list"),
    path("tarjetas/nuevo/", GastoEspecialTarjetaCreateView.as_view(), name="tarjeta_create"),
    path("tarjetas/<int:pk>/eliminar/", GastoEspecialTarjetaDeleteView.as_view(), name="tarjeta_delete"),
]
