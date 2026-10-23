"""Mandar una notificación a todos los teléfonos de una persona."""

import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

registro = logging.getLogger(__name__)


def activos():
    """Las notificaciones solo funcionan si el servidor tiene sus claves (ver .env.example)."""
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def notificar(usuario, titulo, texto, url="/"):
    """Devuelve a cuántos teléfonos llegó. Borra los que ya no existen."""
    if not activos():
        return 0
    enviados = 0
    for suscripcion in usuario.suscripciones.all():
        try:
            webpush(
                subscription_info={
                    "endpoint": suscripcion.endpoint,
                    "keys": {"p256dh": suscripcion.p256dh, "auth": suscripcion.auth},
                },
                data=json.dumps({"titulo": titulo, "texto": texto, "url": url}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CONTACTO},
                ttl=60 * 60,  # si el teléfono está apagado, sirve durante 1 hora
            )
            enviados += 1
        except WebPushException as error:
            respuesta = getattr(error, "response", None)
            if respuesta is not None and respuesta.status_code in (404, 410):
                # El teléfono desinstaló la app o quitó el permiso: ya no sirve
                suscripcion.delete()
            else:
                registro.warning("No se pudo enviar una notificación: %s", error)
    return enviados
