from django.db import migrations, models


ROLE_USUARIO = "Usuario"
ROLE_TECNICO = "Tecnico IT"
ROLE_ADMIN = "Administrador"


def crear_grupos_y_migrar_usuarios(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")

    groups = {}
    for name in (ROLE_USUARIO, ROLE_TECNICO, ROLE_ADMIN):
        group, _ = Group.objects.get_or_create(name=name)
        groups[name] = group

    for user in User.objects.all().iterator():
        user.groups.remove(*groups.values())
        if user.is_superuser or user.is_staff:
            user.groups.add(groups[ROLE_ADMIN])
        else:
            user.groups.add(groups[ROLE_USUARIO])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("GestorApp", "0031_ticketit_asignado_a_flujo_estados"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ticketit",
            name="tipo_ticket",
            field=models.CharField(
                choices=[
                    ("ADMINISTRACION", "ADMINISTRACION"),
                    ("BPCS", "BPCS"),
                    ("HARDWARE", "HARDWARE"),
                    ("HELPDESK", "HELPDESK"),
                    ("TELEFONIA", "TELEFONIA"),
                    ("SOFTWARE", "SOFTWARE"),
                    ("MANTENIMIENTO", "MANTENIMIENTO"),
                ],
                default="HELPDESK",
                max_length=30,
            ),
        ),
        migrations.RunPython(crear_grupos_y_migrar_usuarios, noop_reverse),
    ]
