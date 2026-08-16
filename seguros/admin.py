"""Configuración del panel de administración para el módulo de Seguros."""

from django.contrib import admin
from seguros.models import HistorialRenovacionSeguro, Seguro


class HistorialRenovacionInline(admin.TabularInline):
    model = HistorialRenovacionSeguro
    extra = 1


@admin.register(Seguro)
class SeguroAdmin(admin.ModelAdmin):
    list_display = (
        "bien_asegurado",
        "ramo",
        "compania",
        "numero_poliza",
        "fecha_vencimiento",
        "prima_actual",
        "prima_anterior",
        "incremento_display",
        "activo",
    )
    list_filter = ("ramo", "activo", "compania", "fecha_vencimiento")
    search_fields = ("bien_asegurado", "compania", "numero_poliza", "gestor_nombre", "notas_negociacion")
    inlines = [HistorialRenovacionInline]
    date_hierarchy = "fecha_vencimiento"
    ordering = ["fecha_vencimiento"]

    @admin.display(description="Variación %")
    def incremento_display(self, obj: Seguro) -> str:
        pct = obj.incremento_porcentaje
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct}%"


@admin.register(HistorialRenovacionSeguro)
class HistorialRenovacionSeguroAdmin(admin.ModelAdmin):
    list_display = ("seguro", "ejercicio_anio", "prima_pagada", "fecha_renovacion")
    list_filter = ("ejercicio_anio", "seguro__compania")
    search_fields = ("seguro__bien_asegurado", "seguro__compania", "notas")
    ordering = ("-ejercicio_anio",)
