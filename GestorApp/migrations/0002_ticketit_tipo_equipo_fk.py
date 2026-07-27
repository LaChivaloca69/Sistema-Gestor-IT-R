from django.db import migrations, models
import django.db.models.deletion


def map_tipo_equipo_to_categoria(apps, schema_editor):
    TicketIT = apps.get_model("GestorApp", "TicketIT")
    CategoriaEquipo = apps.get_model("GestorApp", "CategoriaEquipo")
    db_alias = schema_editor.connection.alias

    values = (
        TicketIT.objects.using(db_alias)
        .exclude(tipo_equipo__isnull=True)
        .exclude(tipo_equipo__exact="")
        .values_list("tipo_equipo", flat=True)
        .distinct()
    )

    for value in values:
        categoria = (
            CategoriaEquipo.objects.using(db_alias)
            .filter(nombre_categoria__iexact=value)
            .first()
        )
        if not categoria:
            categoria = CategoriaEquipo.objects.using(db_alias).create(
                nombre_categoria=value,
                activo=True,
            )

        TicketIT.objects.using(db_alias).filter(tipo_equipo=value).update(
            tipo_equipo_fk=categoria
        )


def reverse_map_categoria_to_tipo_equipo(apps, schema_editor):
    TicketIT = apps.get_model("GestorApp", "TicketIT")
    db_alias = schema_editor.connection.alias

    for ticket in TicketIT.objects.using(db_alias).select_related("tipo_equipo_fk"):
        if ticket.tipo_equipo_fk:
            ticket.tipo_equipo = ticket.tipo_equipo_fk.nombre_categoria
        else:
            ticket.tipo_equipo = None
        ticket.save(update_fields=["tipo_equipo"])


class Migration(migrations.Migration):
    dependencies = [
        ("GestorApp", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticketit",
            name="tipo_equipo_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="GestorApp.categoriaequipo",
            ),
        ),
        migrations.RunPython(
            map_tipo_equipo_to_categoria,
            reverse_code=reverse_map_categoria_to_tipo_equipo,
        ),
        migrations.RemoveField(
            model_name="ticketit",
            name="tipo_equipo",
        ),
        migrations.RenameField(
            model_name="ticketit",
            old_name="tipo_equipo_fk",
            new_name="tipo_equipo",
        ),
    ]
