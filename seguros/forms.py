"""Formularios para la gestión y negociación de pólizas de seguro."""

from decimal import Decimal
from typing import Any
from django import forms
from django.utils.translation import gettext_lazy as _

from seguros.models import HistorialRenovacionSeguro, Seguro

INPUT_CLASSES = (
    "w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 "
    "bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 "
    "focus:ring-2 focus:ring-cyan-500 focus:outline-none transition-all placeholder:text-slate-400"
)
SELECT_CLASSES = (
    "w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 "
    "bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 "
    "focus:ring-2 focus:ring-cyan-500 focus:outline-none transition-all"
)
CHECKBOX_CLASSES = (
    "rounded border-slate-300 dark:border-slate-700 text-cyan-600 "
    "focus:ring-cyan-500 h-4 w-4 bg-white dark:bg-slate-800"
)


class SeguroForm(forms.ModelForm):
    """Formulario para creación y edición de pólizas familiares."""

    class Meta:
        model = Seguro
        fields = [
            "ramo",
            "compania",
            "numero_poliza",
            "bien_asegurado",
            "gestor_nombre",
            "gestor_telefono",
            "gestor_email",
            "fecha_inicio",
            "fecha_vencimiento",
            "periodicidad",
            "prima_actual",
            "prima_anterior",
            "activo",
            "notas_negociacion",
        ]
        widgets = {
            "ramo": forms.Select(attrs={"class": SELECT_CLASSES}),
            "compania": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Ej: Mapfre, Allianz, Axa..."}),
            "numero_poliza": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Nº de Póliza"}),
            "bien_asegurado": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: Vivienda Principal, Coche Familiar..."}
            ),
            "gestor_nombre": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Nombre del gestor/mediador"}),
            "gestor_telefono": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Teléfono de contacto"}),
            "gestor_email": forms.EmailInput(attrs={"class": INPUT_CLASSES, "placeholder": "correo@agencia.com"}),
            "fecha_inicio": forms.DateInput(attrs={"class": INPUT_CLASSES, "type": "date"}),
            "fecha_vencimiento": forms.DateInput(attrs={"class": INPUT_CLASSES, "type": "date"}),
            "periodicidad": forms.Select(attrs={"class": SELECT_CLASSES}),
            "prima_actual": forms.NumberInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "0.00", "step": "0.01", "min": "0.01"}
            ),
            "prima_anterior": forms.NumberInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "0.00", "step": "0.01", "min": "0.00"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
            "notas_negociacion": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES,
                    "rows": 4,
                    "placeholder": "Condiciones acordadas, coberturas, histórico de ofertas y estrategia...",
                }
            ),
        }


class HistorialRenovacionSeguroForm(forms.ModelForm):
    """Formulario para registrar renovaciones anuales pasadas."""

    class Meta:
        model = HistorialRenovacionSeguro
        fields = ["ejercicio_anio", "prima_pagada", "fecha_renovacion", "notas"]
        widgets = {
            "ejercicio_anio": forms.NumberInput(attrs={"class": INPUT_CLASSES, "placeholder": "Año (ej: 2025)"}),
            "prima_pagada": forms.NumberInput(attrs={"class": INPUT_CLASSES, "placeholder": "0.00", "step": "0.01"}),
            "fecha_renovacion": forms.DateInput(attrs={"class": INPUT_CLASSES, "type": "date"}),
            "notas": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Observaciones de la renovación"}),
        }
