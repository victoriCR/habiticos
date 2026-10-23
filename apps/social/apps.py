from django.apps import AppConfig


class SocialConfig(AppConfig):
    name = "apps.social"
    label = "social"
    verbose_name = "Comunidad"

    def ready(self):
        # Al marcar o desmarcar un habitico público se crea o quita la tarjeta del día
        from . import signals  # noqa: F401
