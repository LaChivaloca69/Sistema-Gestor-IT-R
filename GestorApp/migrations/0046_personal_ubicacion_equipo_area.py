# Generated manually for fase 2: espacio fisico en personal y departamento en equipo.

from django.db import migrations, models
import django.db.models.deletion


def copiar_area_desde_asignacion_activa(apps, schema_editor):
    Equipo = apps.get_model("GestorApp", "Equipo")
    AsignacionEquipo = apps.get_model("GestorApp", "AsignacionEquipo")
    Personal = apps.get_model("GestorApp", "Personal")

    activas = (
        AsignacionEquipo.objects.filter(estado_asignacion="Activa")
        .select_related("equipo", "personal")
        .order_by("equipo_id", "-fecha_asignacion")
    )
    vistos = set()
    for asignacion in activas:
        equipo_id = asignacion.equipo_id
        if equipo_id in vistos:
            continue
        vistos.add(equipo_id)
        personal = asignacion.personal
        if not personal:
            continue
        personal = Personal.objects.filter(pk=personal.pk).first()
        if not personal:
            continue
        updates = {}
        if personal.area_id and not asignacion.equipo.area_id:
            updates["area_id"] = personal.area_id
        if personal.ubicacion_id and not asignacion.equipo.ubicacion_id:
            updates["ubicacion_id"] = personal.ubicacion_id
        if updates:
            Equipo.objects.filter(pk=equipo_id).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ("GestorApp", "0045_consumibles_stock"),
    ]

    operations = [
        migrations.AddField(
            model_name="personal",
            name="ubicacion",
            field=models.ForeignKey(
                blank=True,
                help_text="Puesto fijo del empleado. Vacio si no tiene escritorio asignado.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="GestorApp.ubicacion",
                verbose_name="Espacio fisico",
            ),
        ),
        migrations.AddField(
            model_name="equipo",
            name="area",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="GestorApp.area",
                verbose_name="Departamento",
            ),
        ),
        migrations.RunPython(
            copiar_area_desde_asignacion_activa,
            migrations.RunPython.noop,
        ),
    ]
