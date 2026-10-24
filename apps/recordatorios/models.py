from datetime import time

from django.conf import settings
from django.db import models

USUARIO = settings.AUTH_USER_MODEL


class Suscripcion(models.Model):
    """Un teléfono (o navegador) que aceptó recibir notificaciones.

    Los datos los da el propio navegador al aceptar; con ellos se le puede enviar
    una notificación a través del servicio de Apple o Google.
    """

    usuario = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="suscripciones")
    endpoint = models.CharField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "suscripción"
        verbose_name_plural = "suscripciones"

    def __str__(self):
        return f"{self.usuario} · {self.endpoint[:40]}…"


class Ajustes(models.Model):
    """Qué recordatorios quiere cada persona."""

    usuario = models.OneToOneField(USUARIO, on_delete=models.CASCADE, related_name="ajustes_recordatorios")
    # "⏰ Queda 1 hora para «Gym»": 1 hora antes de que termine la franja horaria
    fin_de_franja = models.BooleanField(default=True)
    # "🔥 Todavía podés salvar tu racha": a la noche, si una racha está por cortarse
    racha_en_riesgo = models.BooleanField(default=True)
    # "Te faltan 3 habiticos de hoy": los que no tienen franja, a la hora que cada uno elija
    pendientes_del_dia = models.BooleanField(default=True)
    hora_pendientes = models.TimeField(default=time(21, 0))

    class Meta:
        verbose_name = "ajustes"
        verbose_name_plural = "ajustes"

    def __str__(self):
        return f"Recordatorios de {self.usuario}"


class Enviado(models.Model):
    """Un recordatorio que ya se mandó hoy (para no repetirlo en cada revisión)."""

    usuario = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="+")
    clave = models.CharField(max_length=50)  # "franja:<id del habitico>" o "racha"
    fecha = models.DateField()

    class Meta:
        verbose_name = "recordatorio enviado"
        verbose_name_plural = "recordatorios enviados"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "clave", "fecha"], name="un_recordatorio_por_dia"),
        ]
