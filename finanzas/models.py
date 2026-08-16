"""Modelos de datos para el dominio financiero: Categorías, Elementos, Ingresos, Gastos y Desglose de Tarjetas."""

from decimal import Decimal
from typing import Optional
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Categoria(models.Model):
    """Modelo para agrupar macro-flujos de dinero (ej: Gastos Casa, Vehículos, Salud, Ingresos...)."""

    class Tipo(models.TextChoices):
        INGRESO = "INGRESO", _("Ingreso")
        GASTO = "GASTO", _("Gasto")
        ESPECIAL_TARJETA = "ESPECIAL_TARJETA", _("Control Especial Tarjeta")

    nombre = models.CharField(_("nombre"), max_length=100)
    tipo = models.CharField(
        _("tipo de categoría"),
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.GASTO,
        db_index=True,
    )
    icono = models.CharField(
        _("icono identificador"),
        max_length=50,
        default="folder",
        help_text=_("Nombre del icono SVG/Lucide para renderizar en la interfaz (ej: home, car, heart-pulse)."),
    )
    color = models.CharField(
        _("código de color"),
        max_length=20,
        default="#3BB8DB",
        help_text=_("Color representativo para gráficas y etiquetas (ej: #3BB8DB)."),
    )
    descripcion = models.TextField(_("descripción"), blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    class Meta:
        verbose_name = _("categoría")
        verbose_name_plural = _("categorías")
        ordering = ["tipo", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre", "tipo"],
                name="unique_nombre_tipo_categoria",
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_tipo_display()})"


class Elemento(models.Model):
    """Concepto o subcategoría específica perteneciente a una Categoría (ej: Electricidad, Agua, Movistar, Gasolina...)."""

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="elementos",
        verbose_name=_("categoría"),
    )
    nombre = models.CharField(_("nombre del elemento"), max_length=100)
    es_fijo = models.BooleanField(
        _("es gasto/ingreso fijo"),
        default=False,
        help_text=_("Marca si este elemento suele ser un compromiso recurrente mes a mes (ej: Hipoteca, Suministros)."),
    )
    icono = models.CharField(
        _("icono específico"),
        max_length=50,
        blank=True,
        help_text=_("Icono específico opcional. Si está vacío heredará el icono de su categoría."),
    )
    descripcion = models.TextField(_("descripción"), blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    class Meta:
        verbose_name = _("elemento")
        verbose_name_plural = _("elementos")
        ordering = ["categoria", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "nombre"],
                name="unique_elemento_por_categoria",
            )
        ]

    @property
    def icono_efectivo(self) -> str:
        """Devuelve el icono propio o el de la categoría padre si no está definido."""
        return self.icono if self.icono else self.categoria.icono

    def __str__(self) -> str:
        return f"{self.categoria.nombre} > {self.nombre}"


