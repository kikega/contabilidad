"""Configuración del panel de administración para el módulo de Finanzas."""

from django.contrib import admin
from finanzas.models import Categoria, Elemento, Gasto, GastoEspecialTarjeta, Ingreso


class ElementoInline(admin.TabularInline):
    model = Elemento
    extra = 1
    fields = ("nombre", "es_fijo", "icono", "descripcion")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "icono", "color", "creado_en")
    list_filter = ("tipo",)
    search_fields = ("nombre", "descripcion")
    ordering = ("tipo", "nombre")
    inlines = [ElementoInline]


@admin.register(Elemento)
class ElementoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "es_fijo", "icono", "creado_en")
    list_filter = ("categoria__tipo", "categoria", "es_fijo")
    search_fields = ("nombre", "categoria__nombre", "descripcion")
    ordering = ("categoria", "nombre")


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "fuente", "elemento", "monto", "usuario", "descripcion")
    list_filter = ("fuente", "elemento__categoria", "elemento", "fecha", "usuario")
    search_fields = ("descripcion", "notas", "elemento__nombre")
    date_hierarchy = "fecha"
    ordering = ("-fecha",)


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "concepto", "elemento", "monto", "es_fijo", "usuario")
    list_filter = ("elemento__categoria", "elemento", "es_fijo", "fecha", "usuario")
    search_fields = ("concepto", "notas", "elemento__nombre")
    date_hierarchy = "fecha"
    ordering = ("-fecha",)


@admin.register(GastoEspecialTarjeta)
class GastoEspecialTarjetaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "comercio", "tipo_comercio", "tarjeta", "monto", "usuario")
    list_filter = ("tipo_comercio", "tarjeta", "fecha", "usuario")
    search_fields = ("comercio", "tarjeta", "notas")
    date_hierarchy = "fecha"
    ordering = ("-fecha",)
