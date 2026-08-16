"""Formularios para el registro y filtrado de movimientos financieros."""

from decimal import Decimal
from typing import Any
from django import forms
from django.utils.translation import gettext_lazy as _

from finanzas.models import Categoria, Elemento, Gasto, GastoEspecialTarjeta, Ingreso

# Estilos base para inputs con Tailwind CSS y soporte de Dark Mode
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


class CategoriaForm(forms.ModelForm):
    """Formulario para la creación y edición de macro-categorías (ej: Gastos Casa, Vehículos...)."""

    class Meta:
        model = Categoria
        fields = ["nombre", "tipo", "icono", "color", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: Gastos Casa, Vehículos & Movilidad..."}
            ),
            "tipo": forms.Select(attrs={"class": SELECT_CLASSES}),
            "icono": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: home, car, heart-pulse, shopping-cart, wallet..."}
            ),
            "color": forms.TextInput(
                attrs={"class": "h-10 w-full p-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 cursor-pointer", "type": "color"}
            ),
            "descripcion": forms.Textarea(
                attrs={"class": INPUT_CLASSES, "rows": 2, "placeholder": "Descripción u observaciones de la categoría..."}
            ),
        }


class ElementoForm(forms.ModelForm):
    """Formulario para la creación y edición de elementos pertenecientes a una categoría."""

    class Meta:
        model = Elemento
        fields = ["categoria", "nombre", "es_fijo", "icono", "descripcion"]
        widgets = {
            "categoria": forms.Select(attrs={"class": SELECT_CLASSES}),
            "nombre": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: Electricidad, Agua, Comunidad propietarios, Gasolina..."}
            ),
            "es_fijo": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
            "icono": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Opcional (hereda de categoría si está vacío)"}
            ),
            "descripcion": forms.Textarea(
                attrs={"class": INPUT_CLASSES, "rows": 2, "placeholder": "Observaciones del elemento..."}
            ),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        tipo = kwargs.pop("tipo", None)
        super().__init__(*args, **kwargs)
        if tipo:
            self.fields["categoria"].queryset = Categoria.objects.filter(tipo=tipo)


class IngresoForm(forms.ModelForm):
    """Formulario para la creación y edición de ingresos familiares."""

    class Meta:
        model = Ingreso
        fields = ["elemento", "monto", "fecha", "descripcion", "notas"]
        widgets = {
            "elemento": forms.Select(attrs={"class": SELECT_CLASSES}),
            "monto": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "fecha": forms.DateInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "type": "date",
                }
            ),
            "descripcion": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Concepto o detalle opcional (ej: Nómina mensual, Dividendo Q1...)",
                }
            ),
            "notas": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES,
                    "rows": 3,
                    "placeholder": "Observaciones opcionales...",
                }
            ),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["elemento"].queryset = Elemento.objects.filter(
            categoria__tipo=Categoria.Tipo.INGRESO
        ).select_related("categoria").order_by("categoria__nombre", "nombre")


class GastoForm(forms.ModelForm):
    """Formulario para el registro de gastos periódicos vinculados a un elemento."""

    class Meta:
        model = Gasto
        fields = ["concepto", "elemento", "monto", "fecha", "es_fijo", "notas"]
        widgets = {
            "concepto": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Ej: Factura luz Iberdrola, Cuota comunidad T1, Gasolina viaje...",
                }
            ),
            "elemento": forms.Select(attrs={"class": SELECT_CLASSES}),
            "monto": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "fecha": forms.DateInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "type": "date",
                }
            ),
            "es_fijo": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
            "notas": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES,
                    "rows": 3,
                    "placeholder": "Detalles adicionales del gasto...",
                }
            ),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["elemento"].queryset = Elemento.objects.filter(
            categoria__tipo=Categoria.Tipo.GASTO
        ).select_related("categoria").order_by("categoria__nombre", "nombre")


class GastoEspecialTarjetaForm(forms.ModelForm):
    """Formulario para el desglose y auditoría de compras individuales con tarjeta."""

    class Meta:
        model = GastoEspecialTarjeta
        fields = ["tarjeta", "tipo_comercio", "comercio", "monto", "fecha", "notas"]
        widgets = {
            "tarjeta": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Ej: Visa Oro Titular 1, Mastercard Hogar...",
                }
            ),
            "tipo_comercio": forms.Select(attrs={"class": SELECT_CLASSES}),
            "comercio": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Ej: Mercadona, Carrefour, Restaurante El Rincón...",
                }
            ),
            "monto": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "fecha": forms.DateInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "type": "date",
                }
            ),
            "notas": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES,
                    "rows": 3,
                    "placeholder": "Detalles de la compra...",
                }
            ),
        }


class FiltroFinanzasForm(forms.Form):
    """Formulario para la barra de filtros interactiva con HTMX."""

    TIPO_CHOICES = [
        ("TODOS", _("Todos los movimientos")),
        ("INGRESO", _("Sólo Ingresos")),
        ("GASTO", _("Sólo Gastos")),
    ]

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": SELECT_CLASSES}),
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all().order_by("tipo", "nombre"),
        required=False,
        empty_label=_("Todas las categorías"),
        widget=forms.Select(attrs={"class": SELECT_CLASSES}),
    )
    elemento = forms.ModelChoiceField(
        queryset=Elemento.objects.all().select_related("categoria").order_by("categoria__nombre", "nombre"),
        required=False,
        empty_label=_("Todos los elementos"),
        widget=forms.Select(attrs={"class": SELECT_CLASSES}),
    )
    busqueda = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Buscar concepto, comercio, notas...",
            }
        ),
    )


class CuentaAhorroForm(forms.ModelForm):
    """Formulario para crear y editar cuentas, fondos o huchas de ahorro."""

    class Meta:
        from finanzas.models import CuentaAhorro
        model = CuentaAhorro
        fields = [
            "nombre",
            "entidad",
            "tipo",
            "color",
            "icono",
            "numero_cuenta_iban",
            "objetivo_monto",
            "activo",
            "notas",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: Fondo de Emergencia, Ahorro Vacaciones..."}
            ),
            "entidad": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: MyInvestor, Trade Republic, Santander, Openbank..."}
            ),
            "tipo": forms.Select(attrs={"class": SELECT_CLASSES}),
            "color": forms.TextInput(
                attrs={"class": "h-10 w-full p-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 cursor-pointer", "type": "color"}
            ),
            "icono": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: piggy-bank, landmark, trending-up, wallet, vault..."}
            ),
            "numero_cuenta_iban": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "ES00 0000 0000 0000 0000 (opcional)"}
            ),
            "objetivo_monto": forms.NumberInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Meta en € (opcional)", "step": "0.01", "min": "0.00"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
            "notas": forms.Textarea(
                attrs={"class": INPUT_CLASSES, "rows": 3, "placeholder": "Condiciones, rentabilidad % o notas de la cuenta..."}
            ),
        }


class RegistroSaldoMensualForm(forms.Form):
    """Formulario para registrar o actualizar el saldo de un mes concreto."""

    cuenta_id = forms.IntegerField(widget=forms.HiddenInput())
    anio = forms.IntegerField(widget=forms.HiddenInput())
    mes = forms.IntegerField(widget=forms.HiddenInput())
    saldo = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "w-28 text-right px-2 py-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-bold text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:outline-none", "step": "0.01", "min": "0.00"}
        ),
    )
    notas = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "Notas del mes (opcional)"}
        ),
    )

