from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0004_ticketit_prioridad"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipo",
            name="imagen",
            field=models.ImageField(blank=True, null=True, upload_to="equipos"),
        ),
    ]
