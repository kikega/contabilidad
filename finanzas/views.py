"""Vistas y endpoints HTMX para el módulo de Finanzas y Dashboard Principal."""

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from finanzas.forms import (
    CategoriaForm,
    CuentaAhorroForm,
    ElementoForm,
    FiltroFinanzasForm,
    GastoForm,
    IngresoForm,
    RegistroSaldoMensualForm,
)
from finanzas.models import (
    Categoria,
    CuentaAhorro,
    Elemento,
    Gasto,
    Ingreso,
    RegistroSaldoMensual,
)
from finanzas.services import FinanzasService


def _next_url_valida(request: HttpRequest, next_url: Optional[str]) -> Optional[str]:
    """Devuelve el parámetro 'next' solo si es una URL interna segura (evita open redirects)."""
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


def _int_param(
    valor: Optional[str],
    default: Optional[int] = None,
    minimo: Optional[int] = None,
    maximo: Optional[int] = None,
) -> Optional[int]:
    """Convierte un parámetro a entero con valores por defecto y acotación segura."""
    try:
        num = int(valor) if valor not in (None, "") else default
    except (ValueError, TypeError):
        num = default
    if num is None:
        return None
    if minimo is not None and num < minimo:
        num = minimo
    if maximo is not None and num > maximo:
        num = maximo
    return num


