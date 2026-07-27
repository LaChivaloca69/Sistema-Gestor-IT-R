# Generated manually for orden de compra unificada

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GestorApp', '0027_plantilladocumento_presupuesto_orden_compra_valores_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='presupuesto',
            name='orden_compra_plantilla',
        ),
        migrations.DeleteModel(
            name='DetalleCompraMaterial',
        ),
        migrations.DeleteModel(
            name='DetallePresupuesto',
        ),
        migrations.DeleteModel(
            name='CompraMaterial',
        ),
        migrations.DeleteModel(
            name='Presupuesto',
        ),
        migrations.CreateModel(
            name='OrdenCompra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folio_orden', models.CharField(blank=True, max_length=30, unique=True)),
                ('origen', models.CharField(choices=[('CREADO', 'Creado en sistema'), ('SUBIDO', 'Subido existente')], default='CREADO', max_length=10)),
                ('fecha', models.DateField(blank=True, default=django.utils.timezone.now, null=True)),
                ('tipo_moneda', models.CharField(blank=True, choices=[('MXN', 'Pesos (MXN)'), ('USD', 'Dolares (USD)')], default='MXN', max_length=3)),
                ('iva_opcion', models.CharField(blank=True, choices=[('8', '8%'), ('16', '16%'), ('OTRO', 'Otro')], default='16', max_length=4)),
                ('iva_porcentaje', models.DecimalField(decimal_places=2, default=16, max_digits=5)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('iva_monto', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('comentarios', models.TextField(blank=True, null=True)),
                ('notas', models.CharField(blank=True, max_length=255, null=True)),
                ('estado', models.CharField(choices=[('Borrador', 'Borrador'), ('En Proceso', 'En Proceso'), ('Terminado', 'Terminado'), ('Cancelado', 'Cancelado')], default='Borrador', max_length=30)),
                ('archivo_pdf', models.FileField(blank=True, null=True, upload_to='ordenes_compra')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('elaborado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordenes_compra_elaboradas', to=settings.AUTH_USER_MODEL)),
                ('plantilla', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordenes_compra', to='GestorApp.plantilladocumento')),
                ('proveedor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordenes_compra', to='GestorApp.proveedor')),
            ],
            options={
                'verbose_name': 'Orden de compra',
                'verbose_name_plural': 'Ordenes de compra',
                'ordering': ['-creado_en', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='DetalleOrdenCompra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_producto', models.CharField(blank=True, max_length=80, null=True)),
                ('descripcion', models.CharField(max_length=255)),
                ('cantidad', models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ('precio_unitario', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('importe', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('orden', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='GestorApp.ordencompra')),
            ],
            options={
                'verbose_name': 'Detalle de orden de compra',
                'verbose_name_plural': 'Detalles de orden de compra',
                'ordering': ['pk'],
            },
        ),
    ]
