from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Perfil(models.Model):
    """Lo que cada persona muestra de sí misma (y alguna preferencia)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    # La pantalla "¿En quién querés convertirte?" se muestra sola una vez
    bienvenida_vista = models.BooleanField(default=False)
    # El @usuario: lo elige cada persona; vacío hasta que lo elige
    nombre_usuario = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                r"^[a-z0-9._]{3,30}$",
                "Usá de 3 a 30 letras minúsculas, números, puntos o guiones bajos.",
            )
        ],
    )
    frase = models.CharField(max_length=80, blank=True)

    class Meta:
        verbose_name_plural = "perfiles"

    def __str__(self):
        return f"@{self.nombre_usuario}" if self.nombre_usuario else str(self.usuario)
