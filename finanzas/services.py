"""Servicios y capa de lógica de negocio para cálculos financieros y agregaciones."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from finanzas.models import (
    Categoria,
    CuentaAhorro,
    Elemento,
    Gasto,
    GastoEspecialTarjeta,
    Ingreso,
    RegistroSaldoMensual,
)


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

    @classmethod
    def get_anios_disponibles(cls, usuario_id: Optional[int] = None) -> List[int]:
        """Obtiene la lista ordenada de años para los que existen datos contables registrados."""
        hoy = timezone.now().date()

        filtro_ing = Q()
        filtro_gas = Q()
        filtro_tar = Q()
        filtro_aho = Q()
        if usuario_id:
            filtro_ing = Q(usuario_id=usuario_id)
            filtro_gas = Q(usuario_id=usuario_id)
            filtro_tar = Q(usuario_id=usuario_id)
            filtro_aho = Q(cuenta__usuario_id=usuario_id)

        anios_ingresos = Ingreso.objects.filter(filtro_ing).dates("fecha", "year")
        anios_gastos = Gasto.objects.filter(filtro_gas).dates("fecha", "year")
        anios_tarjetas = GastoEspecialTarjeta.objects.filter(filtro_tar).dates("fecha", "year")
        anios_ahorros = RegistroSaldoMensual.objects.filter(filtro_aho).values_list("anio", flat=True).distinct()

        anios_set = {d.year for d in anios_ingresos} | {d.year for d in anios_gastos} | {d.year for d in anios_tarjetas} | set(anios_ahorros)

        if not anios_set:
            anios_set.add(hoy.year)

        return sorted(list(anios_set))

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

    @classmethod
    def get_resumen_ahorros_anual(
        cls,
        anio: int,
        usuario_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calcula la matriz de saldos mensuales, totales, evoluciones y métricas para las cuentas de ahorro."""
        hoy = timezone.now().date()

        filtro_cuenta = Q(activo=True)
        if usuario_id:
            filtro_cuenta &= Q(usuario_id=usuario_id)

        cuentas_qs = CuentaAhorro.objects.filter(filtro_cuenta).prefetch_related("saldos").order_by("nombre")

        filas_cuentas = []
        totales_meses: List[Optional[Decimal]] = [None] * 12
        series_chart_cuentas = []

        total_ahorro_actual = Decimal("0.00")
        total_meta_ahorro = Decimal("0.00")
        tiene_metas = False

        distribucion_labels = []
        distribucion_data = []
        distribucion_colors = []

        for cuenta in cuentas_qs:
            saldos_anio = {s.mes: s for s in cuenta.saldos.filter(anio=anio)}
            # Saldo a cierre de año anterior para calcular variación
            saldo_anterior_cierre = cuenta.saldos.filter(anio=anio - 1, mes=12).first()
            if not saldo_anterior_cierre:
                saldo_anterior_cierre = cuenta.saldos.filter(anio__lt=anio).order_by("-anio", "-mes").first()

            meses_datos = []
            datos_grafico_cuenta: List[Optional[float]] = []
            ultimo_saldo_cuenta: Optional[Decimal] = None
            primer_saldo_cuenta: Optional[Decimal] = saldo_anterior_cierre.saldo if saldo_anterior_cierre else None

            for m in range(1, 13):
                reg = saldos_anio.get(m)
                val_saldo = reg.saldo if reg else None
                notas = reg.notas if reg else ""
                reg_id = reg.id if reg else None

                meses_datos.append({
                    "mes": m,
                    "saldo": val_saldo,
                    "notas": notas,
                    "id": reg_id,
                })

                if val_saldo is not None:
                    ultimo_saldo_cuenta = val_saldo
                    if primer_saldo_cuenta is None:
                        primer_saldo_cuenta = val_saldo
                    # Sumar al total del mes
                    if totales_meses[m - 1] is None:
                        totales_meses[m - 1] = val_saldo
                    else:
                        totales_meses[m - 1] += val_saldo
                    datos_grafico_cuenta.append(float(val_saldo))
                else:
                    datos_grafico_cuenta.append(None)

            # Variación anual de esta cuenta
            variacion_cuenta_imp = Decimal("0.00")
            variacion_cuenta_pct = Decimal("0.00")
            if ultimo_saldo_cuenta is not None and primer_saldo_cuenta is not None:
                variacion_cuenta_imp = (ultimo_saldo_cuenta - primer_saldo_cuenta).quantize(Decimal("0.01"))
                if primer_saldo_cuenta > Decimal("0.00"):
                    variacion_cuenta_pct = (((ultimo_saldo_cuenta - primer_saldo_cuenta) / primer_saldo_cuenta) * Decimal("100.00")).quantize(Decimal("0.01"))

            # Último saldo absoluto general de la cuenta
            ultimo_absoluto = cuenta.get_ultimo_saldo()
            saldo_act = ultimo_absoluto.saldo if ultimo_absoluto else Decimal("0.00")
            total_ahorro_actual += saldo_act

            if cuenta.objetivo_monto:
                total_meta_ahorro += cuenta.objetivo_monto
                tiene_metas = True

            if saldo_act > Decimal("0.00"):
                distribucion_labels.append(cuenta.nombre)
                distribucion_data.append(float(saldo_act))
                distribucion_colors.append(cuenta.color)

            filas_cuentas.append({
                "cuenta": cuenta,
                "meses": meses_datos,
                "saldo_actual": saldo_act,
                "ultimo_saldo_anio": ultimo_saldo_cuenta,
                "variacion_importe": variacion_cuenta_imp,
                "variacion_porcentaje": variacion_cuenta_pct,
            })

            series_chart_cuentas.append({
                "nombre": cuenta.nombre,
                "color": cuenta.color,
                "icono": cuenta.icono,
                "datos": datos_grafico_cuenta,
            })

        # Cálculo de variaciones mes a mes en los totales
        totales_meses_data = []
        evolucion_total_chart: List[Optional[float]] = []
        prev_total_m = None
        ultimo_total_registrado = None
        penultimo_total_registrado = None

        for m_idx, tot_val in enumerate(totales_meses):
            mes_num = m_idx + 1
            var_m = Decimal("0.00")
            if tot_val is not None:
                if prev_total_m is not None:
                    var_m = (tot_val - prev_total_m).quantize(Decimal("0.01"))
                penultimo_total_registrado = ultimo_total_registrado
                ultimo_total_registrado = tot_val
                prev_total_m = tot_val
                evolucion_total_chart.append(float(tot_val))
            else:
                evolucion_total_chart.append(None)

            totales_meses_data.append({
                "mes": mes_num,
                "total": tot_val,
                "variacion_mes": var_m,
            })

        # Variación del último mes registrado
        var_ultimo_mes_imp = Decimal("0.00")
        var_ultimo_mes_pct = Decimal("0.00")
        if ultimo_total_registrado is not None and penultimo_total_registrado is not None:
            var_ultimo_mes_imp = (ultimo_total_registrado - penultimo_total_registrado).quantize(Decimal("0.01"))
            if penultimo_total_registrado > Decimal("0.00"):
                var_ultimo_mes_pct = (((ultimo_total_registrado - penultimo_total_registrado) / penultimo_total_registrado) * Decimal("100.00")).quantize(Decimal("0.01"))

        # Crecimiento acumulado en el año
        primer_total_anio = next((t for t in totales_meses if t is not None), None)
        crecimiento_anio_imp = Decimal("0.00")
        crecimiento_anio_pct = Decimal("0.00")
        if ultimo_total_registrado is not None and primer_total_anio is not None:
            crecimiento_anio_imp = (ultimo_total_registrado - primer_total_anio).quantize(Decimal("0.01"))
            if primer_total_anio > Decimal("0.00"):
                crecimiento_anio_pct = (((ultimo_total_registrado - primer_total_anio) / primer_total_anio) * Decimal("100.00")).quantize(Decimal("0.01"))

        porcentaje_meta = (
            ((total_ahorro_actual / total_meta_ahorro) * Decimal("100.00")).quantize(Decimal("0.01"))
            if tiene_metas and total_meta_ahorro > Decimal("0.00")
            else None
        )

        # Datos para comparativa con año anterior
        totales_anio_anterior: List[Optional[float]] = []
        for m_idx in range(1, 13):
            s_ant = RegistroSaldoMensual.objects.filter(
                cuenta__in=cuentas_qs,
                anio=anio - 1,
                mes=m_idx,
            ).aggregate(total=Sum("saldo"))["total"]
            totales_anio_anterior.append(float(s_ant) if s_ant is not None else None)

        return {
            "anio": anio,
            "meses_abrev": cls.MESES_ABREV,
            "meses_nombres": cls.MESES_NOMBRES,
            "meses_lista": list(enumerate(cls.MESES_NOMBRES, 1)),
            "filas_cuentas": filas_cuentas,
            "totales_meses": totales_meses_data,
            "kpis": {
                "total_ahorro_actual": total_ahorro_actual,
                "total_meta_ahorro": total_meta_ahorro,
                "porcentaje_meta": porcentaje_meta,
                "crecimiento_anio_importe": crecimiento_anio_imp,
                "crecimiento_anio_porcentaje": crecimiento_anio_pct,
                "aportacion_ultimo_mes_importe": var_ultimo_mes_imp,
                "aportacion_ultimo_mes_porcentaje": var_ultimo_mes_pct,
                "num_cuentas": cuentas_qs.count(),
            },
            "graficos": {
                "meses": cls.MESES_ABREV,
                "evolucion_total": evolucion_total_chart,
                "series_cuentas": series_chart_cuentas,
                "distribucion": {
                    "labels": distribucion_labels,
                    "data": distribucion_data,
                    "colors": distribucion_colors,
                },
                "comparativa": {
                    "anio_actual": anio,
                    "data_actual": evolucion_total_chart,
                    "anio_anterior": anio - 1,
                    "data_anterior": totales_anio_anterior,
                },
            },
        }
