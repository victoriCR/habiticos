from django.conf import settings
from django.db import models


class Identidad(models.Model):
    """En quién quiere convertirse la usuaria ("Soy una persona activa").

    Es un catálogo común para todas; solo se agregan o cambian desde /admin/.
    """

    emoji = models.CharField(max_length=16)
    nombre = models.CharField(max_length=100)

    class Meta:
        ordering = ["pk"]
        verbose_name_plural = "identidades"

    def __str__(self):
        return f"{self.emoji} {self.nombre}"


class IdentidadElegida(models.Model):
    """Una identidad que la usuaria eligió construir, en el orden que ella decide."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="identidades_elegidas",
    )
    identidad = models.ForeignKey(
        Identidad,
        on_delete=models.CASCADE,
        related_name="elecciones",
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "pk"]
        verbose_name_plural = "identidades elegidas"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "identidad"],
                name="identidad_elegida_unica",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} · {self.identidad}"
