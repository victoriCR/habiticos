from django.apps import AppConfig


class HabitosConfig(AppConfig):
    name = "apps.habitos"
    label = "habitos"  # el de siempre: así se llaman sus tablas y migraciones
    verbose_name = "Habiticos"  # título de la sección en /admin/
