from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0009_personal_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="compramaterial",
            name="subtotal",
        ),
        migrations.RemoveField(
            model_name="compramaterial",
            name="impuestos",
        ),
        migrations.RemoveField(
            model_name="compramaterial",
            name="total",
        ),
    ]
