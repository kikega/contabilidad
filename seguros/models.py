"""Modelos de datos para la gestión y negociación de pólizas de seguro familiares."""

from decimal import Decimal
from typing import Optional
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Seguro(models.Model):
    """Póliza de seguro familiar con auditoría de costes e incremento interanual."""

    class Ramo(models.TextChoices):
        HOGAR = "HOGAR", _("Hogar / Vivienda")
        COCHE = "COCHE", _("Vehículo / Coche / Moto")
        SALUD = "SALUD", _("Salud y Asistencia Médica")
        VIDA = "VIDA", _("Vida y Accidentes")
        DECESOS = "DECESOS", _("Decesos")
        RESPONSABILIDAD_CIVIL = "RESPONSABILIDAD_CIVIL", _("Responsabilidad Civil")
        MASCOTAS = "MASCOTAS", _("Mascotas")
        OTROS = "OTROS", _("Otros Seguros")

    class Periodicidad(models.TextChoices):
        ANUAL = "ANUAL", _("Anual")
        SEMESTRAL = "SEMESTRAL", _("Semestral")
        TRIMESTRAL = "TRIMESTRAL", _("Trimestral")
        MENSUAL = "MENSUAL", _("Mensual")

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seguros",
        verbose_name=_("titular o responsable"),
    )
    elemento = models.OneToOneField(
        "finanzas.Elemento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seguro",
        verbose_name=_("elemento contable vinculado"),
    )
    ramo = models.CharField(
        _("tipo / ramo de seguro"),
        max_length=30,
        choices=Ramo.choices,
        default=Ramo.HOGAR,
        db_index=True,
    )
    compania = models.CharField(
        _("compañía aseguradora"),
        max_length=150,
        help_text=_("Nombre de la aseguradora (ej: Mapfre, Allianz, Mutua Madrileña, Axa)."),
    )
    numero_poliza = models.CharField(
        _("número de póliza"),
        max_length=100,
        db_index=True,
    )
    bien_asegurado = models.CharField(
        _("bien o personas aseguradas"),
        max_length=200,
        help_text=_("Descripción breve (ej: Vivienda principal, Seat León 1234-XYZ, Familia García)."),
    )
    gestor_nombre = models.CharField(
        _("nombre del mediador / gestor"),
        max_length=150,
        blank=True,
    )
    gestor_telefono = models.CharField(
        _("teléfono del gestor"),
        max_length=50,
        blank=True,
    )
    gestor_email = models.EmailField(
        _("correo electrónico del gestor"),
        blank=True,
    )
    fecha_inicio = models.DateField(
        _("fecha de efecto / inicio"),
        null=True,
        blank=True,
    )
    fecha_vencimiento = models.DateField(
        _("fecha de vencimiento / renovación"),
        db_index=True,
        help_text=_("Fecha clave para preaviso y renegociación de la prima."),
    )
    periodicidad = models.CharField(
        _("periodicidad del pago"),
        max_length=20,
        choices=Periodicidad.choices,
        default=Periodicidad.ANUAL,
    )
    prima_actual = models.DecimalField(
        _("prima actual (€)"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Coste total anualizado o de la última renovación."),
    )
    prima_anterior = models.DecimalField(
        _("prima periodo anterior (€)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Coste del año previo para el cálculo comparativo."),
    )
    activo = models.BooleanField(
        _("póliza en vigor"),
        default=True,
        db_index=True,
    )
    notas_negociacion = models.TextField(
        _("notas de negociación / coberturas"),
        blank=True,
        help_text=_("Estrategia de negociación con el gestor, contraofertas y condiciones clave."),
    )
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    RAMO_ICONOS = {
        Ramo.HOGAR: "home",
        Ramo.COCHE: "car",
        Ramo.SALUD: "heart-pulse",
        Ramo.VIDA: "shield",
        Ramo.DECESOS: "shield",
        Ramo.RESPONSABILIDAD_CIVIL: "scale",
        Ramo.MASCOTAS: "paw-print",
        Ramo.OTROS: "shield-check",
    }

    class Meta:
        verbose_name = _("seguro")
        verbose_name_plural = _("seguros")
        ordering = ["fecha_vencimiento", "compania"]
        indexes = [
            models.Index(fields=["activo", "fecha_vencimiento"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_ramo_display()} - {self.compania} ({self.bien_asegurado}) - {self.prima_actual}€"

    def sync_elemento(self) -> Any:
        """Sincroniza o genera el Elemento contable correspondiente bajo la categoría Seguros delegando en SeguroService."""
        from seguros.services import SeguroService
        return SeguroService.sync_elemento(self)

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)
        # Sincronizar el elemento contable asociado si no existe o ha cambiado
        nombre_esperado = f"{self.compania} - {self.bien_asegurado}".strip()
        if not self.elemento_id or self.elemento.nombre != nombre_esperado:
            self.sync_elemento()
            super().save(update_fields=["elemento"])

    def get_gastos(self) -> Any:
        """Devuelve el queryset de apuntes de gastos registrados asociados a esta póliza."""
        if not self.elemento_id:
            from finanzas.models import Gasto
            return Gasto.objects.none()
        return self.elemento.gastos.select_related("usuario").order_by("-fecha")

    def get_resumen_gastos_anuales(self) -> list:
        """Agrupa los gastos reales pagados por año para análisis comparativo interanual delegando en SeguroService."""
        from seguros.services import SeguroService
        return SeguroService.get_resumen_gastos_anuales(self)

    @property
    def incremento_importe(self) -> Decimal:
        """Calcula la diferencia económica neta respecto al año anterior."""
        if self.prima_anterior is not None:
            return (self.prima_actual - self.prima_anterior).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def incremento_porcentaje(self) -> Decimal:
        """Calcula la subida o bajada porcentual respecto al periodo previo."""
        if self.prima_anterior and self.prima_anterior > Decimal("0.00"):
            variacion = ((self.prima_actual - self.prima_anterior) / self.prima_anterior) * Decimal("100.00")
            return variacion.quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def dias_para_vencimiento(self) -> int:
        """Devuelve el número de días restantes hasta el vencimiento de la póliza."""
        hoy = timezone.localdate()
        return (self.fecha_vencimiento - hoy).days

    @property
    def estado_vencimiento(self) -> str:
        """Categoriza la cercanía de renovación para alertas visuales."""
        dias = self.dias_para_vencimiento
        if dias < 0:
            return "vencido"
        if dias <= 30:
            return "urgente"
        if dias <= 60:
            return "proximo"
        return "vigente"


class HistorialRenovacionSeguro(models.Model):
    """Registro histórico de costes por año de una póliza para análisis evolutivo."""

    seguro = models.ForeignKey(
        Seguro,
        on_delete=models.CASCADE,
        related_name="historial",
        verbose_name=_("póliza vinculada"),
    )
    ejercicio_anio = models.PositiveIntegerField(_("año / ejercicio"), db_index=True)
    prima_pagada = models.DecimalField(
        _("prima pagada (€)"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    fecha_renovacion = models.DateField(_("fecha de cobro / renovación"))
    notas = models.CharField(_("observaciones"), max_length=255, blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)

    class Meta:
        verbose_name = _("historial de renovación de seguro")
        verbose_name_plural = _("historiales de renovación de seguros")
        ordering = ["-ejercicio_anio"]
        constraints = [
            models.UniqueConstraint(
                fields=["seguro", "ejercicio_anio"],
                name="unique_seguro_ejercicio",
            )
        ]

    def __str__(self) -> str:
        return f"{self.seguro.compania} ({self.ejercicio_anio}): {self.prima_pagada}€"
