"""Pruebas unitarias e integradas para el módulo Finanzas, jerarquía Elemento y comando seed_data."""

import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from finanzas.models import Categoria, Elemento, Gasto, GastoEspecialTarjeta, Ingreso
from finanzas.services import FinanzasService
from seguros.models import Seguro

Usuario = get_user_model()


class FinanzasIntegrationTests(TestCase):
    """Pruebas integradas completas de finanzas, comando de seed data y vistas."""

    def test_seed_data_command_integration(self) -> None:
        """Verifica que el comando seed_data cargue todos los modelos y relaciones jerárquicas."""
        call_command("seed_data")

        self.assertTrue(Usuario.objects.filter(email="admin@familia.com").exists())
        self.assertTrue(Usuario.objects.filter(email="carlos@familia.com").exists())
        self.assertTrue(Categoria.objects.filter(tipo=Categoria.Tipo.INGRESO).exists())
        self.assertTrue(Categoria.objects.filter(tipo=Categoria.Tipo.GASTO).exists())
        self.assertTrue(Elemento.objects.count() > 0)
        self.assertTrue(Ingreso.objects.count() > 0)
        self.assertTrue(Gasto.objects.count() > 0)
        self.assertTrue(GastoEspecialTarjeta.objects.count() > 0)
        self.assertTrue(Seguro.objects.count() >= 2)

    def test_dashboard_full_render_with_seeded_data(self) -> None:
        """Verifica la respuesta 200 y el contexto del Dashboard con datos cargados."""
        call_command("seed_data")
        carlos = Usuario.objects.get(email="carlos@familia.com")

        client = Client()
        client.force_login(carlos)

        response = client.get(reverse("finanzas:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("kpis", response.context)
        self.assertIn("graficos_data_json", response.context)
        self.assertIn("movimientos_recientes", response.context)
        self.assertGreater(response.context["kpis"]["total_ingresos"], Decimal("0.00"))

    def test_htmx_tabla_transacciones_endpoint(self) -> None:
        """Verifica el endpoint HTMX para la tabla parcial con filtros y paginación."""
        call_command("seed_data")
        carlos = Usuario.objects.get(email="carlos@familia.com")

        client = Client()
        client.force_login(carlos)

        response = client.get(
            reverse("finanzas:tabla_transacciones_htmx"),
            {"tipo": "INGRESO", "page": "1"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ingreso")

    def test_cuentas_view_and_htmx_endpoint(self) -> None:
        """Verifica la carga de la vista Cuentas y su desglose mensual HTMX."""
        call_command("seed_data")
        carlos = Usuario.objects.get(email="carlos@familia.com")

        client = Client()
        client.force_login(carlos)

        # Cuentas page
        response = client.get(reverse("finanzas:cuentas"), {"anio": "2026", "mes": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("resumen", response.context)
        self.assertContains(response, "Libro Contable")

        # Cuentas HTMX partial
        response_htmx = client.get(
            reverse("finanzas:cuentas_mes_htmx"),
            {"anio": "2026", "mes": "2"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response_htmx.status_code, 200)
        self.assertContains(response_htmx, "Desglose de Ingresos")
        self.assertContains(response_htmx, "Desglose de Gastos")

    def test_administracion_view_and_categoria_crud(self) -> None:
        """Verifica el panel de administración y el ciclo de vida de una categoría."""
        call_command("seed_data")
        admin_user = Usuario.objects.get(email="admin@familia.com")

        client = Client()
        client.force_login(admin_user)

        # 1. Administracion page
        response_admin = client.get(reverse("finanzas:administracion"))
        self.assertEqual(response_admin.status_code, 200)
        self.assertContains(response_admin, "Administración & Configuración Maestra")
        self.assertContains(response_admin, "Categorías & Elementos de Ingresos")
        self.assertContains(response_admin, "Categorías de Gastos")

        # 2. Crear nueva categoría
        response_create = client.post(
            reverse("finanzas:categoria_create"),
            {
                "nombre": "Criptomonedas / Staking",
                "tipo": Categoria.Tipo.INGRESO,
                "icono": "bitcoin",
                "color": "#3BB8DB",
                "descripcion": "Ingresos por activos digitales",
            },
        )
        self.assertEqual(response_create.status_code, 302)
        cat = Categoria.objects.get(nombre="Criptomonedas / Staking")
        self.assertEqual(cat.tipo, Categoria.Tipo.INGRESO)

        # 3. Editar categoría
        response_update = client.post(
            reverse("finanzas:categoria_update", args=[cat.id]),
            {
                "nombre": "Criptomonedas & Finanzas DeFi",
                "tipo": Categoria.Tipo.INGRESO,
                "icono": "coins",
                "color": "#53EAFD",
                "descripcion": "Actualizado",
            },
        )
        self.assertEqual(response_update.status_code, 302)
        cat.refresh_from_db()
        self.assertEqual(cat.nombre, "Criptomonedas & Finanzas DeFi")

        # 4. Eliminar categoría sin elementos
        response_delete = client.post(reverse("finanzas:categoria_delete", args=[cat.id]))
        self.assertEqual(response_delete.status_code, 302)
        self.assertFalse(Categoria.objects.filter(id=cat.id).exists())

    def test_elemento_crud_lifecycle(self) -> None:
        """Verifica el ciclo de vida de un elemento dentro de una categoría."""
        call_command("seed_data")
        admin_user = Usuario.objects.get(email="admin@familia.com")
        cat_casa = Categoria.objects.get(nombre="Gastos Casa")

        client = Client()
        client.force_login(admin_user)

        # 1. Crear nuevo elemento
        response_create = client.post(
            reverse("finanzas:elemento_create"),
            {
                "categoria": cat_casa.id,
                "nombre": "Seguridad & Alarma Securitas",
                "es_fijo": True,
                "icono": "shield",
                "descripcion": "Cuota mensual de alarma del hogar",
            },
        )
        self.assertEqual(response_create.status_code, 302)
        elem = Elemento.objects.get(nombre="Seguridad & Alarma Securitas")
        self.assertEqual(elem.categoria, cat_casa)
        self.assertTrue(elem.es_fijo)

        # 2. Editar elemento
        response_update = client.post(
            reverse("finanzas:elemento_update", args=[elem.id]),
            {
                "categoria": cat_casa.id,
                "nombre": "Alarma & Videovigilancia Prosegur",
                "es_fijo": True,
                "icono": "video",
                "descripcion": "Nueva cuota de seguridad",
            },
        )
        self.assertEqual(response_update.status_code, 302)
        elem.refresh_from_db()
        self.assertEqual(elem.nombre, "Alarma & Videovigilancia Prosegur")

        # 3. Eliminar elemento sin gastos asociados
        response_delete = client.post(reverse("finanzas:elemento_delete", args=[elem.id]))
        self.assertEqual(response_delete.status_code, 302)
        self.assertFalse(Elemento.objects.filter(id=elem.id).exists())

    def test_get_anios_disponibles_fallback_empty(self) -> None:
        """Verifica que si no hay movimientos en la base de datos se devuelva al menos el año actual."""
        hoy = timezone.now().date()
        anios = FinanzasService.get_anios_disponibles()
        self.assertEqual(anios, [hoy.year])

    def test_get_anios_disponibles_dinamicos_segun_datos(self) -> None:
        """Verifica que los años disponibles se extraigan dinámicamente de los ingresos y gastos existentes."""
        from datetime import date
        admin_user = Usuario.objects.create_user(email="test_anios@familia.com", password="password123")
        cat = Categoria.objects.create(nombre="Test Cat", tipo=Categoria.Tipo.INGRESO)
        elem = Elemento.objects.create(categoria=cat, nombre="Test Elem")

        # Crear ingreso en 2023 y gasto en 2025
        Ingreso.objects.create(
            usuario=admin_user,
            elemento=elem,
            fecha=date(2023, 5, 10),
            monto=Decimal("1000.00"),
            descripcion="Ingreso 2023",
        )
        Gasto.objects.create(
            usuario=admin_user,
            elemento=elem,
            fecha=date(2025, 8, 20),
            monto=Decimal("200.00"),
            concepto="Gasto 2025",
        )

        anios = FinanzasService.get_anios_disponibles()
        self.assertEqual(anios, [2023, 2025])

        # Verificar que la vista de Cuentas recibe exactamente [2023, 2025]
        client = Client()
        client.force_login(admin_user)
        response = client.get(reverse("finanzas:cuentas"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["anios_disponibles"], [2023, 2025])

    def test_cuentas_ahorro_model_and_resumen_service(self) -> None:
        """Verifica la creación de cuentas de ahorro, registro de saldos y cálculo del resumen anual."""
        from finanzas.models import CuentaAhorro, RegistroSaldoMensual
        carlos = Usuario.objects.create_user(email="carlos_ahorro@familia.com", password="password123")

        cuenta = CuentaAhorro.objects.create(
            usuario=carlos,
            nombre="Fondo Emergencia Test",
            entidad="MyInvestor",
            tipo=CuentaAhorro.Tipo.FONDO_EMERGENCIA,
            objetivo_monto=Decimal("10000.00"),
        )

        RegistroSaldoMensual.objects.create(cuenta=cuenta, anio=2026, mes=1, saldo=Decimal("5000.00"))
        RegistroSaldoMensual.objects.create(cuenta=cuenta, anio=2026, mes=2, saldo=Decimal("5500.00"))

        self.assertEqual(cuenta.get_saldo_mes(2026, 1), Decimal("5000.00"))
        self.assertEqual(cuenta.get_saldo_mes(2026, 2), Decimal("5500.00"))
        self.assertIsNone(cuenta.get_saldo_mes(2026, 3))
        self.assertEqual(cuenta.get_ultimo_saldo().saldo, Decimal("5500.00"))

        # Probar el servicio anual
        resumen = FinanzasService.get_resumen_ahorros_anual(anio=2026)
        self.assertEqual(resumen["kpis"]["total_ahorro_actual"], Decimal("5500.00"))
        self.assertEqual(resumen["kpis"]["crecimiento_anio_importe"], Decimal("500.00"))
        self.assertEqual(resumen["kpis"]["crecimiento_anio_porcentaje"], Decimal("10.00"))
        self.assertEqual(len(resumen["filas_cuentas"]), 1)

    def test_ahorros_view_and_htmx_endpoints(self) -> None:
        """Verifica la página de Ahorros, el guardado reactivo de saldos HTMX y el CRUD de cuentas."""
        from finanzas.models import CuentaAhorro, RegistroSaldoMensual
        carlos = Usuario.objects.create_user(email="carlos_view@familia.com", password="password123")

        client = Client()
        client.force_login(carlos)

        # 1. Crear cuenta de ahorro mediante vista CreateView
        response_create = client.post(
            reverse("finanzas:cuenta_ahorro_create"),
            {
                "nombre": "Hucha Viaje Japón",
                "entidad": "Revolut",
                "tipo": CuentaAhorro.Tipo.AHORRO_OBJETIVO,
                "color": "#10B981",
                "icono": "plane",
                "objetivo_monto": "4000.00",
                "activo": True,
            },
        )
        self.assertEqual(response_create.status_code, 302)
        cuenta = CuentaAhorro.objects.get(nombre="Hucha Viaje Japón")
        self.assertEqual(cuenta.entidad, "Revolut")

        # 2. Cargar la vista principal de Ahorros
        response_list = client.get(reverse("finanzas:ahorros"), {"anio": "2026"})
        self.assertEqual(response_list.status_code, 200)
        self.assertContains(response_list, "Control de Cuentas de Ahorro")
        self.assertContains(response_list, "Hucha Viaje Japón")

        # 3. Guardar saldo mensual mediante endpoint HTMX
        response_htmx = client.post(
            reverse("finanzas:guardar_saldo_mes_htmx"),
            {
                "cuenta_id": str(cuenta.id),
                "anio": "2026",
                "mes": "3",
                "saldo": "1250.50",
                "notas": "Aportación marzo",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response_htmx.status_code, 200)
        self.assertIn("HX-Trigger", response_htmx.headers)

        # Verificar que el registro se guardó
        reg = RegistroSaldoMensual.objects.get(cuenta=cuenta, anio=2026, mes=3)
        self.assertEqual(reg.saldo, Decimal("1250.50"))
        self.assertEqual(reg.notas, "Aportación marzo")


