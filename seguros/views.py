"""Vistas para el módulo de Gestión y Negociación de Seguros."""

from decimal import Decimal
from typing import Any, Dict
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from seguros.forms import HistorialRenovacionSeguroForm, PagoSeguroGastoForm, SeguroForm
from seguros.models import HistorialRenovacionSeguro, Seguro
from seguros.services import SeguroService


class SeguroListView(LoginRequiredMixin, ListView):
    """Listado general de seguros con cálculo agregado e indicadores de vencimiento."""

    model = Seguro
    template_name = "seguros/seguro_list.html"
    context_object_name = "seguros"

    def get_queryset(self) -> Any:
        qs = Seguro.objects.select_related("elemento", "usuario").all()
        ramo = self.request.GET.get("ramo")
        activo = self.request.GET.get("activo")
        if ramo:
            qs = qs.filter(ramo=ramo)
        if activo in ["1", "true", "True"]:
            qs = qs.filter(activo=True)
        elif activo in ["0", "false", "False"]:
            qs = qs.filter(activo=False)
        return qs.order_by("fecha_vencimiento")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        kpis = SeguroService.get_kpis_seguros(qs)

        context.update({
            **kpis,
            "ramos": Seguro.Ramo.choices,
        })
        return context


class SeguroDetailView(LoginRequiredMixin, DetailView):
    """Vista detallada de una póliza con historial, pagos contables reales y panel de negociación."""

    model = Seguro
    template_name = "seguros/seguro_detail.html"
    context_object_name = "seguro"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        seguro = self.object

        hoy = timezone.localdate()
        fecha_def = seguro.fecha_vencimiento if seguro.fecha_vencimiento and seguro.fecha_vencimiento.year == hoy.year else hoy

        context.update({
            "gastos_reales": seguro.get_gastos(),
            "resumen_anual_gastos": SeguroService.get_resumen_gastos_anuales(seguro),
            "historial": seguro.historial.all().order_by("-ejercicio_anio"),
            "form_historial": HistorialRenovacionSeguroForm(),
            "form_pago": PagoSeguroGastoForm(initial={
                "fecha": fecha_def,
                "monto": seguro.prima_actual,
                "concepto": f"Recibo {seguro.compania} ({seguro.bien_asegurado})",
            }),
        })
        return context


class SeguroCreateView(LoginRequiredMixin, CreateView):
    """Alta de una nueva póliza de seguro."""

    model = Seguro
    form_class = SeguroForm
    template_name = "seguros/seguro_form.html"
    success_url = reverse_lazy("seguros:seguro_list")

    def form_valid(self, form: SeguroForm) -> HttpResponse:
        form.instance.usuario = self.request.user
        response = super().form_valid(form)
        self.object.sync_elemento()
        messages.success(self.request, f"Póliza '{self.object.compania} - {self.object.bien_asegurado}' registrada y vinculada a Finanzas con éxito.")
        return response


class SeguroUpdateView(LoginRequiredMixin, UpdateView):
    """Modificación de póliza existente."""

    model = Seguro
    form_class = SeguroForm
    template_name = "seguros/seguro_form.html"
    success_url = reverse_lazy("seguros:seguro_list")

    def form_valid(self, form: SeguroForm) -> HttpResponse:
        response = super().form_valid(form)
        self.object.sync_elemento()
        messages.success(self.request, "Póliza actualizada.")
        return response


class SeguroDeleteView(LoginRequiredMixin, DeleteView):
    """Baja o eliminación de póliza."""

    model = Seguro
    success_url = reverse_lazy("seguros:seguro_list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        seguro = self.get_object()
        elem = seguro.elemento
        # Si el elemento no tiene gastos asociados, podemos eliminarlo para no dejarlo huérfano
        if elem and not elem.gastos.exists():
            elem.delete()
        messages.info(request, "Póliza eliminada.")
        return super().delete(request, *args, **kwargs)


class SeguroRegistrarPagoView(LoginRequiredMixin, View):
    """Registra un pago/recibo de seguro creando un apunte de Gasto contable en Finanzas."""

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        from finanzas.models import Gasto

        seguro = get_object_or_404(Seguro, pk=pk)
        elem = seguro.sync_elemento()

        form = PagoSeguroGastoForm(request.POST)
        if form.is_valid():
            fecha = form.cleaned_data["fecha"]
            monto = form.cleaned_data["monto"]
            concepto = form.cleaned_data["concepto"] or f"Recibo {seguro.compania} ({seguro.bien_asegurado})"
            notas = form.cleaned_data["notas"]

            Gasto.objects.create(
                usuario=request.user,
                elemento=elem,
                concepto=concepto,
                monto=monto,
                fecha=fecha,
                es_fijo=True,
                notas=notas,
            )
            messages.success(
                request,
                f"Pago de {monto}€ registrado correctamente en el Libro Contable ({fecha.strftime('%d/%m/%Y')}).",
            )
        else:
            messages.error(request, "Error al registrar el pago del seguro. Revisa los datos introducidos.")

        return redirect("seguros:seguro_detail", pk=pk)


class HistorialRenovacionCreateView(LoginRequiredMixin, View):
    """Añadir registro histórico de prima a un seguro."""

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        seguro = get_object_or_404(Seguro, pk=pk)
        form = HistorialRenovacionSeguroForm(request.POST)
        if form.is_valid():
            historial = form.save(commit=False)
            historial.seguro = seguro
            historial.save()
            messages.success(request, "Histórico de renovación añadido.")
        else:
            messages.error(request, "Datos de histórico no válidos.")
        return redirect("seguros:seguro_detail", pk=pk)
