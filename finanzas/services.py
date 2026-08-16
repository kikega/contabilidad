"""Servicios y capa de lógica de negocio para cálculos financieros y agregaciones."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from finanzas.models import Categoria, Elemento, Gasto, GastoEspecialTarjeta, Ingreso


class FinanzasService:
    """Servicio de cálculo y análisis financiero para el Dashboard y reportes."""

    MESES_NOMBRES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    MESES_ABREV = [
        "Ene", "Feb", "Mar", "Abr", "May", "Jun",
        "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
    ]

    @staticmethod
    def get_periodo_fechas(
        anio: Optional[int] = None,
        mes: Optional[int] = None
    ) -> Tuple[date, date, int, Optional[int]]:
        """Determina el rango de fechas para filtrado."""
        hoy = timezone.now().date()
        anio_actual = anio or hoy.year
        
        if mes:
            inicio = date(anio_actual, mes, 1)
            if mes == 12:
                fin = date(anio_actual + 1, 1, 1)
            else:
                fin = date(anio_actual, mes + 1, 1)
        else:
            inicio = date(anio_actual, 1, 1)
            fin = date(anio_actual + 1, 1, 1)

        return inicio, fin, anio_actual, mes

    @classmethod
    def calcular_kpis(
        cls,
        fecha_inicio: date,
        fecha_fin: date,
        usuario_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calcula los indicadores clave de rendimiento (KPIs) para el periodo seleccionado."""
        filtro_ingresos = Q(fecha__gte=fecha_inicio, fecha__lt=fecha_fin)
        filtro_gastos = Q(fecha__gte=fecha_inicio, fecha__lt=fecha_fin)

        if usuario_id:
            filtro_ingresos &= Q(usuario_id=usuario_id)
            filtro_gastos &= Q(usuario_id=usuario_id)

        # Totales periodo actual
        total_ingresos = Ingreso.objects.filter(filtro_ingresos).aggregate(
            total=Coalesce(Sum("monto"), Decimal("0.00"), output_field=DecimalField())
        )["total"]

        total_gastos = Gasto.objects.filter(filtro_gastos).aggregate(
            total=Coalesce(Sum("monto"), Decimal("0.00"), output_field=DecimalField())
        )["total"]

        ahorro_neto = total_ingresos - total_gastos
        ratio_ahorro = (
            ((ahorro_neto / total_ingresos) * Decimal("100.00")).quantize(Decimal("0.01"))
            if total_ingresos > Decimal("0.00")
            else Decimal("0.00")
        )

        # Comparativa con el periodo anterior de igual duración
        dias_periodo = (fecha_fin - fecha_inicio).days
        prev_inicio = fecha_inicio - (fecha_fin - fecha_inicio)
        prev_fin = fecha_inicio

        filtro_prev_ing = Q(fecha__gte=prev_inicio, fecha__lt=prev_fin)
        filtro_prev_gas = Q(fecha__gte=prev_inicio, fecha__lt=prev_fin)
        if usuario_id:
            filtro_prev_ing &= Q(usuario_id=usuario_id)
            filtro_prev_gas &= Q(usuario_id=usuario_id)

        prev_ingresos = Ingreso.objects.filter(filtro_prev_ing).aggregate(
            total=Coalesce(Sum("monto"), Decimal("0.00"), output_field=DecimalField())
        )["total"]
        prev_gastos = Gasto.objects.filter(filtro_prev_gas).aggregate(
            total=Coalesce(Sum("monto"), Decimal("0.00"), output_field=DecimalField())
        )["total"]
        prev_ahorro = prev_ingresos - prev_gastos

        def calc_variacion(actual: Decimal, previo: Decimal) -> Tuple[Decimal, str]:
            if previo > Decimal("0.00"):
                var = ((actual - previo) / previo) * Decimal("100.00")
                return var.quantize(Decimal("0.01")), "up" if var >= 0 else "down"
            elif actual > Decimal("0.00"):
                return Decimal("100.00"), "up"
            return Decimal("0.00"), "neutral"

        var_ingresos, dir_ingresos = calc_variacion(total_ingresos, prev_ingresos)
        var_gastos, dir_gastos = calc_variacion(total_gastos, prev_gastos)
        var_ahorro, dir_ahorro = calc_variacion(ahorro_neto, prev_ahorro)

        return {
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "ahorro_neto": ahorro_neto,
            "ratio_ahorro": ratio_ahorro,
            "tendencias": {
                "ingresos": {"variacion": var_ingresos, "direccion": dir_ingresos},
                "gastos": {"variacion": var_gastos, "direccion": dir_gastos},
                "ahorro": {"variacion": var_ahorro, "direccion": dir_ahorro},
            },
        }

    @classmethod
    def get_datos_graficos_anuales(
        cls,
        anio: int,
        usuario_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Genera las series de datos para los gráficos anuales: Ingresos vs Gastos, Evolución Ahorro y Distribución por Categoría."""
        inicio_anio = date(anio, 1, 1)
        fin_anio = date(anio + 1, 1, 1)

        filtro_ingresos = Q(fecha__gte=inicio_anio, fecha__lt=fin_anio)
        filtro_gastos = Q(fecha__gte=inicio_anio, fecha__lt=fin_anio)
        if usuario_id:
            filtro_ingresos &= Q(usuario_id=usuario_id)
            filtro_gastos &= Q(usuario_id=usuario_id)

        # Agrupación de ingresos por mes
        ingresos_por_mes_qs = (
            Ingreso.objects.filter(filtro_ingresos)
            .annotate(mes=TruncMonth("fecha"))
            .values("mes")
            .annotate(total=Sum("monto"))
            .order_by("mes")
        )
        dict_ingresos = {item["mes"].month: item["total"] for item in ingresos_por_mes_qs}

        # Agrupación de gastos por mes
        gastos_por_mes_qs = (
            Gasto.objects.filter(filtro_gastos)
            .annotate(mes=TruncMonth("fecha"))
            .values("mes")
            .annotate(total=Sum("monto"))
            .order_by("mes")
        )
        dict_gastos = {item["mes"].month: item["total"] for item in gastos_por_mes_qs}

        ingresos_series: List[float] = []
        gastos_series: List[float] = []
        ahorro_mensual_series: List[float] = []
        ahorro_acumulado_series: List[float] = []

        acumulado = Decimal("0.00")
        for m in range(1, 13):
            ing = dict_ingresos.get(m, Decimal("0.00"))
            gas = dict_gastos.get(m, Decimal("0.00"))
            neto = ing - gas
            acumulado += neto

            ingresos_series.append(float(ing))
            gastos_series.append(float(gas))
            ahorro_mensual_series.append(float(neto))
            ahorro_acumulado_series.append(float(acumulado))

        # Distribución de gastos agrupados por Categoría padre
        distribucion_qs = (
            Gasto.objects.filter(filtro_gastos)
            .values("elemento__categoria__nombre", "elemento__categoria__color")
            .annotate(total=Sum("monto"))
            .order_by("-total")
        )

        dist_labels: List[str] = []
        dist_data: List[float] = []
        dist_colors: List[str] = []

        for item in distribucion_qs:
            nombre_cat = item["elemento__categoria__nombre"] or "Varios"
            color_cat = item["elemento__categoria__color"] or "#3BB8DB"
            dist_labels.append(nombre_cat)
            dist_data.append(float(item["total"]))
            dist_colors.append(color_cat)

        return {
            "meses": cls.MESES_ABREV,
            "ingresos": ingresos_series,
            "gastos": gastos_series,
            "ahorro_mensual": ahorro_mensual_series,
            "ahorro_acumulado": ahorro_acumulado_series,
            "distribucion": {
                "labels": dist_labels,
                "data": dist_data,
                "colors": dist_colors,
            },
        }

    @classmethod
    def get_movimientos_recientes(
        cls,
        limite: int = 10,
        tipo_filtro: str = "TODOS",
        usuario_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Devuelve un listado consolidado y ordenado cronológicamente de los movimientos más recientes."""
        movimientos: List[Dict[str, Any]] = []

        if tipo_filtro in ["TODOS", "INGRESO"]:
            qs_ing = Ingreso.objects.select_related("elemento__categoria", "usuario").all()
            if usuario_id:
                qs_ing = qs_ing.filter(usuario_id=usuario_id)
            for ing in qs_ing.order_by("-fecha", "-creado_en")[:limite]:
                elem_nom = ing.elemento.nombre if ing.elemento else (ing.descripcion or ing.get_fuente_display())
                cat_nom = ing.elemento.categoria.nombre if (ing.elemento and ing.elemento.categoria) else "Ingresos"
                cat_col = ing.elemento.categoria.color if (ing.elemento and ing.elemento.categoria) else "#3BB8DB"
                icono = ing.elemento.icono_efectivo if ing.elemento else "wallet"

                movimientos.append({
                    "id": ing.id,
                    "tipo": "INGRESO",
                    "fecha": ing.fecha,
                    "concepto": ing.descripcion or elem_nom,
                    "elemento": elem_nom,
                    "categoria": cat_nom,
                    "categoria_color": cat_col,
                    "icono": icono,
                    "monto": ing.monto,
                    "usuario": ing.usuario.get_short_name() if ing.usuario else "-",
                    "es_positivo": True,
                })

        if tipo_filtro in ["TODOS", "GASTO"]:
            qs_gas = Gasto.objects.select_related("elemento__categoria", "usuario").all()
            if usuario_id:
                qs_gas = qs_gas.filter(usuario_id=usuario_id)
            for gas in qs_gas.order_by("-fecha", "-creado_en")[:limite]:
                elem_nom = gas.elemento.nombre if gas.elemento else gas.concepto
                cat_nom = gas.elemento.categoria.nombre if (gas.elemento and gas.elemento.categoria) else "Gastos"
                cat_col = gas.elemento.categoria.color if (gas.elemento and gas.elemento.categoria) else "#015F78"
                icono = gas.elemento.icono_efectivo if gas.elemento else "folder"

                movimientos.append({
                    "id": gas.id,
                    "tipo": "GASTO",
                    "fecha": gas.fecha,
                    "concepto": gas.concepto,
                    "elemento": elem_nom,
                    "categoria": cat_nom,
                    "categoria_color": cat_col,
                    "icono": icono,
                    "monto": gas.monto,
                    "usuario": gas.usuario.get_short_name() if gas.usuario else "-",
                    "es_positivo": False,
                })

        movimientos.sort(key=lambda x: x["fecha"], reverse=True)
        return movimientos[:limite]

    @classmethod
    def get_resumen_cuentas_mensual(
        cls,
        anio: int,
        mes: int,
        usuario_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Genera el desglose contable mensual completo organizado en jerarquía: Categorías -> Elementos -> Apuntes."""
        inicio = date(anio, mes, 1)
        fin = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)

        # Navegación mes anterior / siguiente
        if mes == 1:
            prev_mes, prev_anio = 12, anio - 1
        else:
            prev_mes, prev_anio = mes - 1, anio

        if mes == 12:
            next_mes, next_anio = 1, anio + 1
        else:
            next_mes, next_anio = mes + 1, anio

        nombre_mes = cls.MESES_NOMBRES[mes - 1]

        # 1. Ingresos jerárquicos
        filtro_ing = Q(fecha__gte=inicio, fecha__lt=fin)
        if usuario_id:
            filtro_ing &= Q(usuario_id=usuario_id)

        ingresos_qs = Ingreso.objects.filter(filtro_ing).select_related("elemento__categoria", "usuario").order_by("fecha")
        categorias_ingreso_qs = (
            Categoria.objects.filter(tipo=Categoria.Tipo.INGRESO)
            .prefetch_related("elementos")
            .order_by("nombre")
        )

        desglose_ingresos: List[Dict[str, Any]] = []
        total_ingresos = Decimal("0.00")

        for cat in categorias_ingreso_qs:
            elementos_data = []
            subtotal_cat = Decimal("0.00")

            for elem in cat.elementos.all():
                items = [ing for ing in ingresos_qs if ing.elemento_id == elem.id]
                subtotal_elem = sum((item.monto for item in items), Decimal("0.00"))
                subtotal_cat += subtotal_elem
                total_ingresos += subtotal_elem

                elementos_data.append({
                    "elemento": elem,
                    "items": items,
                    "subtotal": subtotal_elem,
                    "tiene_items": len(items) > 0,
                })

            desglose_ingresos.append({
                "categoria": cat,
                "elementos": elementos_data,
                "subtotal": subtotal_cat,
                "tiene_items": subtotal_cat > Decimal("0.00"),
            })

        # 2. Gastos jerárquicos
        filtro_gas = Q(fecha__gte=inicio, fecha__lt=fin)
        if usuario_id:
            filtro_gas &= Q(usuario_id=usuario_id)

        gastos_qs = Gasto.objects.filter(filtro_gas).select_related("elemento__categoria", "usuario").order_by("fecha")
        categorias_gasto_qs = (
            Categoria.objects.filter(tipo=Categoria.Tipo.GASTO)
            .prefetch_related("elementos")
            .order_by("nombre")
        )

        desglose_gastos: List[Dict[str, Any]] = []
        total_gastos = Decimal("0.00")
        total_fijos = Decimal("0.00")
        total_variables = Decimal("0.00")

        for cat in categorias_gasto_qs:
            elementos_data = []
            subtotal_cat = Decimal("0.00")

            for elem in cat.elementos.all():
                items = [gas for gas in gastos_qs if gas.elemento_id == elem.id]
                subtotal_elem = sum((item.monto for item in items), Decimal("0.00"))
                subtotal_cat += subtotal_elem
                total_gastos += subtotal_elem

                for it in items:
                    if it.es_fijo or elem.es_fijo:
                        total_fijos += it.monto
                    else:
                        total_variables += it.monto

                elementos_data.append({
                    "elemento": elem,
                    "items": items,
                    "subtotal": subtotal_elem,
                    "tiene_items": len(items) > 0,
                })

            desglose_gastos.append({
                "categoria": cat,
                "elementos": elementos_data,
                "subtotal": subtotal_cat,
                "tiene_items": subtotal_cat > Decimal("0.00"),
            })

        balance_neto = total_ingresos - total_gastos
        ratio_ahorro = (
            ((balance_neto / total_ingresos) * Decimal("100.00")).quantize(Decimal("0.01"))
            if total_ingresos > Decimal("0.00")
            else Decimal("0.00")
        )

        return {
            "anio": anio,
            "mes": mes,
            "nombre_mes": nombre_mes,
            "prev_mes": prev_mes,
            "prev_anio": prev_anio,
            "next_mes": next_mes,
            "next_anio": next_anio,
            "desglose_ingresos": desglose_ingresos,
            "desglose_gastos": desglose_gastos,
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "total_fijos": total_fijos,
            "total_variables": total_variables,
            "balance_neto": balance_neto,
            "ratio_ahorro": ratio_ahorro,
        }
