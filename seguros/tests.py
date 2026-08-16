"""Pruebas unitarias para los modelos del módulo Seguros."""

from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from seguros.models import HistorialRenovacionSeguro, Seguro

Usuario = get_user_model()


class SegurosModelsTests(TestCase):
    """Conjunto de pruebas para validar cálculo de incremento y estado de pólizas."""

    def setUp(self) -> None:
        self.usuario = Usuario.objects.create_user(
            email="titular@ejemplo.com",
            password="Password123!",
        )
        self.fecha_hoy = timezone.now().date()

    def test_calculo_incremento_porcentaje_e_importe(self) -> None:
        """Verifica que el cálculo de incremento anual (importe y porcentaje) sea exacto."""
        seguro = Seguro.objects.create(
            usuario=self.usuario,
            ramo=Seguro.Ramo.COCHE,
            compania="Mapfre",
            numero_poliza="MAP-2024-9988",
            bien_asegurado="Peugeot 3008",
            gestor_nombre="Laura Martínez",
            gestor_telefono="600112233",
            fecha_vencimiento=self.fecha_hoy + timedelta(days=20),
            prima_actual=Decimal("550.00"),
            prima_anterior=Decimal("500.00"),
        )

        # 550 - 500 = 50.00 de incremento
        self.assertEqual(seguro.incremento_importe, Decimal("50.00"))
        # (50 / 500) * 100 = 10.00%
        self.assertEqual(seguro.incremento_porcentaje, Decimal("10.00"))
        # Vence en 20 días => urgente (<= 30 días)
        self.assertEqual(seguro.estado_vencimiento, "urgente")

    def test_seguro_sin_prima_anterior(self) -> None:
        """Verifica el comportamiento cuando es una nueva póliza sin histórico."""
        seguro_nuevo = Seguro.objects.create(
            usuario=self.usuario,
            ramo=Seguro.Ramo.HOGAR,
            compania="Allianz",
            numero_poliza="ALZ-HOG-1234",
            bien_asegurado="Piso Principal",
            fecha_vencimiento=self.fecha_hoy + timedelta(days=90),
            prima_actual=Decimal("320.00"),
            prima_anterior=None,
        )
        self.assertEqual(seguro_nuevo.incremento_importe, Decimal("0.00"))
        self.assertEqual(seguro_nuevo.incremento_porcentaje, Decimal("0.00"))
        self.assertEqual(seguro_nuevo.estado_vencimiento, "vigente")

    def test_historial_renovacion_seguro(self) -> None:
        """Verifica el registro histórico de primas pagadas."""
        seguro = Seguro.objects.create(
            usuario=self.usuario,
            ramo=Seguro.Ramo.SALUD,
            compania="Sanitas",
            numero_poliza="SAN-MED-5544",
            bien_asegurado="Cobertura Familiar Completa",
            fecha_vencimiento=self.fecha_hoy + timedelta(days=45),
            prima_actual=Decimal("1200.00"),
            prima_anterior=Decimal("1100.00"),
        )
        historial = HistorialRenovacionSeguro.objects.create(
            seguro=seguro,
            ejercicio_anio=2023,
            prima_pagada=Decimal("1050.00"),
            fecha_renovacion=self.fecha_hoy - timedelta(days=365),
            notas="Renovación sin siniestros",
        )
        self.assertEqual(historial.prima_pagada, Decimal("1050.00"))
        self.assertEqual(seguro.historial.count(), 1)
