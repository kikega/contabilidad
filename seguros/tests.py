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

    def test_sync_elemento_automatico_al_crear_seguro(self) -> None:
        """Verifica que al dar de alta un seguro se cree/vincule automáticamente el Elemento en la categoría Seguros."""
        from finanzas.models import Categoria, Elemento
        seguro = Seguro.objects.create(
            usuario=self.usuario,
            ramo=Seguro.Ramo.COCHE,
            compania="Línea Directa",
            numero_poliza="LD-AUTO-7788",
            bien_asegurado="Toyota Yaris",
            fecha_vencimiento=self.fecha_hoy + timedelta(days=30),
            prima_actual=Decimal("350.00"),
        )
        self.assertIsNotNone(seguro.elemento)
        self.assertEqual(seguro.elemento.nombre, "Línea Directa - Toyota Yaris")
        self.assertEqual(seguro.elemento.categoria.nombre, "Seguros")
        self.assertEqual(seguro.elemento.categoria.tipo, Categoria.Tipo.GASTO)
        self.assertTrue(seguro.elemento.es_fijo)

    def test_registrar_pago_seguro_view_y_resumen_anual(self) -> None:
        """Verifica el registro de un pago contable (Gasto) desde el módulo de seguros y el resumen interanual."""
        from datetime import date
        from django.test import Client
        from django.urls import reverse
        from finanzas.models import Gasto

        seguro = Seguro.objects.create(
            usuario=self.usuario,
            ramo=Seguro.Ramo.HOGAR,
            compania="Mapfre",
            numero_poliza="MAP-HOG-1122",
            bien_asegurado="Chalet Sierra",
            fecha_vencimiento=self.fecha_hoy + timedelta(days=60),
            prima_actual=Decimal("400.00"),
            prima_anterior=Decimal("380.00"),
        )

        client = Client()
        client.force_login(self.usuario)

        # 1. Registrar pago de 2025
        Gasto.objects.create(
            usuario=self.usuario,
            elemento=seguro.elemento,
            fecha=date(2025, 4, 15),
            concepto="Recibo Anual Hogar 2025",
            monto=Decimal("380.00"),
            es_fijo=True,
        )

        # 2. Registrar pago de 2026 mediante el endpoint de pago
        response = client.post(
            reverse("seguros:pago_create", args=[seguro.id]),
            {
                "fecha": "2026-04-15",
                "monto": "400.00",
                "concepto": "Recibo Anual Hogar 2026",
                "notas": "Renovación con incremento del 5.26%",
            },
        )
        self.assertEqual(response.status_code, 302)

        # Verificar que el gasto fue creado
        gastos = seguro.get_gastos()
        self.assertEqual(gastos.count(), 2)

        # Verificar el resumen anual y la comparativa interanual calculada
        resumen = seguro.get_resumen_gastos_anuales()
        self.assertEqual(len(resumen), 2)
        # Primer item es 2026 (más reciente)
        self.assertEqual(resumen[0]["anio"], 2026)
        self.assertEqual(resumen[0]["total"], Decimal("400.00"))
        self.assertEqual(resumen[0]["prev_total"], Decimal("380.00"))
        self.assertEqual(resumen[0]["var_importe"], Decimal("20.00"))
        self.assertEqual(resumen[0]["var_porcentaje"], Decimal("5.26"))

