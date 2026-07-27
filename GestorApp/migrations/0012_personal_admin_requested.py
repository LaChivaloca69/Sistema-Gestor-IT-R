from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("GestorApp", "0011_alter_compramaterial_estado_compra_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="personal",
            name="admin_requested",
            field=models.BooleanField(default=False, verbose_name="Solicita admin"),
        ),
    ]
