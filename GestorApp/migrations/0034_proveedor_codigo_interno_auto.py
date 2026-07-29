from django.db import migrations


def asignar_codigos_faltantes(apps, schema_editor):
    Proveedor = apps.get_model("GestorApp", "Proveedor")
    prefix = "PROV-"
    width = 6

    existentes = list(
        Proveedor.objects.exclude(codigo_interno__isnull=True)
        .exclude(codigo_interno="")
        .values_list("codigo_interno", flat=True)
    )
    next_number = 1
    for codigo in existentes:
        if isinstance(codigo, str) and codigo.startswith(prefix):
            suffix = codigo[len(prefix):]
            if suffix.isdigit():
                next_number = max(next_number, int(suffix) + 1)

    sin_codigo = Proveedor.objects.filter(codigo_interno__isnull=True) | Proveedor.objects.filter(
        codigo_interno=""
    )
    for proveedor in sin_codigo.order_by("pk"):
        proveedor.codigo_interno = f"{prefix}{next_number:0{width}d}"
        proveedor.save(update_fields=["codigo_interno"])
        next_number += 1


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0033_proveedor_campos_utilidad"),
    ]

    operations = [
        migrations.RunPython(asignar_codigos_faltantes, noop_reverse),
    ]
