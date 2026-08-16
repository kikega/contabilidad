"""Vistas para el módulo de Gestión y Negociación de Seguros."""

from decimal import Decimal
from typing import Any, Dict
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from seguros.forms import HistorialRenovacionSeguroForm, SeguroForm
from seguros.models import HistorialRenovacionSeguro, Seguro


class SeguroListView(LoginRequiredMixin, ListView):
    """Listado general de seguros con cálculo agregado e indicadores de vencimiento."""

    model = Seguro
    template_name = "seguros/seguro_list.html"
    context_object_name = "seguros"

    def get_queryset(self) -> Any:
        qs = Seguro.objects.all()
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
        
        coste_total_anual = qs.filter(activo=True).aggregate(
            total=Sum("prima_actual")
        )["total"] or Decimal("0.00")

        # Conteo de seguros por estado
        urgentes = [s for s in qs if s.activo and s.estado_vencimiento == "urgente"]
        proximos = [s for s in qs if s.activo and s.estado_vencimiento == "proximo"]

        context.update({
            "coste_total_anual": coste_total_anual,
            "num_polizas": qs.filter(activo=True).count(),
            "urgentes_count": len(urgentes),
            "proximos_count": len(proximos),
            "ramos": Seguro.Ramo.choices,
        })
        return context


class SeguroDetailView(LoginRequiredMixin, DetailView):
    """Vista detallada de una póliza con historial y panel de negociación."""

    model = Seguro
    template_name = "seguros/seguro_detail.html"
    context_object_name = "seguro"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["historial"] = self.object.historial.all().order_by("-ejercicio_anio")
        context["form_historial"] = HistorialRenovacionSeguroForm()
        return context


class SeguroCreateView(LoginRequiredMixin, CreateView):
    """Alta de una nueva póliza de seguro."""

    model = Seguro
    form_class = SeguroForm
    template_name = "seguros/seguro_form.html"
    success_url = reverse_lazy("seguros:seguro_list")

    def form_valid(self, form: SeguroForm) -> HttpResponse:
        form.instance.usuario = self.request.user
        messages.success(self.request, "Póliza registrada con éxito.")
        return super().form_valid(form)


class SeguroUpdateView(LoginRequiredMixin, UpdateView):
    """Modificación de póliza existente."""

    model = Seguro
    form_class = SeguroForm
    template_name = "seguros/seguro_form.html"
    success_url = reverse_lazy("seguros:seguro_list")

    def form_valid(self, form: SeguroForm) -> HttpResponse:
        messages.success(self.request, "Póliza actualizada.")
        return super().form_valid(form)


class SeguroDeleteView(LoginRequiredMixin, DeleteView):
    """Baja o eliminación de póliza."""

    model = Seguro
    success_url = reverse_lazy("seguros:seguro_list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.info(request, "Póliza eliminada.")
        return super().delete(request, *args, **kwargs)


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
