from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils import timezone

from apps.recordatorios.enviar import activos, notificar
from apps.recordatorios.logica import pendientes
from apps.recordatorios.models import Enviado


class Command(BaseCommand):
    help = "Manda los recordatorios que tocan ahora (en el servidor corre cada 15 minutos)."

    def handle(self, *args, **options):
        if not activos():
            self.stdout.write("Recordatorios desactivados: faltan VAPID_PUBLIC_KEY y VAPID_PRIVATE_KEY.")
            return
        ahora = timezone.localtime()
        mandados = 0
        for usuario, clave, titulo, texto in pendientes(ahora):
            try:
                # Primero se anota (así, si dos tareas corren a la vez, solo una lo manda)
                Enviado.objects.create(usuario=usuario, clave=clave, fecha=ahora.date())
            except IntegrityError:
                continue
            mandados += bool(notificar(usuario, titulo, texto, url="/"))
        self.stdout.write(f"Recordatorios enviados: {mandados}.")
