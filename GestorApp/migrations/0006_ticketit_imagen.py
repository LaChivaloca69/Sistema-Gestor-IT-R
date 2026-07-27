from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0005_equipo_imagen"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="ticketit",
            name="imagen_url",
        ),
        migrations.AddField(
            model_name="ticketit",
            name="imagen",
            field=models.ImageField(blank=True, null=True, upload_to="support"),
        ),
    ]