class DashboardView(LoginRequiredMixin, TemplateView):
    """Vista principal del Panel de Control Financiero Familiar."""

    template_name = "finanzas/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        anios_disponibles = FinanzasService.get_anios_disponibles()

        # Parámetros GET opcionales para filtrado temporal
        anio_param = self.request.GET.get("anio")
        mes_param = self.request.GET.get("mes")

        if anio_param and anio_param.isdigit():
            anio = int(anio_param)
        elif hoy.year in anios_disponibles:
            anio = hoy.year
        else:
            anio = anios_disponibles[-1] if anios_disponibles else hoy.year

        if anio not in anios_disponibles:
            anios_disponibles.append(anio)
            anios_disponibles.sort()

        mes = _int_param(mes_param, None, 1, 12)

        fecha_inicio, fecha_fin, anio_actual, mes_actual = FinanzasService.get_periodo_fechas(anio, mes)

        kpis = FinanzasService.calcular_kpis(fecha_inicio, fecha_fin)
        graficos_data = FinanzasService.get_datos_graficos_anuales(anio_actual)
        comparativa_anual = FinanzasService.get_comparativa_anual()

        meses_lista = [
            (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
            (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
            (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre")
        ]

        context.update({
            "kpis": kpis,
            "graficos_data": graficos_data,
            "comparativa_anual": comparativa_anual,
            "anio_actual": anio_actual,
            "mes_actual": mes_actual,
            "anios_disponibles": anios_disponibles,
            "meses_lista": meses_lista,
            "filtro_form": FiltroFinanzasForm(),
        })
        return context


class CuentasView(LoginRequiredMixin, TemplateView):
    """Vista general para consultar y auditar el libro contable con matriz anual de 12 meses por categoría."""

    template_name = "finanzas/cuentas.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        anios_disponibles = FinanzasService.get_anios_disponibles()

        anio_param = self.request.GET.get("anio")

        if anio_param and anio_param.isdigit():
            anio = int(anio_param)
        elif hoy.year in anios_disponibles:
            anio = hoy.year
        else:
            anio = anios_disponibles[-1] if anios_disponibles else hoy.year

        if anio not in anios_disponibles:
            anios_disponibles.append(anio)
            anios_disponibles.sort()

        resumen_anual = FinanzasService.get_resumen_cuentas_anual(anio=anio)

        context.update({
            "resumen_anual": resumen_anual,
            "anio_actual": anio,
            "anios_disponibles": anios_disponibles,
        })
        return context


class CuentasMesHtmxView(LoginRequiredMixin, View):
    """Fragmento HTMX que devuelve la matriz anual completa de categorías y apuntes para un año específico."""

    def get(self, request: HttpRequest) -> HttpResponse:
        hoy = timezone.localdate()
        anios_disponibles = FinanzasService.get_anios_disponibles()

        anio_param = request.GET.get("anio")
        if anio_param and anio_param.isdigit():
            anio = int(anio_param)
        elif hoy.year in anios_disponibles:
            anio = hoy.year
        else:
            anio = anios_disponibles[-1] if anios_disponibles else hoy.year

        if anio not in anios_disponibles:
            anios_disponibles.append(anio)
            anios_disponibles.sort()

        resumen_anual = FinanzasService.get_resumen_cuentas_anual(anio=anio)

        return render(
            request,
            "finanzas/partials/cuentas_anual.html",
            {
                "resumen_anual": resumen_anual,
                "anio_actual": anio,
                "anios_disponibles": anios_disponibles,
            },
        )


class ElementoMesDetalleHtmxView(LoginRequiredMixin, View):
    """Devuelve el modal interactivo con los apuntes detallados de un elemento en un mes y año concretos."""

    def get(self, request: HttpRequest) -> HttpResponse:
        hoy = timezone.localdate()
        elemento_id = request.GET.get("elemento_id")
        anio = _int_param(request.GET.get("anio"), hoy.year) or hoy.year
        mes = _int_param(request.GET.get("mes"), hoy.month, 1, 12) or hoy.month
        tipo = request.GET.get("tipo", "gasto").lower()

        elemento = get_object_or_404(Elemento.objects.select_related("categoria"), id=elemento_id)

        meses_nombres = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        nombre_mes = meses_nombres[mes - 1]

        inicio_mes = date(anio, mes, 1)
        fin_mes = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)

        if tipo == "ingreso":
            items = Ingreso.objects.filter(
                elemento=elemento,
                fecha__gte=inicio_mes,
                fecha__lt=fin_mes,
            ).select_related("usuario").order_by("fecha")
            total_mes = sum((item.monto for item in items), Decimal("0.00"))
        else:
            items = Gasto.objects.filter(
                elemento=elemento,
                fecha__gte=inicio_mes,
                fecha__lt=fin_mes,
            ).select_related("usuario").order_by("fecha")
            total_mes = sum((item.monto for item in items), Decimal("0.00"))

        fecha_sugerida = f"{anio:04d}-{mes:02d}-01"

        return render(
            request,
            "finanzas/partials/elemento_mes_detalle_modal.html",
            {
                "elemento": elemento,
                "items": items,
                "total_mes": total_mes,
                "anio": anio,
                "mes": mes,
                "nombre_mes": nombre_mes,
                "tipo": tipo,
                "fecha_sugerida": fecha_sugerida,
            },
        )


class TransaccionesTablaHtmxView(LoginRequiredMixin, View):
    """Renderizado parcial vía HTMX para la tabla interactiva de movimientos."""

    def get(self, request: HttpRequest) -> HttpResponse:
        hoy = timezone.localdate()
        anio = _int_param(request.GET.get("anio"), hoy.year) or hoy.year
        mes_param = request.GET.get("mes")
        mes = _int_param(mes_param, None, 1, 12)
        tipo = request.GET.get("tipo", "TODOS")
        busqueda = request.GET.get("q", "").strip()

        inicio, fin, _, _ = FinanzasService.get_periodo_fechas(anio, mes)

        movimientos = []

        if tipo in ["TODOS", "INGRESO"]:
            qs_ing = Ingreso.objects.filter(fecha__gte=inicio, fecha__lt=fin).select_related("elemento__categoria", "usuario")
            if busqueda:
                qs_ing = qs_ing.filter(descripcion__icontains=busqueda)
            for ing in qs_ing:
                elem_nom = ing.elemento.nombre if ing.elemento else (ing.descripcion or "Ingreso")
                cat_nom = ing.elemento.categoria.nombre if (ing.elemento and ing.elemento.categoria) else "Ingresos"
                cat_col = ing.elemento.categoria.color if (ing.elemento and ing.elemento.categoria) else "#3BB8DB"

                movimientos.append({
                    "id": ing.id,
                    "tipo": "INGRESO",
                    "fecha": ing.fecha,
                    "concepto": ing.descripcion or elem_nom,
                    "elemento": elem_nom,
                    "categoria": cat_nom,
                    "categoria_color": cat_col,
                    "monto": ing.monto,
                    "usuario": ing.usuario.get_short_name() if ing.usuario else "-",
                    "es_positivo": True,
                    "edit_url": f"/finanzas/ingresos/{ing.id}/editar/",
                    "delete_url": f"/finanzas/ingresos/{ing.id}/eliminar/",
                })

        if tipo in ["TODOS", "GASTO"]:
            qs_gas = Gasto.objects.filter(fecha__gte=inicio, fecha__lt=fin).select_related("elemento__categoria", "usuario")
            if busqueda:
                qs_gas = qs_gas.filter(concepto__icontains=busqueda)
            for gas in qs_gas:
                elem_nom = gas.elemento.nombre if gas.elemento else gas.concepto
                cat_nom = gas.elemento.categoria.nombre if (gas.elemento and gas.elemento.categoria) else "Gastos"
                cat_col = gas.elemento.categoria.color if (gas.elemento and gas.elemento.categoria) else "#015F78"

                movimientos.append({
                    "id": gas.id,
                    "tipo": "GASTO",
                    "fecha": gas.fecha,
                    "concepto": gas.concepto,
                    "elemento": elem_nom,
                    "categoria": cat_nom,
                    "categoria_color": cat_col,
                    "monto": gas.monto,
                    "usuario": gas.usuario.get_short_name() if gas.usuario else "-",
                    "es_positivo": False,
                    "edit_url": f"/finanzas/gastos/{gas.id}/editar/",
                    "delete_url": f"/finanzas/gastos/{gas.id}/eliminar/",
                })

        movimientos.sort(key=lambda x: x["fecha"], reverse=True)

        paginator = Paginator(movimientos, 10)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        return render(
            request,
            "finanzas/partials/tabla_transacciones.html",
            {
                "page_obj": page_obj,
                "tipo": tipo,
                "anio": anio,
                "mes": mes_param or "",
            },
        )


class GraficosDataApiView(LoginRequiredMixin, View):
    """Endpoint que suministra datos estructurados JSON para refresco de gráficos."""

    def get(self, request: HttpRequest) -> JsonResponse:
        hoy = timezone.localdate()
        anio = _int_param(request.GET.get("anio"), hoy.year) or hoy.year
        datos = FinanzasService.get_datos_graficos_anuales(anio)
        return JsonResponse(datos)


# ==============================================================================
# CRUD INGRESOS
# ==============================================================================

class IngresoCreateView(LoginRequiredMixin, CreateView):
    """Creación de un nuevo ingreso con soporte para HTMX y formulario tradicional."""

    model = Ingreso
    form_class = IngresoForm
    template_name = "finanzas/ingreso_form.html"
    success_url = reverse_lazy("finanzas:dashboard")

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()
        elem_id = self.request.GET.get("elemento")
        cat_id = self.request.GET.get("categoria")
        if elem_id:
            initial["elemento"] = elem_id
        elif cat_id:
            elem = Elemento.objects.filter(categoria_id=cat_id).first()
            if elem:
                initial["elemento"] = elem.id
        return initial

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return _next_url_valida(self.request, next_url) or reverse_lazy("finanzas:cuentas")

    def form_valid(self, form: IngresoForm) -> HttpResponse:
        form.instance.usuario = self.request.user
        messages.success(self.request, "Ingreso registrado correctamente.")
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        return response


class IngresoUpdateView(LoginRequiredMixin, UpdateView):
    """Edición de un ingreso existente."""

    model = Ingreso
    form_class = IngresoForm
    template_name = "finanzas/ingreso_form.html"
    success_url = reverse_lazy("finanzas:cuentas")

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return _next_url_valida(self.request, next_url) or reverse_lazy("finanzas:cuentas")

    def form_valid(self, form: IngresoForm) -> HttpResponse:
        messages.success(self.request, "Ingreso actualizado correctamente.")
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        return response


class IngresoDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminación de un ingreso registrado."""

    model = Ingreso
    success_url = reverse_lazy("finanzas:cuentas")

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return _next_url_valida(self.request, next_url) or reverse_lazy("finanzas:cuentas")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.info(request, "Ingreso eliminado.")
        response = super().delete(request, *args, **kwargs)
        if request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        return response


# ==============================================================================
# CRUD GASTOS
# ==============================================================================

class GastoFormContextMixin:
    """Expone el mapa categoría->elementos y las categorías de tarjetas para el desplegable dependiente."""

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        categorias = list(FinanzasService.get_categorias_gasto_queryset())
        elementos_por_categoria: Dict[str, list] = {}
        for elem in (
            Elemento.objects.filter(categoria__tipo=Categoria.Tipo.GASTO, finalizado=False)
            .select_related("categoria")
            .order_by("categoria__nombre", "nombre")
        ):
            elementos_por_categoria.setdefault(str(elem.categoria_id), []).append(
                {"id": elem.id, "nombre": elem.nombre, "es_fijo": elem.es_fijo}
            )
        context["gasto_config"] = {
            "elementos_por_categoria": elementos_por_categoria,
            "categorias_tarjeta": [c.id for c in categorias if "tarjeta" in c.nombre.lower()],
        }
        return context


class GastoCreateView(LoginRequiredMixin, GastoFormContextMixin, CreateView):
    """Registro de un nuevo gasto."""

    model = Gasto
    form_class = GastoForm
    template_name = "finanzas/gasto_form.html"
    success_url = reverse_lazy("finanzas:dashboard")

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()
        elem_id = self.request.GET.get("elemento")
        cat_id = self.request.GET.get("categoria")
        if cat_id:
            initial["categoria"] = cat_id
        if elem_id:
            elem = Elemento.objects.select_related("categoria").filter(id=elem_id).first()
            if elem:
                initial["elemento"] = elem.id
                initial["categoria"] = elem.categoria_id
        elif cat_id:
            elem = Elemento.objects.filter(categoria_id=cat_id).first()
            if elem:
                initial["elemento"] = elem.id
        return initial

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return _next_url_valida(self.request, next_url) or reverse_lazy("finanzas:cuentas")

    def form_valid(self, form: GastoForm) -> HttpResponse:
        form.instance.usuario = self.request.user
        messages.success(self.request, "Gasto registrado correctamente.")
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        return response


class GastoUpdateView(LoginRequiredMixin, GastoFormContextMixin, UpdateView):
    """Edición de un gasto."""

    model = Gasto
    form_class = GastoForm
    template_name = "finanzas/gasto_form.html"
    success_url = reverse_lazy("finanzas:cuentas")

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()
        if self.object and self.object.elemento_id:
            initial["categoria"] = self.object.elemento.categoria_id
        return initial

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return _next_url_valida(self.request, next_url) or reverse_lazy("finanzas:cuentas")

    def form_valid(self, form: GastoForm) -> HttpResponse:
        messages.success(self.request, "Gasto modificado correctamente.")
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        return response


class GastoDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminación de un gasto."""

    model = Gasto
    success_url = reverse_lazy("finanzas:cuentas")

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        return _next_url_valida(self.request, next_url) or reverse_lazy("finanzas:cuentas")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.info(request, "Gasto eliminado.")
        response = super().delete(request, *args, **kwargs)
        if request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        return response


# ==============================================================================
# ADMINISTRACIÓN Y GESTIÓN DE CATEGORÍAS & ELEMENTOS
# ==============================================================================

class AdministracionView(LoginRequiredMixin, TemplateView):
    """Panel de administración y configuración de categorías, elementos, seguros y miembros."""

    template_name = "finanzas/administracion.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model
        from seguros.models import Seguro

        Usuario = get_user_model()

        # Categorías organizadas con prefetch de elementos y apuntes
        categorias_ingreso = (
            Categoria.objects.filter(tipo=Categoria.Tipo.INGRESO)
            .prefetch_related(
                Prefetch("elementos", queryset=Elemento.objects.prefetch_related("ingresos").order_by("nombre"))
            )
            .order_by("nombre")
        )
        categorias_gasto = FinanzasService.get_categorias_gasto_queryset(
            elementos_prefetch=Prefetch(
                "elementos",
                queryset=Elemento.objects.prefetch_related(
                    Prefetch("gastos", queryset=Gasto.objects.select_related("usuario").order_by("-fecha", "-id"))
                ).order_by("nombre"),
            )
        )
        categorias_tarjeta = Categoria.objects.filter(tipo=Categoria.Tipo.ESPECIAL_TARJETA).order_by("nombre")

        seguros = Seguro.objects.all().order_by("fecha_vencimiento")
        usuarios = Usuario.objects.all().order_by("-is_staff", "email")

        context.update({
            "categorias_ingreso": categorias_ingreso,
            "categorias_gasto": categorias_gasto,
            "categorias_tarjeta": categorias_tarjeta,
            "total_categorias": Categoria.objects.count(),
            "total_elementos": Elemento.objects.count(),
            "seguros": seguros,
            "usuarios": usuarios,
            "form_categoria": CategoriaForm(),
            "form_elemento": ElementoForm(),
        })
        return context


class CategoriaCreateView(LoginRequiredMixin, CreateView):
    """Creación de una nueva categoría."""

    model = Categoria
    form_class = CategoriaForm
    template_name = "finanzas/categoria_form.html"
    success_url = reverse_lazy("finanzas:administracion")

    def form_valid(self, form: CategoriaForm) -> HttpResponse:
        messages.success(self.request, f"Categoría '{form.instance.nombre}' creada con éxito.")
        return super().form_valid(form)


class CategoriaUpdateView(LoginRequiredMixin, UpdateView):
    """Edición de categoría existente."""

    model = Categoria
    form_class = CategoriaForm
    template_name = "finanzas/categoria_form.html"
    success_url = reverse_lazy("finanzas:administracion")

    def form_valid(self, form: CategoriaForm) -> HttpResponse:
        messages.success(self.request, f"Categoría '{form.instance.nombre}' actualizada.")
        return super().form_valid(form)


class CategoriaDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminación de una categoría."""

    model = Categoria
    template_name = "finanzas/categoria_confirm_delete.html"
    success_url = reverse_lazy("finanzas:administracion")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        categoria = self.get_object()
        tiene_elementos = categoria.elementos.exists()

        if tiene_elementos:
            messages.error(
                request,
                f"No se puede eliminar la categoría '{categoria.nombre}' porque contiene elementos vinculados.",
            )
            return redirect("finanzas:administracion")

        messages.info(request, f"Categoría '{categoria.nombre}' eliminada.")
        return super().delete(request, *args, **kwargs)


# ==============================================================================
# CRUD ELEMENTOS
# ==============================================================================

class ElementoCreateView(LoginRequiredMixin, CreateView):
    """Creación de un nuevo elemento/concepto en una categoría."""

    model = Elemento
    form_class = ElementoForm
    template_name = "finanzas/elemento_form.html"
    success_url = reverse_lazy("finanzas:administracion")

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()
        cat_id = self.request.GET.get("categoria")
        if cat_id:
            initial["categoria"] = cat_id
        return initial

    def form_valid(self, form: ElementoForm) -> HttpResponse:
        messages.success(self.request, f"Elemento '{form.instance.nombre}' creado en '{form.instance.categoria.nombre}'.")
        return super().form_valid(form)


class ElementoUpdateView(LoginRequiredMixin, UpdateView):
    """Edición de un elemento."""

    model = Elemento
    form_class = ElementoForm
    template_name = "finanzas/elemento_form.html"
    success_url = reverse_lazy("finanzas:administracion")

    def form_valid(self, form: ElementoForm) -> HttpResponse:
        messages.success(self.request, f"Elemento '{form.instance.nombre}' actualizado.")
        return super().form_valid(form)


class ElementoDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminación de un elemento."""

    model = Elemento
    template_name = "finanzas/elemento_confirm_delete.html"
    success_url = reverse_lazy("finanzas:administracion")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        elemento = self.get_object()
        tiene_gastos = elemento.gastos.exists()
        tiene_ingresos = elemento.ingresos.exists()

        if tiene_gastos or tiene_ingresos:
            messages.error(
                request,
                f"No se puede eliminar el elemento '{elemento.nombre}' porque contiene apuntes registrados.",
            )
            return redirect("finanzas:administracion")

        messages.info(request, f"Elemento '{elemento.nombre}' eliminado.")
        return super().delete(request, *args, **kwargs)


# ==============================================================================
# VISTAS DE CUENTAS DE AHORRO Y REGISTRO DE SALDOS MENSUALES
# ==============================================================================


class AhorrosListView(LoginRequiredMixin, TemplateView):
    """Vista principal de Cuentas de Ahorro con matriz anual y evolución estadística."""

    template_name = "finanzas/ahorros.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()

        anio = _int_param(self.request.GET.get("anio"), hoy.year) or hoy.year

        anios_disponibles = FinanzasService.get_anios_disponibles()
        if anio not in anios_disponibles:
            anios_disponibles.append(anio)
            anios_disponibles.sort()

        resumen_ahorros = FinanzasService.get_resumen_ahorros_anual(anio=anio)

        context["anio_actual"] = anio
        context["anios_disponibles"] = anios_disponibles
        context["resumen"] = resumen_ahorros
        context["cuentas_activas"] = CuentaAhorro.objects.filter(activo=True).order_by("nombre")
        context["form_cuenta"] = CuentaAhorroForm()
        context["graficos"] = resumen_ahorros["graficos"]
        return context


class GuardarSaldoMensualHtmxView(LoginRequiredMixin, View):
    """Guarda o actualiza de forma instantánea con HTMX el saldo de un mes concreto con validación estricta."""

    def post(self, request: HttpRequest) -> HttpResponse:
        hoy = timezone.localdate()
        cuenta_id = _int_param(request.POST.get("cuenta_id"))
        anio = _int_param(request.POST.get("anio"), hoy.year) or hoy.year
        mes = _int_param(request.POST.get("mes"), hoy.month, 1, 12) or hoy.month
        saldo_str = request.POST.get("saldo", "").replace(",", ".").strip()
        notas = request.POST.get("notas", "").strip()

        if cuenta_id:
            try:
                cuenta = get_object_or_404(CuentaAhorro, id=cuenta_id)

                if saldo_str == "":
                    # Si se deja en blanco, eliminar el registro
                    RegistroSaldoMensual.objects.filter(cuenta=cuenta, anio=anio, mes=mes).delete()
                else:
                    saldo_dec = Decimal(saldo_str)
                    if saldo_dec >= Decimal("0.00"):
                        RegistroSaldoMensual.objects.update_or_create(
                            cuenta=cuenta,
                            anio=anio,
                            mes=mes,
                            defaults={"saldo": saldo_dec, "notas": notas},
                        )
            except (ValueError, TypeError, InvalidOperation):
                pass

        resumen_ahorros = FinanzasService.get_resumen_ahorros_anual(anio=anio)
        response = render(
            request,
            "finanzas/partials/matriz_ahorros.html",
            {
                "resumen": resumen_ahorros,
                "anio_actual": anio,
            },
        )
        response["HX-Trigger"] = json.dumps({"actualizarGraficos": resumen_ahorros["graficos"]})
        return response


class CuentaAhorroCreateView(LoginRequiredMixin, CreateView):
    """Creación de una nueva cuenta, hucha o depósito de ahorro."""

    model = CuentaAhorro
    form_class = CuentaAhorroForm
    template_name = "finanzas/cuenta_ahorro_form.html"
    success_url = reverse_lazy("finanzas:ahorros")

    def form_valid(self, form: CuentaAhorroForm) -> HttpResponse:
        form.instance.usuario = self.request.user
        messages.success(self.request, f"Cuenta de ahorro '{form.instance.nombre}' creada con éxito.")
        return super().form_valid(form)


class CuentaAhorroUpdateView(LoginRequiredMixin, UpdateView):
    """Edición de una cuenta de ahorro existente."""

    model = CuentaAhorro
    form_class = CuentaAhorroForm
    template_name = "finanzas/cuenta_ahorro_form.html"
    success_url = reverse_lazy("finanzas:ahorros")

    def form_valid(self, form: CuentaAhorroForm) -> HttpResponse:
        messages.success(self.request, f"Cuenta de ahorro '{form.instance.nombre}' actualizada.")
        return super().form_valid(form)


class CuentaAhorroDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminación de una cuenta de ahorro."""

    model = CuentaAhorro
    template_name = "finanzas/cuenta_ahorro_confirm_delete.html"
    success_url = reverse_lazy("finanzas:ahorros")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        cuenta = self.get_object()
        nombre = cuenta.nombre
        cuenta.delete()
        messages.info(request, f"Cuenta de ahorro '{nombre}' y sus registros históricos eliminados.")
        return redirect("finanzas:ahorros")

