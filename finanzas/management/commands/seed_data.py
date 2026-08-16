"""Comando de gestión para popular la base de datos con datos de prueba realistas."""

import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from finanzas.models import Categoria, Elemento, Gasto, GastoEspecialTarjeta, Ingreso
from seguros.models import HistorialRenovacionSeguro, Seguro

Usuario = get_user_model()


class Command(BaseCommand):
    """Popula la base de datos con estructura jerárquica (Categoría -> Elemento -> Apuntes)."""

    help = "Genera datos de prueba completos con la jerarquía Categoría -> Elementos -> Apuntes."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
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
                "Gastos Casa",
                "home",
                "#015F78",
                "Compromisos y suministros de la vivienda habitual",
                [
                    ("Hipoteca / Alquiler", True, "home", "Cuota hipotecaria mensual"),
                    ("Electricidad", False, "zap", "Factura de luz Iberdrola / Endesa"),
                    ("Agua", False, "droplet", "Suministro de agua Canal Isabel II"),
                    ("Comunidad Propietarios", True, "building-2", "Cuota ordinaria de la comunidad de vecinos"),
                    ("Movistar / Fibra & Móvil", True, "wifi", "Internet fibra 1Gb + líneas móviles"),
                    ("Gas Natural", False, "flame", "Calefacción y agua caliente"),
                    ("Mantenimiento y Hogar", False, "hammer", "Pequeñas reparaciones y compras de casa"),
                ],
            ),
            (
                "Coches & Movilidad",
                "car",
                "#42D3F2",
                "Vehículos familiares, repostajes y desplazamientos",
                [
                    ("Préstamo Coche", True, "car", "Financiación bancaria vehículo"),
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
                    fuente=Ingreso.Fuente.NOMINA_TITULAR_1,
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
                    fuente=Ingreso.Fuente.NOMINA_TITULAR_2,
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
                        fuente=Ingreso.Fuente.NOMINA_TITULAR_1,
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
                        fuente=Ingreso.Fuente.RENDIMIENTOS_CAPITAL,
                        fecha=date(anio, mes, 28),
                        defaults={
                            "monto": Decimal("180.50"),
                            "descripcion": f"Dividendos Fondo Indexado T{mes//3}",
                        },
                    )

                # GASTOS FIJOS Y VARIABLES
                gastos_fijos_mensuales = [
                    ("Gastos Casa > Hipoteca / Alquiler", "Cuota Hipoteca BBVA", Decimal("780.00"), 1, titular1, True),
                    ("Gastos Casa > Comunidad Propietarios", "Recibo Comunidad Propietarios", Decimal("85.00"), 5, titular1, True),
                    ("Gastos Casa > Movistar / Fibra & Móvil", "Factura Movistar Fusión", Decimal("95.00"), 10, titular1, True),
                    ("Coches & Movilidad > Préstamo Coche", "Letra Préstamo Vehículo Santander", Decimal("220.00"), 5, titular1, True),
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

        # 4. Desgloses Especiales de Tarjetas de Crédito
        compras_tarjeta = [
            (titular1, "Visa Oro Carlos", GastoEspecialTarjeta.TipoComercio.SUPERMERCADO, "Mercadona Las Rozas", Decimal("134.50"), date(2026, 1, 10)),
            (titular1, "Visa Oro Carlos", GastoEspecialTarjeta.TipoComercio.GASOLINA, "Estación Repsol M-40", Decimal("72.80"), date(2026, 1, 14)),
            (titular1, "Visa Oro Carlos", GastoEspecialTarjeta.TipoComercio.RESTAURANTE_OCIO, "Restaurante La Tagliatella", Decimal("68.00"), date(2026, 1, 20)),
            (titular2, "Mastercard Familiar Elena", GastoEspecialTarjeta.TipoComercio.SUPERMERCADO, "Carrefour Majadahonda", Decimal("148.20"), date(2026, 1, 17)),
            (titular2, "Mastercard Familiar Elena", GastoEspecialTarjeta.TipoComercio.COMPRAS_ONLINE, "Amazon Prime Compras Hogar", Decimal("54.99"), date(2026, 1, 22)),
            (titular2, "Mastercard Familiar Elena", GastoEspecialTarjeta.TipoComercio.FARMACIA_SALUD, "Farmacia Central", Decimal("28.40"), date(2026, 1, 25)),
            (titular1, "Visa Oro Carlos", GastoEspecialTarjeta.TipoComercio.SUPERMERCADO, "Mercadona Las Rozas", Decimal("128.90"), date(2026, 2, 7)),
            (titular1, "Visa Oro Carlos", GastoEspecialTarjeta.TipoComercio.GASOLINA, "Cepsa A-6", Decimal("65.00"), date(2026, 2, 11)),
        ]

        for usr, tarj, tip, com, mon, fec in compras_tarjeta:
            GastoEspecialTarjeta.objects.get_or_create(
                usuario=usr,
                tarjeta=tarj,
                comercio=com,
                fecha=fec,
                defaults={"tipo_comercio": tip, "monto": mon},
            )

        self.stdout.write(self.style.SUCCESS("✓ Compras especiales de tarjeta registradas."))

        # 5. Pólizas de Seguros e Histórico de Renovaciones
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
            },
        )

        HistorialRenovacionSeguro.objects.get_or_create(
            seguro=seguro_auto_1,
            ejercicio_anio=2024,
            defaults={"prima_pagada": Decimal("440.00"), "fecha_renovacion": date(2024, 3, 15)},
        )
        HistorialRenovacionSeguro.objects.get_or_create(
            seguro=seguro_auto_1,
            ejercicio_anio=2025,
            defaults={"prima_pagada": Decimal("465.00"), "fecha_renovacion": date(2025, 3, 15)},
        )
        HistorialRenovacionSeguro.objects.get_or_create(
            seguro=seguro_auto_1,
            ejercicio_anio=2026,
            defaults={"prima_pagada": Decimal("485.50"), "fecha_renovacion": date(2026, 3, 15)},
        )

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
            },
        )

        HistorialRenovacionSeguro.objects.get_or_create(
            seguro=seguro_hogar,
            ejercicio_anio=2024,
            defaults={"prima_pagada": Decimal("275.00"), "fecha_renovacion": date(2024, 6, 1)},
        )
        HistorialRenovacionSeguro.objects.get_or_create(
            seguro=seguro_hogar,
            ejercicio_anio=2025,
            defaults={"prima_pagada": Decimal("285.00"), "fecha_renovacion": date(2025, 6, 1)},
        )
        HistorialRenovacionSeguro.objects.get_or_create(
            seguro=seguro_hogar,
            ejercicio_anio=2026,
            defaults={"prima_pagada": Decimal("295.00"), "fecha_renovacion": date(2026, 6, 1)},
        )

        self.stdout.write(self.style.SUCCESS("✓ Pólizas de seguros e histórico de renovaciones generados."))

        self.stdout.write(self.style.SUCCESS("\n========================================================================"))
        self.stdout.write(self.style.SUCCESS("🎉 ¡DATOS DE PRUEBA CARGADOS CON ÉXITO!"))
        self.stdout.write(self.style.SUCCESS("========================================================================"))
        self.stdout.write("Credenciales de acceso:")
        self.stdout.write("* Administrador: admin@familia.com  |  Clave: admin123")
        self.stdout.write("* Titular 1:     carlos@familia.com |  Clave: familiar123")
        self.stdout.write("* Titular 2:     elena@familia.com  |  Clave: familiar123")
        self.stdout.write(self.style.SUCCESS("========================================================================\n"))
