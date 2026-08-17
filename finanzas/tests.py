"""Pruebas unitarias e integradas para el módulo Finanzas, jerarquía Elemento y comando seed_data."""

import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from finanzas.models import Categoria, Elemento, Gasto, Ingreso
from finanzas.services import FinanzasService
from seguros.models import Seguro

Usuario = get_user_model()


class FinanzasIntegrationTests(TestCase):
    """Pruebas integradas completas de finanzas, comando de seed data y vistas."""

    def test_seed_data_command_integration(self) -> None:
        """Verifica que el comando seed_data cargue todos los modelos y relaciones jerárquicas."""
        call_command("seed_data", force=True)

        self.assertTrue(Usuario.objects.filter(email="admin@familia.com").exists())
        self.assertTrue(Usuario.objects.filter(email="carlos@familia.com").exists())
        self.assertTrue(Categoria.objects.filter(tipo=Categoria.Tipo.INGRESO).exists())
        self.assertTrue(Categoria.objects.filter(tipo=Categoria.Tipo.GASTO).exists())
        self.assertTrue(Elemento.objects.count() > 0)
        self.assertTrue(Ingreso.objects.count() > 0)
        self.assertTrue(Gasto.objects.count() > 0)
        self.assertTrue(Seguro.objects.count() >= 2)

        # Estructura de préstamos y renting según el diseño de ingresos/gastos generalizados
        self.assertTrue(Categoria.objects.filter(nombre="Préstamos & Financiaciones", tipo=Categoria.Tipo.GASTO).exists())
        self.assertTrue(Elemento.objects.filter(nombre="Hipoteca / Alquiler", categoria__nombre="Préstamos & Financiaciones").exists())
        self.assertTrue(Elemento.objects.filter(nombre="Renting Coche", categoria__nombre="Coches & Movilidad").exists())
        self.assertFalse(Elemento.objects.filter(nombre="Préstamo Coche").exists())

    def test_dashboard_full_render_with_seeded_data(self) -> None:
        """Verifica la respuesta 200 y el contexto del Dashboard con datos cargados."""
        call_command("seed_data", force=True)
        carlos = Usuario.objects.get(email="carlos@familia.com")

        client = Client()
        client.force_login(carlos)

        response = client.get(reverse("finanzas:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("kpis", response.context)
        self.assertIn("graficos_data", response.context)
        self.assertIn("comparativa_anual", response.context)
        self.assertGreater(response.context["kpis"]["total_ingresos"], Decimal("0.00"))
        self.assertContains(response, "Comparativa Anual")
        self.assertTrue(response.context["comparativa_anual"]["filas"])

    def test_comparativa_anual_agregaciones_por_anio(self) -> None:
        """Verifica que la comparativa anual agrega ingresos, gastos por categoría y ahorro por año."""
        from datetime import date

        carlos = Usuario.objects.create_user(email="comp@familia.com", password="password123")
        cat_ing = Categoria.objects.create(nombre="Nóminas", tipo=Categoria.Tipo.INGRESO)
        elem_ing = Elemento.objects.create(categoria=cat_ing, nombre="Sueldo Carlos")
        cat_gas = Categoria.objects.create(nombre="Gastos Casa", tipo=Categoria.Tipo.GASTO, color="#10B981")
        elem_hip = Elemento.objects.create(categoria=cat_gas, nombre="Hipoteca / Alquiler", es_fijo=True)

        Ingreso.objects.create(usuario=carlos, elemento=elem_ing, monto=Decimal("3000.00"), fecha=date(2025, 1, 10))
        Ingreso.objects.create(usuario=carlos, elemento=elem_ing, monto=Decimal("3200.00"), fecha=date(2026, 1, 10))
        Gasto.objects.create(usuario=carlos, elemento=elem_hip, concepto="Cuota", monto=Decimal("850.00"), fecha=date(2025, 1, 5))
        Gasto.objects.create(usuario=carlos, elemento=elem_hip, concepto="Cuota", monto=Decimal("900.00"), fecha=date(2026, 1, 5))

        resumen = FinanzasService.get_comparativa_anual()
        filas = {f["anio"]: f for f in resumen["filas"]}

        self.assertEqual(set(filas.keys()), {2025, 2026})
        self.assertEqual(filas[2025]["ingresos"], Decimal("3000.00"))
        self.assertEqual(filas[2025]["gastos"], Decimal("850.00"))
        self.assertEqual(filas[2025]["ahorro"], Decimal("2150.00"))
        self.assertEqual(filas[2026]["ingresos"], Decimal("3200.00"))
        self.assertEqual(filas[2026]["gastos"], Decimal("900.00"))

        # Desglose por categoría alineado con la lista de categorías
        self.assertEqual(len(resumen["categorias"]), 1)
        self.assertEqual(resumen["categorias"][0]["nombre"], "Gastos Casa")
        self.assertEqual(
            filas[2025]["categorias"][resumen["categorias"][0]["id"]],
            Decimal("850.00"),
        )

        # Series del gráfico
        self.assertEqual(resumen["graficos"]["ingresos"], [3000.0, 3200.0])
        self.assertEqual(resumen["graficos"]["ahorro"], [2150.0, 2300.0])

    def test_htmx_tabla_transacciones_endpoint(self) -> None:
        """Verifica el endpoint HTMX para la tabla parcial con filtros y paginación."""
        call_command("seed_data", force=True)
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
        """Verifica la carga de la vista Cuentas con matriz anual de 12 meses y su modal de detalle HTMX."""
        call_command("seed_data", force=True)
        carlos = Usuario.objects.get(email="carlos@familia.com")

        client = Client()
        client.force_login(carlos)

        # Cuentas page con matriz anual
        response = client.get(reverse("finanzas:cuentas"), {"anio": "2026"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("resumen_anual", response.context)
        self.assertContains(response, "Libro Contable & Cuentas Anuales")
        self.assertContains(response, "Total Ingresos")
        self.assertContains(response, "Total Gastos")

        # Cuentas HTMX annual partial
        response_htmx = client.get(
            reverse("finanzas:cuentas_mes_htmx"),
            {"anio": "2026"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response_htmx.status_code, 200)
        self.assertContains(response_htmx, "Resumen General del Ejercicio 2026")
        self.assertContains(response_htmx, "Categorías de Ingresos")
        self.assertContains(response_htmx, "Categorías de Gastos")

        # Elemento Mes Detalle HTMX Modal
        elem = Elemento.objects.first()
        response_modal = client.get(
            reverse("finanzas:elemento_mes_detalle_htmx"),
            {"elemento_id": elem.id, "anio": "2026", "mes": "1", "tipo": "gasto"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response_modal.status_code, 200)
        self.assertContains(response_modal, elem.nombre)

        # Verificación del orden prioritario de categorías de gastos: Tarjetas primero, luego Gastos Casa
        desglose_gastos = response.context["resumen_anual"]["desglose_gastos"]
        self.assertGreaterEqual(len(desglose_gastos), 2)
        self.assertIn("tarjeta", desglose_gastos[0]["categoria"].nombre.lower())
        self.assertIn("casa", desglose_gastos[1]["categoria"].nombre.lower())

    def test_orden_categorias_gasto_tarjetas_primero_luego_casa(self) -> None:
        """Verifica que el servicio de cuentas devuelva las categorías de gasto ordenadas con Tarjetas primero, luego Gastos Casa, y después el resto alfabéticamente."""
        Categoria.objects.all().delete()
        cat_varios = Categoria.objects.create(nombre="Varios & Imprevistos", tipo=Categoria.Tipo.GASTO)
        cat_casa = Categoria.objects.create(nombre="Gastos Casa", tipo=Categoria.Tipo.GASTO)
        cat_auto = Categoria.objects.create(nombre="Coches & Movilidad", tipo=Categoria.Tipo.GASTO)
        cat_tarjeta = Categoria.objects.create(nombre="Tarjetas de Crédito", tipo=Categoria.Tipo.GASTO)
        cat_seguros = Categoria.objects.create(nombre="Seguros", tipo=Categoria.Tipo.GASTO)

        qs = FinanzasService.get_categorias_gasto_queryset()
        nombres = [c.nombre for c in qs]
        self.assertEqual(
            nombres,
            [
                "Tarjetas de Crédito",
                "Gastos Casa",
                "Coches & Movilidad",
                "Seguros",
                "Varios & Imprevistos",
            ],
        )

        resumen = FinanzasService.get_resumen_cuentas_anual(anio=2026)
        nombres_resumen = [item["categoria"].nombre for item in resumen["desglose_gastos"]]
        self.assertEqual(
            nombres_resumen,
            [
                "Tarjetas de Crédito",
                "Gastos Casa",
                "Coches & Movilidad",
                "Seguros",
                "Varios & Imprevistos",
            ],
        )

    def test_administracion_view_and_categoria_crud(self) -> None:
        """Verifica el panel de administración y el ciclo de vida de una categoría."""
        call_command("seed_data", force=True)
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
        call_command("seed_data", force=True)
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

    def test_graficos_no_xss_en_json_script(self) -> None:
        """Verifica que los nombres de categorías/cuentas con marcado no se inyecten como HTML/JS literal."""
        from finanzas.models import CuentaAhorro, Gasto, RegistroSaldoMensual

        payload = '</script><script>alert(1)</script>'
        carlos = Usuario.objects.create_user(email="xss@familia.com", password="password123")

        cat = Categoria.objects.create(
            nombre=f"Maliciosa {payload}",
            tipo=Categoria.Tipo.GASTO,
            color="#3BB8DB",
        )
        elem = Elemento.objects.create(categoria=cat, nombre="Elem XSS")
        Gasto.objects.create(
            usuario=carlos,
            elemento=elem,
            concepto="Compra",
            monto=Decimal("10.00"),
            fecha=timezone.now().date(),
        )

        cuenta = CuentaAhorro.objects.create(
            usuario=carlos,
            nombre=f"Cuenta {payload}",
            entidad="Test",
            tipo=CuentaAhorro.Tipo.OTRO,
        )
        RegistroSaldoMensual.objects.create(cuenta=cuenta, anio=2026, mes=1, saldo=Decimal("100.00"))

        client = Client()
        client.force_login(carlos)

        for url_name, kwargs in [
            ("finanzas:dashboard", {}),
            ("finanzas:ahorros", {"anio": "2026"}),
        ]:
            response = client.get(reverse(url_name), kwargs)
            self.assertEqual(response.status_code, 200)
            content = response.content.decode("utf-8")
            self.assertNotIn(payload, content)

    def test_seed_data_bloqueado_fuera_de_debug(self) -> None:
        """Verifica que seed_data se bloquea en entornos no DEBUG salvo con el flag --force."""
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("seed_data")

    def test_next_url_evita_open_redirect(self) -> None:
        """Verifica que el parámetro 'next' solo permita redirecciones a hosts internos."""
        from datetime import date

        carlos = Usuario.objects.create_user(email="redirect@familia.com", password="password123")
        cat = Categoria.objects.create(nombre="Ingresos Redirect", tipo=Categoria.Tipo.INGRESO)
        elem = Elemento.objects.create(categoria=cat, nombre="Nómina")
        cat_gasto = Categoria.objects.create(nombre="Gastos Redirect", tipo=Categoria.Tipo.GASTO)
        elem_gasto = Elemento.objects.create(categoria=cat_gasto, nombre="Compra")

        client = Client()
        client.force_login(carlos)

        # next externo -> debe caer al fallback interno (cuentas)
        response = client.post(
            reverse("finanzas:ingreso_create"),
            {
                "elemento": elem.id,
                "monto": "100.00",
                "fecha": date.today().isoformat(),
                "descripcion": "",
                "notas": "",
                "next": "https://evil.example.com/robo",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("finanzas:cuentas"), response["Location"])
        self.assertNotIn("evil.example.com", response["Location"])

        # next interno relativo -> se respeta
        response = client.post(
            reverse("finanzas:gasto_create"),
            {
                "categoria": cat_gasto.id,
                "concepto": "Compra",
                "elemento": elem_gasto.id,
                "monto": "20.00",
                "fecha": date.today().isoformat(),
                "es_fijo": "",
                "notas": "",
                "next": "/cuentas/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/", response["Location"])

    def test_gasto_tarjeta_concepto_automatico_y_elementos_filtrados(self) -> None:
        """Verifica que en la categoría de tarjetas solo aparecen sus elementos y el concepto se genera solo."""
        from datetime import date

        carlos = Usuario.objects.create_user(email="tarjeta@familia.com", password="password123")
        cat_tarjeta = Categoria.objects.create(nombre="Tarjetas de Crédito", tipo=Categoria.Tipo.GASTO)
        elem_visa = Elemento.objects.create(categoria=cat_tarjeta, nombre="Tarjeta Visa Oro")
        Elemento.objects.create(categoria=cat_tarjeta, nombre="Tarjeta Mastercard")

        cat_casa = Categoria.objects.create(nombre="Gastos Casa", tipo=Categoria.Tipo.GASTO)
        elem_luz = Elemento.objects.create(categoria=cat_casa, nombre="Electricidad")

        client = Client()
        client.force_login(carlos)

        # El desplegable de elementos solo ofrece los de la categoría de tarjetas
        response = client.get(reverse("finanzas:gasto_create"), {"categoria": cat_tarjeta.id})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(
            list(form.fields["elemento"].queryset.values_list("nombre", flat=True)),
            ["Tarjeta Mastercard", "Tarjeta Visa Oro"],
        )

        # El concepto se autogenera: liquidación del mes anterior (se paga el día 1 del mes siguiente)
        response = client.post(
            reverse("finanzas:gasto_create"),
            {
                "categoria": cat_tarjeta.id,
                "elemento": elem_visa.id,
                "monto": "510.00",
                "fecha": date(2026, 3, 1).isoformat(),
                "es_fijo": "",
                "notas": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        gasto = Gasto.objects.get(elemento=elem_visa)
        self.assertEqual(gasto.concepto, "Liquidación Tarjetas de Crédito (02/2026)")
        self.assertEqual(gasto.monto, Decimal("510.00"))

        # En el resto de categorías el concepto sigue siendo obligatorio
        response = client.post(
            reverse("finanzas:gasto_create"),
            {
                "categoria": cat_casa.id,
                "elemento": elem_luz.id,
                "monto": "50.00",
                "fecha": date.today().isoformat(),
                "es_fijo": "",
                "notas": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("concepto", response.context["form"].errors)

    def test_gasto_elemento_fijo_concepto_y_recurrencia_automaticas(self) -> None:
        """En un elemento recurrente no se pide concepto: se autogenera y el gasto queda marcado como fijo."""
        from datetime import date

        carlos = Usuario.objects.create_user(email="hipo@familia.com", password="password123")
        cat = Categoria.objects.create(nombre="Gastos Casa", tipo=Categoria.Tipo.GASTO)
        elem = Elemento.objects.create(categoria=cat, nombre="Hipoteca / Alquiler", es_fijo=True)

        client = Client()
        client.force_login(carlos)

        response = client.post(
            reverse("finanzas:gasto_create"),
            {
                "categoria": cat.id,
                "elemento": elem.id,
                "monto": "850.00",
                "fecha": date(2026, 3, 15).isoformat(),
                "concepto": "",
                "es_fijo": "",
                "notas": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        gasto = Gasto.objects.get(elemento=elem)
        self.assertEqual(gasto.concepto, "Cuota Hipoteca / Alquiler (03/2026)")
        self.assertTrue(gasto.es_fijo)

    def test_gasto_elemento_fijo_marca_recurrente_automatico(self) -> None:
        """Si el elemento ya es un compromiso fijo, el gasto se marca como recurrente sin preguntar."""
        carlos = Usuario.objects.create_user(email="fin@familia.com", password="password123")
        cat = Categoria.objects.create(nombre="Gastos Casa", tipo=Categoria.Tipo.GASTO)
        hipoteca = Elemento.objects.create(categoria=cat, nombre="Hipoteca / Alquiler", es_fijo=True)
        Elemento.objects.create(categoria=cat, nombre="Compra puntual", es_fijo=False)

        client = Client()
        client.force_login(carlos)

        response = client.get(reverse("finanzas:gasto_create"), {"elemento": hipoteca.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].fields["es_fijo"].initial)

        # Un elemento no fijo no fuerza el check de recurrencia
        no_fijo = Elemento.objects.get(nombre="Compra puntual")
        response = client.get(reverse("finanzas:gasto_create"), {"elemento": no_fijo.id})
        self.assertFalse(response.context["form"].fields["es_fijo"].initial)

        # El mapa del desplegable dependiente informa si cada elemento es fijo
        config = response.context["gasto_config"]["elementos_por_categoria"][str(cat.id)]
        self.assertEqual(
            {el["nombre"]: el["es_fijo"] for el in config},
            {"Compra puntual": False, "Hipoteca / Alquiler": True},
        )

    def test_elemento_finalizado_se_excluye_del_formulario_de_gasto(self) -> None:
        """Verifica que un elemento marcado como finalizado no se ofrezca para registrar nuevos gastos."""
        from datetime import date

        carlos = Usuario.objects.create_user(email="fin@familia.com", password="password123")
        cat, _ = Categoria.objects.get_or_create(
            nombre="Préstamos & Financiaciones",
            tipo=Categoria.Tipo.GASTO,
        )
        Elemento.objects.create(
            categoria=cat,
            nombre="Hipoteca / Alquiler",
            finalizado=True,
            fecha_finalizacion=date(2026, 5, 1),
        )
        Elemento.objects.create(categoria=cat, nombre="Préstamo Coche")

        client = Client()
        client.force_login(carlos)

        response = client.get(reverse("finanzas:gasto_create"), {"categoria": cat.id})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(
            list(form.fields["elemento"].queryset.values_list("nombre", flat=True)),
            ["Préstamo Coche"],
        )

        # La hipoteca finalizada tampoco aparece en el mapa de elementos del desplegable dependiente
        self.assertEqual(
            [el["nombre"] for el in response.context["gasto_config"]["elementos_por_categoria"].get(str(cat.id), [])],
            ["Préstamo Coche"],
        )