class Ingreso(models.Model):
    """Registro de entradas económicas y fuentes salariales de la unidad familiar."""

    class Fuente(models.TextChoices):
        NOMINA_TITULAR_1 = "NOMINA_TITULAR_1", _("Nómina Titular 1")
        NOMINA_TITULAR_2 = "NOMINA_TITULAR_2", _("Nómina Titular 2")
        RESCATE_PLAN_PENSIONES = "RESCATE_PLAN_PENSIONES", _("Rescate Plan Pensiones")
        PENSIONES = "PENSIONES", _("Pensiones")
        RENDIMIENTOS_CAPITAL = "RENDIMIENTOS_CAPITAL", _("Rendimientos de Capital / Inversión")
        OTROS = "OTROS", _("Otros Ingresos")

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingresos",
        verbose_name=_("usuario responsable"),
    )
    elemento = models.ForeignKey(
        Elemento,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ingresos",
        verbose_name=_("elemento / concepto"),
        limit_choices_to={"categoria__tipo": Categoria.Tipo.INGRESO},
    )
    fuente = models.CharField(
        _("fuente de ingreso"),
        max_length=30,
        choices=Fuente.choices,
        default=Fuente.NOMINA_TITULAR_1,
        db_index=True,
    )
    monto = models.DecimalField(
        _("importe (€)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    fecha = models.DateField(
        _("fecha de percepción"),
        default=timezone.now,
        db_index=True,
    )
    descripcion = models.CharField(_("concepto o descripción"), max_length=255, blank=True)
    notas = models.TextField(_("observaciones"), blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    class Meta:
        verbose_name = _("ingreso")
        verbose_name_plural = _("ingresos")
        ordering = ["-fecha", "-creado_en"]
        indexes = [
            models.Index(fields=["fecha", "fuente"]),
            models.Index(fields=["fecha", "monto"]),
        ]

    @property
    def categoria(self) -> Optional[Categoria]:
        """Acceso a la categoría padre del elemento."""
        return self.elemento.categoria if self.elemento else None

    def __str__(self) -> str:
        elem_name = self.elemento.nombre if self.elemento else "Ingreso"
        return f"{elem_name} ({self.get_fuente_display()}) - {self.monto}€ ({self.fecha})"


class Gasto(models.Model):
    """Registro de gastos periódicos y desembolsos de la unidad familiar."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gastos",
        verbose_name=_("usuario responsable"),
    )
    elemento = models.ForeignKey(
        Elemento,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gastos",
        verbose_name=_("elemento / subcategoría"),
        limit_choices_to={"categoria__tipo": Categoria.Tipo.GASTO},
    )
    concepto = models.CharField(_("concepto del apunte"), max_length=255)
    monto = models.DecimalField(
        _("importe (€)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    fecha = models.DateField(
        _("fecha del gasto"),
        default=timezone.now,
        db_index=True,
    )
    es_fijo = models.BooleanField(
        _("gasto fijo/recurrente"),
        default=False,
        help_text=_("Marcar si es un compromiso fijo mensual (préstamo, alquiler, cuota)."),
    )
    notas = models.TextField(_("observaciones y detalles"), blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    class Meta:
        verbose_name = _("gasto")
        verbose_name_plural = _("gastos")
        ordering = ["-fecha", "-creado_en"]
        indexes = [
            models.Index(fields=["fecha", "monto"]),
        ]

    @property
    def categoria(self) -> Optional[Categoria]:
        """Acceso a la categoría padre del elemento."""
        return self.elemento.categoria if self.elemento else None

    def __str__(self) -> str:
        elem_name = self.elemento.nombre if self.elemento else "Gasto"
        return f"{elem_name}: {self.concepto} - {self.monto}€ ({self.fecha})"


class GastoEspecialTarjeta(models.Model):
    """Auditoría y desglose detallado de compras clave realizadas con tarjetas de crédito."""

    class TipoComercio(models.TextChoices):
        SUPERMERCADO = "SUPERMERCADO", _("Supermercados / Alimentación")
        MERCADO = "MERCADO", _("Mercados y Comercio Local")
        RESTAURANTE_OCIO = "RESTAURANTE_OCIO", _("Restaurantes y Ocio")
        GASOLINA = "GASOLINA", _("Combustible y Estaciones de Servicio")
        COMPRAS_ONLINE = "COMPRAS_ONLINE", _("Compras Online")
        FARMACIA_SALUD = "FARMACIA_SALUD", _("Farmacia y Cuidado Personal")
        OTROS = "OTROS", _("Otros Pagos con Tarjeta")

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gastos_tarjeta",
        verbose_name=_("titular / usuario"),
    )
    tarjeta = models.CharField(
        _("tarjeta utilizada"),
        max_length=100,
        help_text=_("Nombre identificativo (ej: Visa Oro Titular 1, Mastercard Familiar)."),
    )
    tipo_comercio = models.CharField(
        _("tipo de comercio"),
        max_length=30,
        choices=TipoComercio.choices,
        default=TipoComercio.SUPERMERCADO,
        db_index=True,
    )
    comercio = models.CharField(
        _("establecimiento / comercio"),
        max_length=200,
        help_text=_("Nombre del comercio (ej: Mercadona, Carrefour, Amazon)."),
    )
    monto = models.DecimalField(
        _("importe (€)"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    fecha = models.DateField(_("fecha de la operación"), default=timezone.now, db_index=True)
    gasto_asociado = models.ForeignKey(
        Gasto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="desgloses_tarjeta",
        verbose_name=_("gasto global vinculado"),
        help_text=_("Opcional: vinculación con el apunte agregado mensual de tarjeta."),
    )
    notas = models.TextField(_("notas"), blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    class Meta:
        verbose_name = _("control especial de tarjeta")
        verbose_name_plural = _("controles especiales de tarjetas")
        ordering = ["-fecha", "-creado_en"]
        indexes = [
            models.Index(fields=["fecha", "tipo_comercio"]),
            models.Index(fields=["tarjeta", "fecha"]),
        ]

    def __str__(self) -> str:
        return f"{self.comercio} ({self.get_tipo_comercio_display()}) - {self.monto}€ [{self.tarjeta}]"


class CuentaAhorro(models.Model):
    """Cuenta, hucha o depósito destinado a la acumulación de ahorro o inversión."""

    class Tipo(models.TextChoices):
        FONDO_EMERGENCIA = "FONDO_EMERGENCIA", _("Fondo de Emergencia")
        AHORRO_OBJETIVO = "AHORRO_OBJETIVO", _("Ahorro para Objetivos / Metas")
        CUENTA_REMUNERADA = "CUENTA_REMUNERADA", _("Cuenta Remunerada / Depósito")
        INVERSION = "INVERSION", _("Inversión / Fondos Indexados")
        HUCHA_EFECTIVO = "HUCHA_EFECTIVO", _("Efectivo / Hucha")
        OTRO = "OTRO", _("Otro Ahorro")

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cuentas_ahorro",
        verbose_name=_("titular o responsable"),
    )
    nombre = models.CharField(_("nombre de la cuenta"), max_length=100)
    entidad = models.CharField(_("banco / entidad"), max_length=100, help_text=_("Ej: MyInvestor, Trade Republic, Santander, Openbank, Efectivo."))
    tipo = models.CharField(
        _("tipo de cuenta"),
        max_length=30,
        choices=Tipo.choices,
        default=Tipo.FONDO_EMERGENCIA,
        db_index=True,
    )
    color = models.CharField(
        _("código de color"),
        max_length=20,
        default="#3BB8DB",
        help_text=_("Color distintivo para gráficas y visualización (ej: #3BB8DB)."),
    )
    icono = models.CharField(
        _("icono identificador"),
        max_length=50,
        default="piggy-bank",
        help_text=_("Nombre del icono Lucide (ej: piggy-bank, landmark, trending-up, wallet)."),
    )
    numero_cuenta_iban = models.CharField(
        _("IBAN o identificador (opcional)"),
        max_length=50,
        blank=True,
    )
    objetivo_monto = models.DecimalField(
        _("meta de ahorro (€)"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Objetivo o cantidad objetivo a alcanzar (opcional)."),
    )
    activo = models.BooleanField(_("cuenta activa"), default=True, db_index=True)
    notas = models.TextField(_("notas / condiciones"), blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    class Meta:
        verbose_name = _("cuenta de ahorro")
        verbose_name_plural = _("cuentas de ahorro")
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.entidad}) - {self.get_tipo_display()}"

    def get_saldo_mes(self, anio: int, mes: int) -> Optional[Decimal]:
        """Devuelve el saldo registrado en un mes y año específicos."""
        registro = self.saldos.filter(anio=anio, mes=mes).first()
        return registro.saldo if registro else None

    def get_ultimo_saldo(self) -> Optional["RegistroSaldoMensual"]:
        """Devuelve el registro de saldo más reciente."""
        return self.saldos.order_by("-anio", "-mes").first()


class RegistroSaldoMensual(models.Model):
    """Instantánea de saldo consolidado en una cuenta de ahorro en un mes concreto."""

    cuenta = models.ForeignKey(
        CuentaAhorro,
        on_delete=models.CASCADE,
        related_name="saldos",
        verbose_name=_("cuenta de ahorro"),
    )
    anio = models.PositiveIntegerField(_("año / ejercicio"), db_index=True)
    mes = models.PositiveSmallIntegerField(_("mes (1-12)"), db_index=True)
    saldo = models.DecimalField(
        _("saldo a fin de mes (€)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    notas = models.CharField(_("observaciones del mes"), max_length=255, blank=True)
    creado_en = models.DateTimeField(_("creado en"), auto_now_add=True)
    actualizado_en = models.DateTimeField(_("actualizado en"), auto_now=True)

    class Meta:
        verbose_name = _("registro de saldo mensual")
        verbose_name_plural = _("registros de saldos mensuales")
        ordering = ["-anio", "-mes", "cuenta__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["cuenta", "anio", "mes"],
                name="unique_saldo_cuenta_mes_anio",
            )
        ]
        indexes = [
            models.Index(fields=["anio", "mes"]),
        ]

    def __str__(self) -> str:
        return f"{self.cuenta.nombre} ({self.mes}/{self.anio}): {self.saldo}€"

