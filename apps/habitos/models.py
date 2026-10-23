from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


# Un habitico eliminado espera en "Eliminados recientemente" (se puede recuperar)
# y después de estos días se borra para siempre
DIAS_EN_PAPELERA = 30


class HabiticosVisibles(models.Manager):
    """Habito.objects (y usuaria.habitos) nunca devuelven los eliminados."""

    def get_queryset(self):
        return super().get_queryset().filter(eliminado__isnull=True)


class Habito(models.Model):
    # El primero es el que usa Django por defecto (también en usuaria.habitos).
    # Para ver también los eliminados: Habito.todos
    objects = HabiticosVisibles()
    todos = models.Manager()

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habitos",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    # Posición en la lista (se cambia arrastrando); empata por id
    orden = models.PositiveIntegerField(default=0)
    # Franja horaria opcional en la que se puede marcar (ambas o ninguna)
    hora_desde = models.TimeField(null=True, blank=True)
    hora_hasta = models.TimeField(null=True, blank=True)
    # Opcional. Si se borra la identidad, el hábito pasa a "Otros hábitos"
    identidad = models.ForeignKey(
        "identidades.Identidad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="habitos",
    )
    # Cuándo se eliminó (vacío si no está eliminado). Ver DIAS_EN_PAPELERA
    eliminado = models.DateTimeField(null=True, blank=True)
    # Privado por defecto: solo los públicos aparecen en el perfil
    publico = models.BooleanField(default=False)

    class Meta:
        ordering = ["orden", "pk"]
        # Nombre que se muestra en /admin/
        verbose_name = "habitico"
        verbose_name_plural = "habiticos"

    def __str__(self):
        return self.nombre

    @property
    def se_borra_a(self):
        """Momento exacto en que un habitico eliminado se borra para siempre."""
        return self.eliminado + timedelta(days=DIAS_EN_PAPELERA)

    @property
    def se_borra_el(self):
        """La fecha (local) de se_borra_a."""
        return timezone.localdate(self.se_borra_a)

    @property
    def tiene_franja(self):
        return self.hora_desde is not None and self.hora_hasta is not None

    def en_franja(self, hora):
        """¿Se puede marcar a esta hora? Los extremos cuentan: hasta las 5:00 incluye las 5:00."""
        if not self.tiene_franja:
            return True
        hora = hora.replace(second=0, microsecond=0)
        return self.hora_desde <= hora <= self.hora_hasta


class Registro(models.Model):
    habito = models.ForeignKey(
        Habito,
        on_delete=models.CASCADE,
        related_name="registros",
    )
    fecha = models.DateField()
    # Por defecto, el momento en que se marca; se puede corregir desde el calendario.
    # null=True: los registros anteriores a este campo no tienen hora
    marcado = models.DateTimeField(default=timezone.now, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["habito", "fecha"],
                name="un_registro_por_dia",
            ),
        ]

    def __str__(self):
        return f"{self.habito} · {self.fecha}"
