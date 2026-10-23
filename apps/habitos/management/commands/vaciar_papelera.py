from django.core.management.base import BaseCommand

from apps.habitos.models import DIAS_EN_PAPELERA
from apps.habitos.views import vaciar_papelera


class Command(BaseCommand):
    help = f"Borra para siempre los habiticos eliminados hace más de {DIAS_EN_PAPELERA} días."

    def handle(self, *args, **options):
        # En el servidor lo ejecuta una tarea diaria (ver render.yaml)
        borrados = vaciar_papelera()
        self.stdout.write(f"Papelera vaciada: {borrados} habitico(s) borrado(s) para siempre.")
