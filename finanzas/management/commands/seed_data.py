"""Comando de gestión para popular la base de datos con datos de prueba realistas."""

import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from finanzas.models import (
    Categoria,
    CuentaAhorro,
    Elemento,
    Gasto,
    Ingreso,
    RegistroSaldoMensual,
)
from seguros.models import HistorialRenovacionSeguro, Seguro

Usuario = get_user_model()


class Command(BaseCommand):
    """Popula la base de datos con estructura jerárquica (Categoría -> Elemento -> Apuntes)."""

    help = "Genera datos de prueba completos con la jerarquía Categoría -> Elementos -> Apuntes."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Permite ejecutar aunque DEBUG esté desactivado (útil para la suite de tests).",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_data crea usuarios con contraseñas conocidas y solo puede ejecutarse en desarrollo (DEBUG=True)."
            )
        self.stdout.write(self.style.WARNING("🌱 Iniciando generación de datos de prueba..."))

        # 1. Crear Usuarios
        admin_user, _ = Usuario.objects.get_or_create(
            email="admin@familia.com",
            defaults={
                "first_name": "Administrador",
                "last_name": "Familiar",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        admin_user.set_password("admin123")
        admin_user.save()

        titular1, _ = Usuario.objects.get_or_create(
            email="carlos@familia.com",
            defaults={
                "first_name": "Carlos",
                "last_name": "García",
                "is_active": True,
            },
        )
        titular1.set_password("familiar123")
        titular1.save()

        titular2, _ = Usuario.objects.get_or_create(
            email="elena@familia.com",
            defaults={
                "first_name": "Elena",
                "last_name": "Martín",
                "is_active": True,
            },
        )
        titular2.set_password("familiar123")
        titular2.save()

        self.stdout.write(self.style.SUCCESS("✓ Usuarios de prueba creados (admin@familia.com / carlos@familia.com / elena@familia.com)."))

        # 2. Definir Estructura de Categorías y sus Elementos
        # Ingresos
        cat_ingreso, _ = Categoria.objects.get_or_create(
            nombre="Ingresos del Trabajo & Capital",
            tipo=Categoria.Tipo.INGRESO,
            defaults={
                "icono": "wallet",
                "color": "#3BB8DB",
                "descripcion": "Salarios, rendimientos financieros y entradas monetarias",
            },
        )

        elementos_ingreso_defs = [
            ("Nómina Carlos", True, "wallet", "Salario fijo mensual Titular 1"),
            ("Nómina Elena", True, "briefcase", "Salario fijo mensual Titular 2"),
            ("Pagas Extraordinarias", False, "gift", "Pagas extras semestrales"),
            ("Rendimientos de Inversión", False, "trending-up", "Fondos indexados y dividendos"),
            ("Otros Ingresos", False, "plus-circle", "Devoluciones fiscales o ventas particulares"),
        ]

        elementos_ingreso = {}
        for nom, fijo, ico, desc in elementos_ingreso_defs:
            elem, _ = Elemento.objects.get_or_create(
                categoria=cat_ingreso,
                nombre=nom,
                defaults={"es_fijo": fijo, "icono": ico, "descripcion": desc},
            )
            elementos_ingreso[nom] = elem

        # Gastos
        categorias_gasto_defs = [
            (
                "Tarjetas de Crédito",
                "credit-card",
                "#F59E0B",
                "Liquidaciones y cargos mensuales de tarjetas",
                [
                    ("Tarjeta Visa Oro", False, "credit-card", "Liquidación mensual Visa Oro"),
                    ("Tarjeta Mastercard", False, "credit-card", "Liquidación mensual Mastercard Familiar"),
                ],
            ),
            (
                "Gastos Casa",
                "home",
                "#015F78",
                "Compromisos y suministros de la vivienda habitual",
                [
                    ("Electricidad", False, "zap", "Factura de luz Iberdrola / Endesa"),
                    ("Agua", False, "droplet", "Suministro de agua Canal Isabel II"),
                    ("Comunidad Propietarios", True, "building-2", "Cuota ordinaria de la comunidad de vecinos"),
                    ("Movistar / Fibra & Móvil", True, "wifi", "Internet fibra 1Gb + líneas móviles"),
                    ("Gas Natural", False, "flame", "Calefacción y agua caliente"),
                    ("Mantenimiento y Hogar", False, "hammer", "Pequeñas reparaciones y compras de casa"),
                ],
            ),
            (
                "Préstamos & Financiaciones",
                "landmark",
                "#8B5CF6",
                "Cuotas de préstamos y financiaciones pagadas por domiciliación o transferencia",
                [
                    ("Hipoteca / Alquiler", True, "landmark", "Cuota hipotecaria mensual (se marca como finalizada al terminar de pagar)"),
                ],
            ),
            (
                "Coches & Movilidad",
                "car",
                "#42D3F2",
                "Vehículos familiares, repostajes y desplazamientos",
                [
                    ("Renting Coche", True, "car", "Renting con opción de compra o cambio de vehículo"),
                    ("Combustible / Gasolina", False, "fuel", "Repsol / Cepsa repostajes"),
                    ("Mantenimiento & Taller", False, "wrench", "Revisiones anuales, aceite y neumáticos"),
                    ("ITV & Impuestos", True, "file-text", "Impuesto municipal e ITV"),
                    ("Peajes & Parkings", False, "parking-square", "Aparcamientos y autopistas"),
                ],
            ),
            (
                "Seguros",
                "shield-check",
                "#2C92B8",
                "Pólizas de protección familiar, hogar y vehículos",
                [
                    ("Seguro Hogar", True, "home", "Póliza multirriesgo vivienda"),
                    ("Seguro Coche Principal", True, "car", "Póliza todo riesgo Carlos"),
                    ("Seguro Coche Secundario", True, "car", "Póliza terceros ampliado Elena"),
                    ("Seguro Salud Familiar", True, "heart-pulse", "Cuota médica Adeslas / Sanitas"),
                    ("Seguro de Vida", True, "shield", "Cobertura de amortización hipotecaria"),
                ],
            ),
            (
                "Alimentación & Supermercado",
                "shopping-cart",
                "#104E64",
                "Cesta de la compra, productos frescos y supermercado",
                [
                    ("Supermercado Semanal", False, "shopping-cart", "Compras en Mercadona, Carrefour o Lidl"),
                    ("Mercados y Frescos", False, "store", "Frutería, pescadería y carnicería local"),
                ],
            ),
            (
                "Salud & Médicos",
                "heart-pulse",
                "#3BB8DB",
                "Atención médica, medicamentos y cuidado personal",
                [
                    ("Farmacia & Medicamentos", False, "pill", "Gastos de botiquín y recetas"),
                    ("Dentista & Ortodoncia", False, "smile", "Revisiones y tratamientos bucodentales"),
                    ("Óptica & Especialistas", False, "glasses", "Gafas, lentillas y visitas privadas"),
                ],
            ),
            (
                "Ocio & Familia",
                "utensils",
                "#53EAFD",
                "Restauración, cultura, viajes y suscripciones",
                [
                    ("Restaurantes & Bares", False, "utensils", "Comidas y cenas fuera de casa"),
                    ("Cine, Conciertos & Cultura", False, "ticket", "Entradas espectáculos y eventos"),
                    ("Vacaciones & Escapadas", False, "plane", "Hoteles, billetes y viajes"),
                    ("Suscripciones Digitales", True, "tv", "Netflix, Spotify, Prime, etc."),
                ],
            ),
            (
                "Varios & Imprevistos",
                "folder",
                "#053345",
                "Ropa, regalos y compras extraordinarias",
                [
                    ("Ropa & Calzado", False, "shirt", "Moda y calzado familiar"),
                    ("Regalos & Celebraciones", False, "gift", "Cumpleaños, navidades y aniversarios"),
                    ("Gastos Varios", False, "more-horizontal", "Otros imprevistos no clasificados"),
                ],
            ),
        ]

        elementos_gasto = {}
        for nom_cat, ico_cat, color_cat, desc_cat, lista_elems in categorias_gasto_defs:
            cat, _ = Categoria.objects.get_or_create(
                nombre=nom_cat,
                tipo=Categoria.Tipo.GASTO,
                defaults={"icono": ico_cat, "color": color_cat, "descripcion": desc_cat},
            )
            for nom_e, fijo_e, ico_e, desc_e in lista_elems:
                elem, _ = Elemento.objects.get_or_create(
                    categoria=cat,
                    nombre=nom_e,
                    defaults={"es_fijo": fijo_e, "icono": ico_e, "descripcion": desc_e},
                )
                elementos_gasto[f"{nom_cat} > {nom_e}"] = elem

        self.stdout.write(self.style.SUCCESS("✓ Jerarquía completa de Categorías y Elementos creada."))

        # 3. Generar Histórico de Movimientos para 2025 y 2026
        anios = [2025, 2026]
        hoy = timezone.now().date()

        for anio in anios:
            limite_mes = 12 if anio < hoy.year else hoy.month
            for mes in range(1, limite_mes + 1):
                fecha_base = date(anio, mes, 5)

                # INGRESOS
                # Nómina Carlos
                Ingreso.objects.get_or_create(
                    usuario=titular1,
                    elemento=elementos_ingreso["Nómina Carlos"],
                    fecha=fecha_base,
                    defaults={
                        "monto": Decimal("2450.00"),
                        "descripcion": f"Nómina Carlos - {fecha_base.strftime('%B %Y')}",
                    },
                )

                # Nómina Elena
                Ingreso.objects.get_or_create(
                    usuario=titular2,
                    elemento=elementos_ingreso["Nómina Elena"],
                    fecha=fecha_base,
                    defaults={
                        "monto": Decimal("1920.00"),
                        "descripcion": f"Nómina Elena - {fecha_base.strftime('%B %Y')}",
                    },
                )

                # Paga extra en Junio y Diciembre
                if mes in [6, 12]:
                    Ingreso.objects.get_or_create(
                        usuario=titular1,
                        elemento=elementos_ingreso["Pagas Extraordinarias"],
                        fecha=date(anio, mes, 20),
                        defaults={
                            "monto": Decimal("2450.00"),
                            "descripcion": f"Paga Extraordinaria Carlos ({mes}/{anio})",
                        },
                    )

                # Rendimiento Inversiones trimestral
                if mes in [3, 6, 9, 12]:
                    Ingreso.objects.get_or_create(
                        usuario=titular1,
                        elemento=elementos_ingreso["Rendimientos de Inversión"],
                        fecha=date(anio, mes, 28),
                        defaults={
                            "monto": Decimal("180.50"),
                            "descripcion": f"Dividendos Fondo Indexado T{mes//3}",
                        },
                    )

                # GASTOS FIJOS Y VARIABLES
                gastos_fijos_mensuales = [
                    ("Tarjetas de Crédito > Tarjeta Visa Oro", "Liquidación Mensual Visa Oro", Decimal("510.00"), 1, titular1, False),
                    ("Tarjetas de Crédito > Tarjeta Mastercard", "Liquidación Mensual Mastercard", Decimal("340.00"), 1, titular2, False),
                    ("Préstamos & Financiaciones > Hipoteca / Alquiler", "Cuota Hipoteca BBVA", Decimal("780.00"), 1, titular1, True),
                    ("Gastos Casa > Comunidad Propietarios", "Recibo Comunidad Propietarios", Decimal("85.00"), 5, titular1, True),
                    ("Gastos Casa > Movistar / Fibra & Móvil", "Factura Movistar Fusión", Decimal("95.00"), 10, titular1, True),
                    ("Coches & Movilidad > Renting Coche", "Cuota Renting Vehículo", Decimal("220.00"), 5, titular1, True),
                    ("Seguros > Seguro Salud Familiar", "Cuota Médica Familiar Adeslas", Decimal("135.00"), 1, titular2, True),
                    ("Ocio & Familia > Suscripciones Digitales", "Netflix + Spotify Familiar", Decimal("27.99"), 15, titular2, True),
                ]

                for key_elem, concepto, monto, dia, usr, fijo in gastos_fijos_mensuales:
                    Gasto.objects.get_or_create(
                        usuario=usr,
                        elemento=elementos_gasto[key_elem],
                        fecha=date(anio, mes, dia),
                        concepto=concepto,
                        defaults={"monto": monto, "es_fijo": fijo},
                    )

                # Suministros Variables de Casa
                luz_monto = Decimal(f"{random.randint(65, 115)}.{random.randint(10, 99)}")
                Gasto.objects.get_or_create(
                    usuario=titular1,
                    elemento=elementos_gasto["Gastos Casa > Electricidad"],
                    fecha=date(anio, mes, 12),
                    concepto=f"Factura Luz Iberdrola ({mes}/{anio})",
                    defaults={"monto": luz_monto, "es_fijo": False},
                )

                if mes % 2 == 0:  # Agua bimensual
                    agua_monto = Decimal(f"{random.randint(45, 80)}.{random.randint(10, 99)}")
                    Gasto.objects.get_or_create(
                        usuario=titular1,
                        elemento=elementos_gasto["Gastos Casa > Agua"],
                        fecha=date(anio, mes, 18),
                        concepto=f"Recibo Agua Canal Isabel II ({mes}/{anio})",
                        defaults={"monto": agua_monto, "es_fijo": False},
                    )

                # Alimentación
                for sem in range(1, 5):
                    dia_compra = min(sem * 7, 28)
                    super_monto = Decimal(f"{random.randint(110, 160)}.{random.randint(10, 99)}")
                    Gasto.objects.get_or_create(
                        usuario=titular2,
                        elemento=elementos_gasto["Alimentación & Supermercado > Supermercado Semanal"],
                        fecha=date(anio, mes, dia_compra),
                        concepto=f"Compra Mercadona Semana {sem}",
                        defaults={"monto": super_monto, "es_fijo": False},
                    )

                # Gasolina
                gasolina_monto = Decimal(f"{random.randint(60, 90)}.{random.randint(10, 99)}")
                Gasto.objects.get_or_create(
                    usuario=titular1,
                    elemento=elementos_gasto["Coches & Movilidad > Combustible / Gasolina"],
                    fecha=date(anio, mes, 14),
                    concepto="Repostaje Gasolina Repsol",
                    defaults={"monto": gasolina_monto, "es_fijo": False},
                )

                # Restaurantes y Ocio
                rest_monto = Decimal(f"{random.randint(40, 95)}.{random.randint(10, 99)}")
                Gasto.objects.get_or_create(
                    usuario=titular1,
                    elemento=elementos_gasto["Ocio & Familia > Restaurantes & Bares"],
                    fecha=date(anio, mes, 22),
                    concepto="Cena fin de semana familiar",
                    defaults={"monto": rest_monto, "es_fijo": False},
                )

                # Farmacia
                if mes % 2 == 1:
                    farm_monto = Decimal(f"{random.randint(15, 45)}.{random.randint(10, 99)}")
                    Gasto.objects.get_or_create(
                        usuario=titular2,
                        elemento=elementos_gasto["Salud & Médicos > Farmacia & Medicamentos"],
                        fecha=date(anio, mes, 25),
                        concepto="Medicamentos y botiquín",
                        defaults={"monto": farm_monto, "es_fijo": False},
                    )

        self.stdout.write(self.style.SUCCESS("✓ Flujo completo de Ingresos y Gastos generado para 2025 y 2026."))

        # 4. Pólizas de Seguros vinculadas a Finanzas (Elementos & Gastos)
        seguro_auto_1, _ = Seguro.objects.get_or_create(
            numero_poliza="MAP-AUT-2024-8841",
            defaults={
                "usuario": titular1,
                "ramo": Seguro.Ramo.COCHE,
                "compania": "Mapfre Seguros",
                "bien_asegurado": "Peugeot 3008 (Matrícula 4412-LBC)",
                "periodicidad": Seguro.Periodicidad.ANUAL,
                "prima_actual": Decimal("485.50"),
                "prima_anterior": Decimal("465.00"),
                "fecha_inicio": date(2024, 3, 15),
                "fecha_vencimiento": date(2026, 3, 15),
                "gestor_nombre": "Javier Morales",
                "gestor_telefono": "912 345 678",
                "gestor_email": "jmorales@mapfre-agencia.es",
                "notas_negociacion": "Todo riesgo con franquicia de 150€. Comparativa realizada con Línea Directa (ofrecían 450€ pero sin coche de sustitución).",
            },
        )
        seguro_auto_1.sync_elemento()

        seguro_hogar, _ = Seguro.objects.get_or_create(
            numero_poliza="ALL-HOG-2023-9912",
            defaults={
                "usuario": titular1,
                "ramo": Seguro.Ramo.HOGAR,
                "compania": "Allianz",
                "bien_asegurado": "Vivienda Unifamiliar (C/ Rosales 14)",
                "periodicidad": Seguro.Periodicidad.ANUAL,
                "prima_actual": Decimal("295.00"),
                "prima_anterior": Decimal("285.00"),
                "fecha_inicio": date(2023, 6, 1),
                "fecha_vencimiento": date(2026, 6, 1),
                "gestor_nombre": "María Gómez",
                "gestor_telefono": "918 765 432",
                "gestor_email": "mgomez@allianz-seguros.com",
                "notas_negociacion": "Continente 180.000€, Contenido 45.000€. Incluye daños por agua y asistencia jurídica.",
            },
        )
        seguro_hogar.sync_elemento()

        seguro_salud, _ = Seguro.objects.get_or_create(
            numero_poliza="ADE-SAL-2024-5510",
            defaults={
                "usuario": titular2,
                "ramo": Seguro.Ramo.SALUD,
                "compania": "Adeslas",
                "bien_asegurado": "Asistencia Médica Familiar (Carlos, Elena y 2 Hijos)",
                "periodicidad": Seguro.Periodicidad.MENSUAL,
                "prima_actual": Decimal("135.00"),
                "prima_anterior": Decimal("128.00"),
                "fecha_inicio": date(2024, 1, 1),
                "fecha_vencimiento": date(2026, 12, 31),
                "gestor_nombre": "Adeslas Atención Cliente",
                "gestor_telefono": "900 505 040",
                "notas_negociacion": "Cuota mensual de 135€ para 4 asegurados sin copagos. Incluye dental básico.",
            },
        )
        seguro_salud.sync_elemento()

        seguro_vida, _ = Seguro.objects.get_or_create(
            numero_poliza="STA-VID-2022-7733",
            defaults={
                "usuario": titular1,
                "ramo": Seguro.Ramo.VIDA,
                "compania": "Santa Lucía",
                "bien_asegurado": "Amortización Préstamo Hipotecario",
                "periodicidad": Seguro.Periodicidad.ANUAL,
                "prima_actual": Decimal("198.00"),
                "prima_anterior": Decimal("190.00"),
                "fecha_inicio": date(2022, 10, 10),
                "fecha_vencimiento": date(2026, 10, 10),
                "notas_negociacion": "Vinculado a la hipoteca. Cobertura de fallecimiento e invalidez absoluta.",
            },
        )
        seguro_vida.sync_elemento()

        # Historial de renovaciones archivadas
        for seg, hists in [
            (seguro_auto_1, [(2024, Decimal("440.00"), date(2024, 3, 15)), (2025, Decimal("465.00"), date(2025, 3, 15)), (2026, Decimal("485.50"), date(2026, 3, 15))]),
            (seguro_hogar, [(2024, Decimal("275.00"), date(2024, 6, 1)), (2025, Decimal("285.00"), date(2025, 6, 1)), (2026, Decimal("295.00"), date(2026, 6, 1))]),
            (seguro_vida, [(2024, Decimal("182.00"), date(2024, 10, 10)), (2025, Decimal("190.00"), date(2025, 10, 10)), (2026, Decimal("198.00"), date(2026, 10, 10))]),
        ]:
            for an, mon, fec in hists:
                HistorialRenovacionSeguro.objects.get_or_create(
                    seguro=seg,
                    ejercicio_anio=an,
                    defaults={"prima_pagada": mon, "fecha_renovacion": fec},
                )

        # Generar apuntes de Gasto reales para los seguros en 2025 y 2026
        # 1. Seguro Auto (Marzo)
        Gasto.objects.get_or_create(
            usuario=titular1,
            elemento=seguro_auto_1.elemento,
            fecha=date(2025, 3, 15),
            concepto="Recibo Anual Mapfre Seguros - Peugeot 3008",
            defaults={"monto": Decimal("465.00"), "es_fijo": True, "notas": "Renovación ejercicio 2025"},
        )
        Gasto.objects.get_or_create(
            usuario=titular1,
            elemento=seguro_auto_1.elemento,
            fecha=date(2026, 3, 15),
            concepto="Recibo Anual Mapfre Seguros - Peugeot 3008",
            defaults={"monto": Decimal("485.50"), "es_fijo": True, "notas": "Renovación ejercicio 2026 (+4.41%)"},
        )

        # 2. Seguro Hogar (Junio)
        Gasto.objects.get_or_create(
            usuario=titular1,
            elemento=seguro_hogar.elemento,
            fecha=date(2025, 6, 1),
            concepto="Recibo Anual Allianz Seguros Hogar",
            defaults={"monto": Decimal("285.00"), "es_fijo": True, "notas": "Renovación anual vivienda 2025"},
        )
        Gasto.objects.get_or_create(
            usuario=titular1,
            elemento=seguro_hogar.elemento,
            fecha=date(2026, 6, 1),
            concepto="Recibo Anual Allianz Seguros Hogar",
            defaults={"monto": Decimal("295.00"), "es_fijo": True, "notas": "Renovación anual vivienda 2026 (+3.51%)"},
        )

        # 3. Seguro Salud (Mensual)
        for an in [2025, 2026]:
            lim_m = 12 if an < hoy.year else hoy.month
            mon_salud = Decimal("128.00") if an == 2025 else Decimal("135.00")
            for m in range(1, lim_m + 1):
                Gasto.objects.get_or_create(
                    usuario=titular2,
                    elemento=seguro_salud.elemento,
                    fecha=date(an, m, 1),
                    concepto=f"Cuota Mensual Adeslas Salud ({m}/{an})",
                    defaults={"monto": mon_salud, "es_fijo": True},
                )

        # 4. Seguro Vida (Octubre)
        Gasto.objects.get_or_create(
            usuario=titular1,
            elemento=seguro_vida.elemento,
            fecha=date(2025, 10, 10),
            concepto="Recibo Anual Seguro Vida Hipoteca Santa Lucía",
            defaults={"monto": Decimal("190.00"), "es_fijo": True},
        )
        if hoy.month >= 10 or hoy.year > 2026:
            Gasto.objects.get_or_create(
                usuario=titular1,
                elemento=seguro_vida.elemento,
                fecha=date(2026, 10, 10),
                concepto="Recibo Anual Seguro Vida Hipoteca Santa Lucía",
                defaults={"monto": Decimal("198.00"), "es_fijo": True},
            )

        self.stdout.write(self.style.SUCCESS("✓ Pólizas de seguros, elementos contables vinculados y gastos generados con éxito."))

        # 5. Cuentas de Ahorro y Saldos Mensuales Consolidados
        cuenta_emergencia, _ = CuentaAhorro.objects.get_or_create(
            nombre="Fondo de Emergencia Familiar",
            defaults={
                "usuario": titular1,
                "entidad": "MyInvestor",
                "tipo": CuentaAhorro.Tipo.FONDO_EMERGENCIA,
                "color": "#3BB8DB",
                "icono": "shield-check",
                "numero_cuenta_iban": "ES44 0000 1111 2222 3333",
                "objetivo_monto": Decimal("15000.00"),
                "notas": "Fondo para imprevistos equivalente a 6 meses de gastos fijos. Remunerada al 2.50% TAE.",
            },
        )

        cuenta_vacaciones, _ = CuentaAhorro.objects.get_or_create(
            nombre="Hucha Vacaciones & Viajes",
            defaults={
                "usuario": titular2,
                "entidad": "BBVA",
                "tipo": CuentaAhorro.Tipo.AHORRO_OBJETIVO,
                "color": "#10B981",
                "icono": "plane",
                "numero_cuenta_iban": "ES98 0182 4444 5555 6666",
                "objetivo_monto": Decimal("3500.00"),
                "notas": "Ahorro programado mensual para las vacaciones de verano e invierno.",
            },
        )

        cuenta_indexados, _ = CuentaAhorro.objects.get_or_create(
            nombre="Cartera Fondos Indexados",
            defaults={
                "usuario": titular1,
                "entidad": "Indexa Capital",
                "tipo": CuentaAhorro.Tipo.INVERSION,
                "color": "#8B5CF6",
                "icono": "trending-up",
                "numero_cuenta_iban": "ES21 0081 7777 8888 9999",
                "objetivo_monto": Decimal("30000.00"),
                "notas": "Inversión a largo plazo (Perfil 8/10). Aportación periódica mensual de 250€.",
            },
        )

        cuenta_remunerada, _ = CuentaAhorro.objects.get_or_create(
            nombre="Cuenta Remunerada Ahorro",
            defaults={
                "usuario": titular2,
                "entidad": "Trade Republic",
                "tipo": CuentaAhorro.Tipo.CUENTA_REMUNERADA,
                "color": "#F59E0B",
                "icono": "landmark",
                "numero_cuenta_iban": "DE89 0000 9999 1111 2222",
                "objetivo_monto": Decimal("10000.00"),
                "notas": "Cuenta de ahorro con liquidación mensual de intereses al 3.25% TAE.",
            },
        )

        # Saldos mensuales históricos en 2025
        saldos_2025 = {
            cuenta_emergencia: [
                (1, Decimal("10000.00")), (2, Decimal("10300.00")), (3, Decimal("10650.00")), (4, Decimal("10950.00")),
                (5, Decimal("11250.00")), (6, Decimal("11800.00")), (7, Decimal("12100.00")), (8, Decimal("12400.00")),
                (9, Decimal("12700.00")), (10, Decimal("13000.00")), (11, Decimal("13300.00")), (12, Decimal("13800.00")),
            ],
            cuenta_vacaciones: [
                (1, Decimal("600.00")), (2, Decimal("900.00")), (3, Decimal("1200.00")), (4, Decimal("1500.00")),
                (5, Decimal("1800.00")), (6, Decimal("2600.00")), (7, Decimal("3200.00")), (8, Decimal("800.00")),
                (9, Decimal("1100.00")), (10, Decimal("1400.00")), (11, Decimal("1700.00")), (12, Decimal("2000.00")),
            ],
            cuenta_indexados: [
                (1, Decimal("14500.00")), (2, Decimal("14900.00")), (3, Decimal("15350.00")), (4, Decimal("15700.00")),
                (5, Decimal("16200.00")), (6, Decimal("16750.00")), (7, Decimal("17100.00")), (8, Decimal("17500.00")),
                (9, Decimal("17950.00")), (10, Decimal("18400.00")), (11, Decimal("18900.00")), (12, Decimal("19500.00")),
            ],
            cuenta_remunerada: [
                (1, Decimal("4000.00")), (2, Decimal("4200.00")), (3, Decimal("4500.00")), (4, Decimal("4800.00")),
                (5, Decimal("5000.00")), (6, Decimal("5300.00")), (7, Decimal("5600.00")), (8, Decimal("5900.00")),
                (9, Decimal("6200.00")), (10, Decimal("6500.00")), (11, Decimal("6800.00")), (12, Decimal("7200.00")),
            ],
        }

        for cta, saldos_mes in saldos_2025.items():
            for m, sld in saldos_mes:
                RegistroSaldoMensual.objects.get_or_create(
                    cuenta=cta,
                    anio=2025,
                    mes=m,
                    defaults={"saldo": sld},
                )

        # Saldos mensuales en 2026 (hasta mes actual o mes 8)
        lim_m_2026 = 12 if hoy.year > 2026 else min(hoy.month, 12)
        saldos_2026 = {
            cuenta_emergencia: [
                (1, Decimal("14100.00")), (2, Decimal("14400.00")), (3, Decimal("14700.00")), (4, Decimal("15000.00")),
                (5, Decimal("15300.00")), (6, Decimal("15600.00")), (7, Decimal("15900.00")), (8, Decimal("16200.00")),
                (9, Decimal("16500.00")), (10, Decimal("16800.00")), (11, Decimal("17100.00")), (12, Decimal("17500.00")),
            ],
            cuenta_vacaciones: [
                (1, Decimal("2300.00")), (2, Decimal("2600.00")), (3, Decimal("2900.00")), (4, Decimal("3200.00")),
                (5, Decimal("3500.00")), (6, Decimal("4200.00")), (7, Decimal("4800.00")), (8, Decimal("1200.00")),
                (9, Decimal("1500.00")), (10, Decimal("1800.00")), (11, Decimal("2100.00")), (12, Decimal("2400.00")),
            ],
            cuenta_indexados: [
                (1, Decimal("19950.00")), (2, Decimal("20400.00")), (3, Decimal("20850.00")), (4, Decimal("21300.00")),
                (5, Decimal("21800.00")), (6, Decimal("22300.00")), (7, Decimal("22800.00")), (8, Decimal("23350.00")),
                (9, Decimal("23900.00")), (10, Decimal("24500.00")), (11, Decimal("25100.00")), (12, Decimal("25700.00")),
            ],
            cuenta_remunerada: [
                (1, Decimal("7500.00")), (2, Decimal("7800.00")), (3, Decimal("8100.00")), (4, Decimal("8400.00")),
                (5, Decimal("8700.00")), (6, Decimal("9000.00")), (7, Decimal("9300.00")), (8, Decimal("9600.00")),
                (9, Decimal("9900.00")), (10, Decimal("10200.00")), (11, Decimal("10500.00")), (12, Decimal("10800.00")),
            ],
        }

        for cta, saldos_mes in saldos_2026.items():
            for m, sld in saldos_mes:
                if m <= lim_m_2026:
                    RegistroSaldoMensual.objects.get_or_create(
                        cuenta=cta,
                        anio=2026,
                        mes=m,
                        defaults={"saldo": sld},
                    )

        self.stdout.write(self.style.SUCCESS("✓ Cuentas de ahorro y registros de saldos mensuales generados."))

        self.stdout.write(self.style.SUCCESS("\n========================================================================"))
        self.stdout.write(self.style.SUCCESS("🎉 ¡DATOS DE PRUEBA CARGADOS CON ÉXITO!"))
        self.stdout.write(self.style.SUCCESS("========================================================================"))
        self.stdout.write("Credenciales de acceso:")
        self.stdout.write("* Administrador: admin@familia.com  |  Clave: admin123")
        self.stdout.write("* Titular 1:     carlos@familia.com |  Clave: familiar123")
        self.stdout.write("* Titular 2:     elena@familia.com  |  Clave: familiar123")
        self.stdout.write(self.style.SUCCESS("========================================================================\n"))

