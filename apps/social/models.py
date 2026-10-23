from django.conf import settings
from django.db import models

USUARIO = settings.AUTH_USER_MODEL

# Rachas que se celebran en la Comunidad con 🏆
HITOS = {7, 21, 30, 66, 100}

# Frases para animar: predefinidas (no hay texto libre: nadie puede escribir algo hiriente)
FRASES = {
    "vamos": "¡Vamos!",
    "constancia": "¡Qué constancia!",
    "orgullo": "¡Orgulloso/a de vos!",
    "un_dia": "¡Un día a la vez!",
    "aplauso": "👏",
}


class Seguimiento(models.Model):
    """`seguidor` sigue a `seguido`."""

    seguidor = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="siguiendo")
    seguido = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="seguidores")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["seguidor", "seguido"], name="seguir_una_vez"),
            models.CheckConstraint(
                condition=~models.Q(seguidor=models.F("seguido")), name="no_seguirse_a_si_mismo"
            ),
        ]

    def __str__(self):
        return f"{self.seguidor} → {self.seguido}"


class Bloqueo(models.Model):
    """`bloqueador` no quiere ver ni ser visto por `bloqueado`."""

    bloqueador = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="bloqueos")
    bloqueado = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="bloqueado_por")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["bloqueador", "bloqueado"], name="bloquear_una_vez"),
        ]

    def __str__(self):
        return f"{self.bloqueador} ⊘ {self.bloqueado}"


class Reporte(models.Model):
    """Un aviso a la administración sobre un perfil (se revisa en /admin/)."""

    MOTIVOS = {
        "ofensivo": "Contenido ofensivo",
        "suplantacion": "Se hace pasar por otra persona",
        "spam": "Spam o cuenta falsa",
        "otro": "Otro motivo",
    }

    reportante = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="reportes_hechos")
    reportado = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="reportes_recibidos")
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    detalle = models.TextField(blank=True)
    revisado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["revisado", "-creado"]

    def __str__(self):
        return f"{self.reportado} ({self.get_motivo_display()})"


class DiaCompartido(models.Model):
    """La tarjeta de la Comunidad: el día de una persona (sus habiticos públicos cumplidos).

    Se crea sola al marcar un habitico público; su contenido se arma al mostrarla.
    """

    usuario = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="dias_compartidos")
    fecha = models.DateField()
    actualizado = models.DateTimeField()  # el último habitico marcado (ordena el feed)

    class Meta:
        ordering = ["-actualizado"]
        verbose_name = "día compartido"
        verbose_name_plural = "días compartidos"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "fecha"], name="una_tarjeta_por_dia"),
        ]

    def __str__(self):
        return f"{self.usuario} · {self.fecha}"


class Reaccion(models.Model):
    """❤️ Apoyar (una por persona) o 💬 Animar con una frase predefinida (una por persona)."""

    APOYO = "apoyo"
    ANIMO = "animo"

    dia = models.ForeignKey(DiaCompartido, on_delete=models.CASCADE, related_name="reacciones")
    usuario = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="reacciones")
    tipo = models.CharField(max_length=10, choices={APOYO: "Apoyo", ANIMO: "Ánimo"})
    frase = models.CharField(max_length=20, choices=FRASES, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado"]
        verbose_name = "reacción"
        verbose_name_plural = "reacciones"
        constraints = [
            models.UniqueConstraint(fields=["dia", "usuario", "tipo"], name="una_reaccion_por_tipo"),
        ]

    def __str__(self):
        return f"{self.usuario} → {self.dia} ({self.tipo})"


class Aviso(models.Model):
    """Lo que te cuenta la campanita de Comunidad: alguien te siguió, te apoyó o te animó."""

    SEGUIR = "seguir"
    APOYO = "apoyo"
    ANIMO = "animo"

    destinatario = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="avisos")
    actor = models.ForeignKey(USUARIO, on_delete=models.CASCADE, related_name="+")
    tipo = models.CharField(max_length=10, choices={SEGUIR: "Seguir", APOYO: "Apoyo", ANIMO: "Ánimo"})
    dia = models.ForeignKey(DiaCompartido, on_delete=models.CASCADE, null=True, blank=True)
    frase = models.CharField(max_length=20, choices=FRASES, blank=True)
    leido = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.actor} → {self.destinatario} ({self.tipo})"
