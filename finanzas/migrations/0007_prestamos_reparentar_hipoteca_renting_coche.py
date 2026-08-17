"""Crea la categoría de Préstamos, reparenta la hipoteca y renombra el renting del coche."""

from django.db import migrations


def crear_categoria_prestamos_reparentar_hipoteca_y_renombrar_renting(apps, schema_editor):
    Categoria = apps.get_model("finanzas", "Categoria")
    Elemento = apps.get_model("finanzas", "Elemento")

    cat_prestamos, _ = Categoria.objects.get_or_create(
        nombre="Préstamos & Financiaciones",
        tipo="GASTO",
        defaults={
            "icono": "landmark",
            "color": "#8B5CF6",
            "descripcion": "Cuotas de préstamos y financiaciones pagadas por domiciliación o transferencia",
        },
    )

    hipoteca = Elemento.objects.filter(nombre__iexact="Hipoteca / Alquiler").first()
    if hipoteca:
        hipoteca.categoria = cat_prestamos
        hipoteca.icono = "landmark"
        hipoteca.es_fijo = True
        hipoteca.descripcion = "Cuota hipotecaria mensual (se marca como finalizada al terminar de pagar)"
        hipoteca.save(update_fields=["categoria", "icono", "es_fijo", "descripcion"])

    Elemento.objects.filter(nombre="Préstamo Coche").update(
        nombre="Renting Coche",
        descripcion="Renting con opción de compra o cambio de vehículo",
    )


def revertir(apps, schema_editor):
    Elemento = apps.get_model("finanzas", "Elemento")
    Elemento.objects.filter(nombre="Renting Coche").update(
        nombre="Préstamo Coche",
        descripcion="Financiación bancaria vehículo",
    )
    Categoria = apps.get_model("finanzas", "Categoria")
    Categoria.objects.filter(nombre="Préstamos & Financiaciones").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("finanzas", "0006_elemento_fecha_finalizacion_elemento_finalizado"),
    ]

    operations = [
        migrations.RunPython(
            crear_categoria_prestamos_reparentar_hipoteca_y_renombrar_renting,
            revertir,
        ),
    ]