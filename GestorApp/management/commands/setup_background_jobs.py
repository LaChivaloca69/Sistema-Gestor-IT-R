"""Asegura schedules de django-q y/o dispara un job puntual."""

from django.core.management.base import BaseCommand

from GestorApp.job_queue import enqueue_recordatorios, enqueue_retencion
from GestorApp.schedules import ensure_default_schedules


class Command(BaseCommand):
    help = (
        "Configura schedules de background (retencion diaria, recordatorios 15m) "
        "y opcionalmente encola un job ahora."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-retencion",
            action="store_true",
            help="Encola retencion de historial ahora.",
        )
        parser.add_argument(
            "--run-recordatorios",
            action="store_true",
            help="Encola barrido de recordatorios operativos ahora.",
        )

    def handle(self, *args, **options):
        ok = ensure_default_schedules()
        if ok:
            self.stdout.write(self.style.SUCCESS("Schedules de django-q asegurados."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "No se pudieron asegurar schedules (migra django_q o revisa la app)."
                )
            )

        if options["run_retencion"]:
            result, mode = enqueue_retencion(accion="ambos")
            self.stdout.write(f"Retencion ({mode}): {result}")

        if options["run_recordatorios"]:
            result, mode = enqueue_recordatorios()
            self.stdout.write(f"Recordatorios ({mode}): {result}")
