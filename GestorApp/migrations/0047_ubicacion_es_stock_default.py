from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0046_personal_ubicacion_equipo_area"),
    ]

    operations = [
        migrations.AddField(
            model_name="ubicacion",
            name="es_stock_default",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Espacio al que regresan los equipos al devolverlos a stock.",
                verbose_name="Almacen / stock por defecto",
            ),
        ),
    ]
