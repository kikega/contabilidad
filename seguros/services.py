"""Servicios y capa de lógica de negocio para la gestión y auditoría de pólizas de seguros."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from django.db.models import Count, QuerySet, Sum
from django.utils import timezone


class SeguroService:
    """Servicio para la sincronización contable, cálculo de KPIs e históricos de pólizas."""

    @staticmethod
    def sync_elemento(seguro: Any) -> Any:
        """Sincroniza o genera el Elemento contable correspondiente bajo la categoría Seguros."""
        from finanzas.models import Categoria, Elemento

        cat_seguros, _ = Categoria.objects.get_or_create(
            nombre="Seguros",
            tipo=Categoria.Tipo.GASTO,
            defaults={
                "icono": "shield-check",
                "color": "#2C92B8",
                "descripcion": "Pólizas de protección familiar, hogar y vehículos",
            },
        )

        nombre_base = f"{seguro.compania} - {seguro.bien_asegurado}".strip()
        nombre_elem = nombre_base
        icono_elem = seguro.RAMO_ICONOS.get(seguro.ramo, "shield-check")
        desc_elem = f"Póliza {seguro.numero_poliza} ({seguro.get_ramo_display()})"

        if seguro.elemento_id:
            elem = seguro.elemento
            # Si el nombre base ya está en uso por otro elemento, desambiguar con el número de póliza
            if Elemento.objects.filter(categoria=cat_seguros, nombre=nombre_elem).exclude(pk=elem.pk).exists():
                nombre_elem = f"{nombre_base} ({seguro.numero_poliza})".strip()
            elem.categoria = cat_seguros
            elem.nombre = nombre_elem
            elem.icono = icono_elem
            elem.descripcion = desc_elem
            elem.es_fijo = True
            elem.save()
        else:
            elem = Elemento.objects.filter(categoria=cat_seguros, nombre=nombre_elem).first()
            # Si el elemento existente ya está vinculado a otra póliza de seguro, desambiguar
            if elem and hasattr(elem, "seguro") and elem.seguro_id and elem.seguro_id != seguro.id:
                nombre_elem = f"{nombre_base} ({seguro.numero_poliza})".strip()
                elem = Elemento.objects.filter(categoria=cat_seguros, nombre=nombre_elem).first()

            if not elem:
                elem = Elemento.objects.create(
                    categoria=cat_seguros,
                    nombre=nombre_elem,
                    icono=icono_elem,
                    descripcion=desc_elem,
                    es_fijo=True,
                )
            else:
                elem.icono = icono_elem
                elem.descripcion = desc_elem
                elem.es_fijo = True
                elem.save()
            seguro.elemento = elem

        return seguro.elemento

    @staticmethod
    def get_resumen_gastos_anuales(seguro: Any) -> List[Dict[str, Any]]:
        """Agrupa los gastos reales pagados por año para análisis comparativo interanual."""
        if not seguro.elemento_id:
            return []

        qs = (
            seguro.elemento.gastos.values("fecha__year")
            .annotate(total=Sum("monto"), num_pagos=Count("id"))
            .order_by("-fecha__year")
        )

        resumen: List[Dict[str, Any]] = []
        lista = list(qs)
        for i, item in enumerate(lista):
            anio = item["fecha__year"]
            total = item["total"] or Decimal("0.00")

            prev_total: Optional[Decimal] = None
            var_importe = Decimal("0.00")
            var_porcentaje = Decimal("0.00")
            if i + 1 < len(lista):
                prev_total = lista[i + 1]["total"] or Decimal("0.00")
                var_importe = (total - prev_total).quantize(Decimal("0.01"))
                if prev_total > Decimal("0.00"):
                    var_porcentaje = (((total - prev_total) / prev_total) * Decimal("100.00")).quantize(Decimal("0.01"))

            resumen.append({
                "anio": anio,
                "total": total,
                "num_pagos": item["num_pagos"],
                "prev_total": prev_total,
                "var_importe": var_importe,
                "var_porcentaje": var_porcentaje,
            })
        return resumen

    @staticmethod
    def get_kpis_seguros(qs: QuerySet) -> Dict[str, Any]:
        """Calcula métricas agregadas de pólizas activas para el listado general."""
        polizas_activas = qs.filter(activo=True)
        coste_total_anual = polizas_activas.aggregate(
            total=Sum("prima_actual")
        )["total"] or Decimal("0.00")

        urgentes = [s for s in polizas_activas if s.estado_vencimiento == "urgente"]
        proximos = [s for s in polizas_activas if s.estado_vencimiento == "proximo"]

        return {
            "coste_total_anual": coste_total_anual,
            "num_polizas": polizas_activas.count(),
            "urgentes_count": len(urgentes),
            "proximos_count": len(proximos),
        }
