from django.apps import AppConfig


class PerfilesConfig(AppConfig):
    name = "apps.perfiles"
    label = "perfiles"
    verbose_name = "Perfiles"

    def ready(self):
        # Conecta las señales (como cerrar la sesión a medianoche)
        from . import signals  # noqa: F401
