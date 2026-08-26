# Generated manually for Fase 1 inventario por tipo

from django.db import migrations, models


def reclasificar_categorias(apps, schema_editor):
    CategoriaEquipo = apps.get_model("GestorApp", "CategoriaEquipo")

    periferico_keys = (
        "monitor",
        "pantalla",
        "teclado",
        "mouse",
        "raton",
        "cable",
        "patch",
        "ram",
        "memoria",
        "ssd",
        "hdd",
        "disco",
        "almacenamiento",
        "headset",
        "audifono",
        "auricular",
        "webcam",
        "camara web",
        "dock",
        "periferic",
        "accesorio",
        "gpu",
        "fuente",
        "adaptador",
    )
    herramienta_keys = (
        "herramienta",
        "tester",
        "crimp",
        "taladro",
        "destornill",
        "pinza",
        "multimetro",
        "maletin",
    )
    consumible_keys = (
        "consumible",
        "alcohol",
        "isopropil",
        "toalla",
        "toner",
        "tinta",
        "terminal rj",
        "limpia",
        "quimico",
    )
    equipo_keys = (
        "laptop",
        "notebook",
        "desktop",
        "pc",
        "computadora",
        "impresora",
        "multifuncional",
        "router",
        "switch",
        "accesspoint",
        "access point",
        "ups",
        "gabinete",
        "servidor",
        "server",
        "tablet",
        "escaner",
        "scanner",
        "plotter",
        "telefono",
        "celular",
    )

    def infer(nombre):
        text = (nombre or "").strip().lower()
        if not text:
            return "Equipo"
        if any(k in text for k in consumible_keys):
            return "Consumible"
        if any(k in text for k in herramienta_keys):
            return "Herramienta"
        if any(k in text for k in periferico_keys):
            return "Periferico"
        if any(k in text for k in equipo_keys):
            return "Equipo"
        return "Equipo"

    for cat in CategoriaEquipo.objects.all():
        nuevo = infer(cat.nombre_categoria)
        if cat.tipo != nuevo:
            cat.tipo = nuevo
            cat.save(update_fields=["tipo"])

    seeds = [
        ("Laptop", "Equipo", "Computadora portatil"),
        ("Desktop", "Equipo", "PC de escritorio"),
        ("Impresora", "Equipo", "Impresora o multifuncional"),
        ("Monitor", "Periferico", "Pantalla / monitor"),
        ("Teclado", "Periferico", "Teclado"),
        ("Mouse", "Periferico", "Mouse / raton"),
        ("Memoria RAM", "Periferico", "Modulo de memoria RAM"),
        ("Almacenamiento", "Periferico", "SSD / HDD"),
        ("Herramienta", "Herramienta", "Herramienta de taller IT"),
        ("Cable", "Consumible", "Cables a granel / stock"),
        ("Limpieza", "Consumible", "Alcohol, toallas y similares"),
    ]
    existing = {
        (c.nombre_categoria or "").strip().lower()
        for c in CategoriaEquipo.objects.all()
    }
    for nombre, tipo, desc in seeds:
        key = nombre.lower()
        if key in existing:
            continue
        if any(key == e or key in e or e in key for e in existing):
            continue
        CategoriaEquipo.objects.create(
            nombre_categoria=nombre,
            descripcion_categoria=desc,
            tipo=tipo,
            activo=True,
        )
        existing.add(key)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0042_comentario_ticket"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="categoriaequipo",
            options={
                "ordering": ["tipo", "nombre_categoria"],
                "verbose_name": "Categoria de inventario",
                "verbose_name_plural": "Categorias de inventario",
            },
        ),
        migrations.AddField(
            model_name="categoriaequipo",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("Equipo", "Equipo"),
                    ("Periferico", "Periferico"),
                    ("Herramienta", "Herramienta"),
                    ("Consumible", "Consumible"),
                ],
                db_index=True,
                default="Equipo",
                max_length=20,
                verbose_name="Tipo de inventario",
            ),
        ),
        migrations.RunPython(reclasificar_categorias, noop_reverse),
    ]
