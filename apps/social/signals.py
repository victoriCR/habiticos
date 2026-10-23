"""La tarjeta del día (DiaCompartido) se mantiene sola: aparece al marcar un habitico
público y desaparece si ya no queda ninguno marcado ese día."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.habitos.models import Habito, Registro

from .models import DiaCompartido


def registros_publicos(usuario_id, fecha):
    """Los días cumplidos que se pueden mostrar: habiticos públicos, activos y no eliminados."""
    return Registro.objects.filter(
        habito__usuario_id=usuario_id,
        habito__publico=True,
        habito__activo=True,
        habito__eliminado__isnull=True,
        fecha=fecha,
    )


@receiver(post_save, sender=Registro)
def compartir_al_marcar(sender, instance, **kwargs):
    habito = Habito.todos.filter(pk=instance.habito_id).first()
    if not habito or not habito.publico or not habito.activo or habito.eliminado:
        return
    momento = instance.marcado or timezone.now()
    dia, creado = DiaCompartido.objects.get_or_create(
        usuario_id=habito.usuario_id, fecha=instance.fecha, defaults={"actualizado": momento}
    )
    if not creado and momento > dia.actualizado:
        dia.actualizado = momento
        dia.save(update_fields=["actualizado"])


@receiver(post_delete, sender=Registro)
def quitar_si_queda_vacio(sender, instance, **kwargs):
    usuario_id = Habito.todos.filter(pk=instance.habito_id).values_list("usuario_id", flat=True).first()
    if usuario_id and not registros_publicos(usuario_id, instance.fecha).exists():
        DiaCompartido.objects.filter(usuario_id=usuario_id, fecha=instance.fecha).delete()
