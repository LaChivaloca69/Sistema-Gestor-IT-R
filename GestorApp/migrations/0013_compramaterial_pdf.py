from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("GestorApp", "0012_personal_admin_requested"),
    ]

    operations = [
        migrations.AddField(
            model_name="compramaterial",
            name="archivo_pdf",
            field=models.FileField(blank=True, null=True, upload_to="compras_material"),
        ),
    ]
