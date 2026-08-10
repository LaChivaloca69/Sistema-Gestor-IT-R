from django.apps import AppConfig


class GestorappConfig(AppConfig):
    name = "GestorApp"

    def ready(self):
        from django.db.models.signals import post_migrate

        from .schedules import on_post_migrate_ensure_schedules

        post_migrate.connect(on_post_migrate_ensure_schedules, sender=self)
