from datetime import datetime, time, timedelta

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone


def proxima_medianoche():
    """Las 00:00 de mañana, en la zona horaria de settings.TIME_ZONE."""
    manana = timezone.localdate() + timedelta(days=1)
    return timezone.make_aware(datetime.combine(manana, time.min))


@receiver(user_logged_in)
def cerrar_sesion_a_medianoche(sender, request, user, **kwargs):
    """Al iniciar sesión, la sesión caduca a medianoche y hay que volver a entrar."""
    request.session.set_expiry(proxima_medianoche())
