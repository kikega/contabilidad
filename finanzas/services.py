"""Servicios y capa de lógica de negocio para cálculos financieros y agregaciones."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from django.db.models import Case, Count, DecimalField, IntegerField, Q, Sum, Value, When, QuerySet
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from finanzas.models import (
    Categoria,
    CuentaAhorro,
    Elemento,
    Gasto,
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
        filtro_aho = Q()
        if usuario_id:
            filtro_ing = Q(usuario_id=usuario_id)
            filtro_gas = Q(usuario_id=usuario_id)
            filtro_aho = Q(cuenta__usuario_id=usuario_id)

        anios_ingresos = Ingreso.objects.filter(filtro_ing).dates("fecha", "year")
        anios_gastos = Gasto.objects.filter(filtro_gas).dates("fecha", "year")
        anios_ahorros = RegistroSaldoMensual.objects.filter(filtro_aho).values_list("anio", flat=True).distinct()

        anios_set = {d.year for d in anios_ingresos} | {d.year for d in anios_gastos} | set(anios_ahorros)

        if not anios_set:
            anios_set.add(hoy.year)

        return sorted(list(anios_set))

    @classmethod
    def get_categorias_gasto_queryset(cls, elementos_prefetch=None) -> QuerySet[Categoria]:
        """Obtiene el queryset de categorías de gasto ordenadas con prioridad:
        1. Tarjetas (nombres con 'tarjeta')
        2. Gastos Casa (nombres con 'gastos casa' o 'casa')
        3. Resto de categorías por orden alfabético.
        """
        prioridad_orden = Case(
            When(nombre__icontains="tarjeta", then=Value(1)),
            When(Q(nombre__icontains="gastos casa") | Q(nombre__iexact="casa"), then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
        return (
            Categoria.objects.filter(tipo=Categoria.Tipo.GASTO)
            .annotate(prioridad_orden=prioridad_orden)
            .prefetch_related(elementos_prefetch or "elementos")
            .order_by("prioridad_orden", "nombre")
        )

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
                elem_nom = ing.elemento.nombre if ing.elemento else (ing.descripcion or "Ingreso")
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
    def get_resumen_cuentas_anual(
        cls,
        anio: int,
        usuario_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calcula la matriz completa anual (12 meses) de ingresos y gastos organizados por categorías y elementos."""
        inicio_anio = date(anio, 1, 1)
        fin_anio = date(anio + 1, 1, 1)

        def _agregados_por_elemento_mes(modelo) -> Dict[int, Dict[int, Tuple[Decimal, int]]]:
            """Agrupa en SQL los importes por elemento y mes: {elemento_id: {mes: (total, count)}}."""
            qs = modelo.objects.filter(fecha__gte=inicio_anio, fecha__lt=fin_anio)
            if usuario_id:
                qs = qs.filter(usuario_id=usuario_id)
            filas = (
                qs.exclude(elemento_id__isnull=True)
                .values("elemento_id")
                .annotate(mes=TruncMonth("fecha"))
                .values("elemento_id", "mes")
                .annotate(total=Sum("monto"), count=Count("id"))
            )
            agregados: Dict[int, Dict[int, Tuple[Decimal, int]]] = {}
            for fila in filas:
                agregados.setdefault(fila["elemento_id"], {})[fila["mes"].month] = (
                    fila["total"],
                    fila["count"],
                )
            return agregados

        def _construir_desglose(categorias_qs, agregados):
            desglose = []
            totales_mes = [Decimal("0.00")] * 12
            total_anual = Decimal("0.00")

            for cat in categorias_qs:
                elementos_data = []
                totales_mes_cat = [Decimal("0.00")] * 12
                total_anual_cat = Decimal("0.00")

                for elem in cat.elementos.all():
                    meses_elem = []
                    total_anual_elem = Decimal("0.00")
                    por_mes = agregados.get(elem.id, {})

                    for m in range(1, 13):
                        total_m, count_m = por_mes.get(m, (Decimal("0.00"), 0))
                        meses_elem.append({"mes": m, "total": total_m, "count": count_m})

                        total_anual_elem += total_m
                        totales_mes_cat[m - 1] += total_m
                        totales_mes[m - 1] += total_m

                    total_anual_cat += total_anual_elem
                    total_anual += total_anual_elem

                    elementos_data.append({
                        "elemento": elem,
                        "meses": meses_elem,
                        "total_anual": total_anual_elem,
                        "tiene_apuntes": total_anual_elem > Decimal("0.00"),
                    })

                desglose.append({
                    "categoria": cat,
                    "elementos": elementos_data,
                    "totales_meses": totales_mes_cat,
                    "total_anual": total_anual_cat,
                    "tiene_apuntes": total_anual_cat > Decimal("0.00"),
                })

            return desglose, totales_mes, total_anual

        # 1. Ingresos
        categorias_ingreso_qs = (
            Categoria.objects.filter(tipo=Categoria.Tipo.INGRESO)
            .prefetch_related("elementos")
            .order_by("nombre")
        )
        desglose_ingresos, totales_ingresos_mes, total_anual_ingresos = _construir_desglose(
            categorias_ingreso_qs,
            _agregados_por_elemento_mes(Ingreso),
        )

        # 2. Gastos
        desglose_gastos, totales_gastos_mes, total_anual_gastos = _construir_desglose(
            cls.get_categorias_gasto_queryset(),
            _agregados_por_elemento_mes(Gasto),
        )

        # 3. Totales globales mes a mes
        resumen_global_meses = []
        for m in range(1, 13):
            ing_m = totales_ingresos_mes[m - 1]
            gas_m = totales_gastos_mes[m - 1]
            resumen_global_meses.append({
                "mes": m,
                "nombre": cls.MESES_ABREV[m - 1],
                "ingresos": ing_m,
                "gastos": gas_m,
                "balance": ing_m - gas_m,
            })

        balance_anual = total_anual_ingresos - total_anual_gastos
        ratio_ahorro_anual = (
            ((balance_anual / total_anual_ingresos) * Decimal("100.00")).quantize(Decimal("0.01"))
            if total_anual_ingresos > Decimal("0.00")
            else Decimal("0.00")
        )

        return {
            "anio": anio,
            "meses_abrev": cls.MESES_ABREV,
            "meses_nombres": cls.MESES_NOMBRES,
            "desglose_ingresos": desglose_ingresos,
            "desglose_gastos": desglose_gastos,
            "totales_ingresos_mes": totales_ingresos_mes,
            "totales_gastos_mes": totales_gastos_mes,
            "resumen_global_meses": resumen_global_meses,
            "total_anual_ingresos": total_anual_ingresos,
            "total_anual_gastos": total_anual_gastos,
            "balance_anual": balance_anual,
            "ratio_ahorro_anual": ratio_ahorro_anual,
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

        cuentas_qs = CuentaAhorro.objects.filter(filtro_cuenta).order_by("nombre")
        cuentas = list(cuentas_qs)

        # Carga masiva de saldos en una sola query para evitar consultas N+1
        saldos_por_cuenta: Dict[int, List["RegistroSaldoMensual"]] = defaultdict(list)
        for reg in RegistroSaldoMensual.objects.filter(cuenta__in=cuentas_qs).order_by("anio", "mes"):
            saldos_por_cuenta[reg.cuenta_id].append(reg)

        filas_cuentas = []
        totales_meses: List[Optional[Decimal]] = [None] * 12
        series_chart_cuentas = []

        total_ahorro_actual = Decimal("0.00")
        total_meta_ahorro = Decimal("0.00")
        tiene_metas = False

        distribucion_labels = []
        distribucion_data = []
        distribucion_colors = []

        for cuenta in cuentas:
            saldos_cuenta = saldos_por_cuenta.get(cuenta.id, [])
            saldos_anio = {s.mes: s for s in saldos_cuenta if s.anio == anio}
            previos = [s for s in saldos_cuenta if s.anio < anio]

            # Saldo a cierre de año anterior para calcular variación
            saldo_anterior_cierre = next((s for s in saldos_cuenta if s.anio == anio - 1 and s.mes == 12), None)
            if not saldo_anterior_cierre and previos:
                saldo_anterior_cierre = previos[-1]  # lista ordenada por (anio, mes)

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
            ultimo_absoluto = saldos_cuenta[-1] if saldos_cuenta else None
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

        # Datos para comparativa con año anterior (1 query agrupada)
        totales_anio_anterior: List[Optional[float]] = []
        if cuentas:
            agrupados_prev = (
                RegistroSaldoMensual.objects.filter(cuenta__in=cuentas, anio=anio - 1)
                .values("mes")
                .annotate(total=Sum("saldo"))
            )
            total_prev_por_mes = {fila["mes"]: fila["total"] for fila in agrupados_prev}
            totales_anio_anterior = [
                float(total_prev_por_mes[m]) if m in total_prev_por_mes else None
                for m in range(1, 13)
            ]
        else:
            totales_anio_anterior = [None] * 12

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
