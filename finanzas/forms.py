"""Formularios para el registro y filtrado de movimientos financieros."""

from decimal import Decimal
from typing import Any, Dict
from django import forms
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from finanzas.models import Categoria, Elemento, Gasto, Ingreso

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
DATEPICKER_CLASSES = (
    "w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 "
    "bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 "
    "focus:ring-2 focus:ring-cyan-500 focus:outline-none transition-all placeholder:text-slate-400 "
    "datepicker"
)
DATE_INPUT_FORMATS = [
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%Y-%m-%d",
]


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
        fields = ["categoria", "nombre", "es_fijo", "finalizado", "fecha_finalizacion", "icono", "descripcion"]
        widgets = {
            "categoria": forms.Select(attrs={"class": SELECT_CLASSES}),
            "nombre": forms.TextInput(
                attrs={"class": INPUT_CLASSES, "placeholder": "Ej: Electricidad, Agua, Comunidad propietarios, Gasolina..."}
            ),
            "es_fijo": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
            "finalizado": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
            "fecha_finalizacion": forms.DateInput(
                format="%d/%m/%Y",
                attrs={"class": DATEPICKER_CLASSES, "placeholder": "dd/mm/aaaa", "autocomplete": "off"},
            ),
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
        if "fecha_finalizacion" in self.fields:
            self.fields["fecha_finalizacion"].input_formats = DATE_INPUT_FORMATS
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
                format="%d/%m/%Y",
                attrs={
                    "class": DATEPICKER_CLASSES,
                    "placeholder": "dd/mm/aaaa",
                    "autocomplete": "off",
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
        if "fecha" in self.fields:
            self.fields["fecha"].input_formats = DATE_INPUT_FORMATS
        self.fields["elemento"].queryset = Elemento.objects.filter(
            categoria__tipo=Categoria.Tipo.INGRESO
        ).select_related("categoria").order_by("categoria__nombre", "nombre")


class GastoForm(forms.ModelForm):
    """Formulario para el registro de gastos periódicos vinculados a un elemento.

    Incluye un selector de categoría que filtra los elementos disponibles y, en la
    categoría de tarjetas, el concepto se genera automáticamente (liquidación del
    mes anterior que se paga el día 1 del mes siguiente).
    """

    categoria = forms.ModelChoiceField(
        label=_("Categoría de gasto"),
        queryset=Categoria.objects.none(),
        widget=forms.Select(attrs={"class": SELECT_CLASSES}),
    )
    concepto = forms.CharField(
        label=_("Concepto del apunte"),
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: Factura luz Iberdrola, Cuota comunidad T1, Gasolina viaje...",
            }
        ),
    )

    class Meta:
        model = Gasto
        fields = ["categoria", "concepto", "elemento", "monto", "fecha", "es_fijo", "notas"]
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
                format="%d/%m/%Y",
                attrs={
                    "class": DATEPICKER_CLASSES,
                    "placeholder": "dd/mm/aaaa",
                    "autocomplete": "off",
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
        if "fecha" in self.fields:
            self.fields["fecha"].input_formats = DATE_INPUT_FORMATS
        from finanzas.services import FinanzasService

        self.fields["categoria"].queryset = FinanzasService.get_categorias_gasto_queryset()

        cat_id = self.data.get("categoria") if self.data else None
        if cat_id is None:
            cat_id = self.initial.get("categoria")

        # Los elementos finalizados no deben poder usarse para nuevos gastos,
        # salvo el elemento ya asociado cuando se edita un gasto existente.
        ids_extra: list = []
        if self.instance and self.instance.pk and self.instance.elemento_id:
            ids_extra = [self.instance.elemento_id]

        qs = Elemento.objects.filter(
            Q(categoria__tipo=Categoria.Tipo.GASTO) & (Q(finalizado=False) | Q(pk__in=ids_extra))
        ).select_related("categoria")
        if cat_id:
            qs = qs.filter(categoria_id=cat_id)
        self.fields["elemento"].queryset = qs.order_by("categoria__nombre", "nombre")

        # Si el elemento seleccionado ya es un compromiso recurrente (es_fijo),
        # el gasto se marca como fijo automáticamente: no hace falta preguntarlo.
        if not (self.instance and self.instance.pk):
            elem_id = self.data.get("elemento") if self.data else None
            if not elem_id:
                elem_id = self.initial.get("elemento")
                if hasattr(elem_id, "pk"):
                    elem_id = elem_id.pk
            if elem_id and Elemento.objects.filter(id=elem_id, es_fijo=True).exists():
                self.fields["es_fijo"].initial = True

    def clean(self) -> Dict[str, Any]:
        cleaned = super().clean()
        concepto = (cleaned.get("concepto") or "").strip()
        categoria = cleaned.get("categoria")
        elemento = cleaned.get("elemento")
        es_tarjeta = bool(categoria and "tarjeta" in categoria.nombre.lower())
        es_recurrente = bool(elemento and elemento.es_fijo)

        # La recurrencia la define el elemento: si es un compromiso fijo, el gasto lo es también
        if es_recurrente:
            cleaned["es_fijo"] = True

        if not concepto:
            fecha = cleaned.get("fecha") or timezone.localdate()
            anio, mes = fecha.year, fecha.month
            if es_tarjeta:
                if fecha.day == 1:
                    mes -= 1
                    if mes == 0:
                        mes, anio = 12, anio - 1
                cleaned["concepto"] = f"Liquidación {categoria.nombre} ({mes:02d}/{anio})"
            elif es_recurrente:
                cleaned["concepto"] = f"Cuota {elemento.nombre} ({mes:02d}/{anio})"
            else:
                self.add_error("concepto", _("Indica un concepto para el gasto."))
        return cleaned


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

