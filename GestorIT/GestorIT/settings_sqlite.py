from .settings import *

# Configuracion local para pruebas rapidas sin depender de PostgreSQL.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
