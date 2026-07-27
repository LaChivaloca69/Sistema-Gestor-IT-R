"""Aplica la politica de retencion del historial (archivar / purgar).

Ejemplos:
  python manage.py limpiar_historial --dry-run
  python manage.py limpiar_historial
  python manage.py limpiar_historial --solo-archivar
  python manage.py limpiar_historial --solo-purgar
"""
from django.core.management.base import BaseCommand

from GestorApp import historial


class Command(BaseCommand):
    help = (
        "Archiva y/o purga registros del historial segun HISTORIAL_RETENCION "
        "en settings.py."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo cuenta cuantos registros se afectarian, sin modificar la BD.",
        )
        parser.add_argument(
            "--solo-archivar",
            action="store_true",
            help="Solo ejecuta el paso de archivo (no purga).",
        )
        parser.add_argument(
            "--solo-purgar",
            action="store_true",
            help="Solo ejecuta el paso de purga (no archiva).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        solo_archivar = options["solo_archivar"]
        solo_purgar = options["solo_purgar"]

        if solo_archivar and solo_purgar:
            self.stderr.write(self.style.ERROR("No combines --solo-archivar y --solo-purgar."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se modificara la base de datos."))

        if solo_purgar:
            resultado = {"archivo": {"omitido": True}, "purga": historial.purgar_historial(dry_run=dry_run)}
        elif solo_archivar:
            resultado = {"archivo": historial.archivar_historial(dry_run=dry_run), "purga": {"omitido": True}}
        else:
            resultado = historial.aplicar_retencion(dry_run=dry_run)

        archivo = resultado.get("archivo") or {}
        purga = resultado.get("purga") or {}
        self.stdout.write(
            f"Archivados: {archivo.get('archivados', 0)}"
            + (" (simulado)" if archivo.get("dry_run") else "")
            + (f" [{archivo.get('omitido')}]" if archivo.get("omitido") else "")
        )
        self.stdout.write(
            f"Purgados: {purga.get('purgados', 0)}"
            + (" (simulado)" if purga.get("dry_run") else "")
            + (f" [{purga.get('omitido')}]" if purga.get("omitido") else "")
        )
        if resultado.get("config"):
            cfg = resultado["config"]
            self.stdout.write(
                f"Config: modo={cfg['modo']}, dias_activo={cfg['dias_activo']}, "
                f"dias_archivo={cfg['dias_archivo']}, proteger_criticos={cfg['proteger_criticos']}"
            )
        self.stdout.write(self.style.SUCCESS("Retencion de historial aplicada."))
