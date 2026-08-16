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
