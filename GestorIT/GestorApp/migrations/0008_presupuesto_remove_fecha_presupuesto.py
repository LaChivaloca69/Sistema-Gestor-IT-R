from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0007_presupuesto_pdf_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="presupuesto",
            name="fecha_presupuesto",
        ),
    ]
