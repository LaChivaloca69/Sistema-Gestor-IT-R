# Fase 4: consumibles stock por cantidad

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("GestorApp", "0044_equipo_padre_kit_periferico"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductoConsumible",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(max_length=40, unique=True, verbose_name="SKU / codigo")),
                ("nombre", models.CharField(max_length=160)),
                ("descripcion", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "unidad",
                    models.CharField(
                        choices=[
                            ("pza", "Pieza"),
                            ("caja", "Caja"),
                            ("ml", "Mililitro"),
                            ("L", "Litro"),
                            ("m", "Metro"),
                            ("rollo", "Rollo"),
                            ("otro", "Otro"),
                        ],
                        default="pza",
                        max_length=10,
                    ),
                ),
                ("stock_actual", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("stock_minimo", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                (
                    "costo_aproximado",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Costo unitario approx.",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "categoria",
                    models.ForeignKey(
                        limit_choices_to={"tipo": "Consumible"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="productos_consumibles",
                        to="GestorApp.categoriaequipo",
                    ),
                ),
                (
                    "proveedor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="productos_consumibles",
                        to="GestorApp.proveedor",
                    ),
                ),
                (
                    "ubicacion",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="productos_consumibles",
                        to="GestorApp.ubicacion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Producto consumible",
                "verbose_name_plural": "Productos consumibles",
                "ordering": ["nombre", "sku"],
            },
        ),
        migrations.CreateModel(
            name="MovimientoStock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "tipo_movimiento",
                    models.CharField(
                        choices=[
                            ("Entrada", "Entrada"),
                            ("Salida", "Salida"),
                            ("Ajuste", "Ajuste"),
                        ],
                        max_length=20,
                    ),
                ),
                ("cantidad", models.DecimalField(decimal_places=2, max_digits=12)),
                ("stock_antes", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("stock_despues", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("motivo", models.CharField(blank=True, max_length=255, null=True)),
                ("fecha_movimiento", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "orden_compra",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movimientos_stock",
                        to="GestorApp.ordencompra",
                    ),
                ),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movimientos",
                        to="GestorApp.productoconsumible",
                    ),
                ),
                (
                    "responsable",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movimientos_stock",
                        to="GestorApp.personal",
                    ),
                ),
            ],
            options={
                "verbose_name": "Movimiento de stock",
                "verbose_name_plural": "Movimientos de stock",
                "ordering": ["-fecha_movimiento", "-pk"],
            },
        ),
        migrations.AlterField(
            model_name="historialactividad",
            name="modulo",
            field=models.CharField(
                choices=[
                    ("ticket", "Tickets de soporte"),
                    ("seguimiento", "Seguimiento de tickets"),
                    ("equipo", "Equipos"),
                    ("asignacion", "Asignaciones de equipo"),
                    ("movimiento_equipo", "Movimientos de equipo"),
                    ("consumible", "Consumibles"),
                    ("personal", "Personal"),
                    ("mantenimiento", "Mantenimiento"),
                    ("orden_compra", "Ordenes de compra"),
                    ("bitacora", "Bitacora"),
                    ("sistema", "Sistema"),
                    ("gobierno", "Gobierno y roles"),
                    ("solicitud_equipo", "Solicitudes de equipo"),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
    ]
