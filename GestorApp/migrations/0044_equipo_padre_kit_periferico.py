# Fase 2: kit equipo-periferico

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0043_categoriaequipo_tipo_inventario"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipo",
            name="equipo_padre",
            field=models.ForeignKey(
                blank=True,
                help_text="Solo perifericos: maquina a la que estan vinculados.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="perifericos",
                to="GestorApp.equipo",
                verbose_name="Equipo padre",
            ),
        ),
        migrations.AlterField(
            model_name="movimientoequipo",
            name="tipo_movimiento",
            field=models.CharField(
                choices=[
                    ("Dada de alta", "Dada de alta"),
                    ("Dada de baja", "Dada de baja"),
                    ("Asignacion de equipo", "Asignacion de equipo"),
                    ("Cambio de asignacion", "Cambio de asignacion"),
                    ("En mantenimiento", "En mantenimiento"),
                    ("Cambio de ubicacion", "Cambio de ubicacion"),
                    ("Vincular periferico", "Vincular periferico"),
                    ("Desvincular periferico", "Desvincular periferico"),
                    ("Reemplazar periferico", "Reemplazar periferico"),
                ],
                max_length=40,
            ),
        ),
    ]
