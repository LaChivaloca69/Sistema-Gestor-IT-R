from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0006_ticketit_imagen"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="presupuesto",
            name="impuestos",
        ),
        migrations.RemoveField(
            model_name="presupuesto",
            name="subtotal",
        ),
        migrations.RemoveField(
            model_name="presupuesto",
            name="total",
        ),
        migrations.AddField(
            model_name="presupuesto",
            name="archivo_pdf",
            field=models.FileField(blank=True, null=True, upload_to="presupuestos"),
        ),
        migrations.AddField(
            model_name="presupuesto",
            name="fecha_compra",
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name="presupuesto",
            name="numero_importacion",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="presupuesto",
            name="numero_pedimiento",
            field=models.CharField(max_length=50, null=True),
        ),
    ]
