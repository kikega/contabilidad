"""Configuración del panel de administración para el módulo de Finanzas."""

from django.contrib import admin
from finanzas.models import (
    Categoria,
    CuentaAhorro,
    Elemento,
    Gasto,
    Ingreso,
    RegistroSaldoMensual,
)


class ElementoInline(admin.TabularInline):
    model = Elemento
    extra = 1
    fields = ("nombre", "es_fijo", "icono", "descripcion")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "icono", "color", "num_elementos", "creado_en")
    list_filter = ("tipo",)
    search_fields = ("nombre", "descripcion")
    ordering = ("tipo", "nombre")
    inlines = [ElementoInline]

    @admin.display(description="Nº Elementos")
    def num_elementos(self, obj: Categoria) -> int:
        return obj.elementos.count()


@admin.register(Elemento)
class ElementoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "es_fijo", "finalizado", "icono", "poliza_seguro_vinculada", "creado_en")
    list_filter = ("categoria__tipo", "categoria", "es_fijo", "finalizado")
    search_fields = ("nombre", "categoria__nombre", "descripcion")
    ordering = ("categoria", "nombre")
    autocomplete_fields = ["categoria"]
    list_editable = ("finalizado",)
    list_select_related = ("categoria",)

    @admin.display(description="Seguro Vinculado")
    def poliza_seguro_vinculada(self, obj: Elemento) -> str:
        if hasattr(obj, "seguro") and obj.seguro:
            return f"Póliza {obj.seguro.compania} ({obj.seguro.numero_poliza})"
        return "-"


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "elemento", "monto", "descripcion", "usuario")
    list_filter = ("elemento__categoria", "fecha", "usuario")
    search_fields = ("descripcion", "notas", "elemento__nombre")
    list_select_related = ("elemento__categoria", "usuario")
    autocomplete_fields = ["elemento", "usuario"]
    date_hierarchy = "fecha"
    ordering = ("-fecha",)


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "concepto", "elemento", "monto", "es_fijo", "usuario")
    list_filter = ("elemento__categoria", "es_fijo", "fecha", "usuario")
    search_fields = ("concepto", "notas", "elemento__nombre")
    list_select_related = ("elemento__categoria", "usuario")
    autocomplete_fields = ["elemento", "usuario"]
    date_hierarchy = "fecha"
    ordering = ("-fecha",)


class RegistroSaldoMensualInline(admin.TabularInline):
    model = RegistroSaldoMensual
    extra = 1
    fields = ("anio", "mes", "saldo", "notas")
    ordering = ("-anio", "-mes")


@admin.register(CuentaAhorro)
class CuentaAhorroAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "entidad",
        "tipo",
        "ultimo_saldo_display",
        "objetivo_monto",
        "activo",
        "usuario",
    )
    list_filter = ("tipo", "activo", "entidad")
    search_fields = ("nombre", "entidad", "numero_cuenta_iban", "notas")
    autocomplete_fields = ["usuario"]
    inlines = [RegistroSaldoMensualInline]
    ordering = ("nombre",)

    @admin.display(description="Último Saldo Registrado")
    def ultimo_saldo_display(self, obj: CuentaAhorro) -> str:
        ultimo = obj.get_ultimo_saldo()
        if ultimo:
            return f"{ultimo.saldo} € ({ultimo.mes}/{ultimo.anio})"
        return "Sin saldos"


@admin.register(RegistroSaldoMensual)
class RegistroSaldoMensualAdmin(admin.ModelAdmin):
    list_display = ("cuenta", "anio", "mes", "saldo", "notas", "actualizado_en")
    list_filter = ("anio", "mes", "cuenta__tipo", "cuenta")
    search_fields = ("cuenta__nombre", "cuenta__entidad", "notas")
    list_select_related = ("cuenta",)
    autocomplete_fields = ["cuenta"]
    ordering = ("-anio", "-mes", "cuenta__nombre")

