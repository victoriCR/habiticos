"""Qué recordatorios tocan en un momento dado. Separado del envío para poder probarlo."""

from collections import defaultdict
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.utils.dateformat import time_format

from apps.habitos.models import Habito, Registro
from apps.habitos.rachas import calcular_racha

from .models import Ajustes, Enviado

# "⏰ Queda 1 hora": se avisa en la última hora de la franja
ANTES_DEL_FIN = timedelta(hours=1)
# "🔥 Todavía podés salvar tu racha": desde esta hora de la noche
HORA_RACHA = time(20, 0)
# Solo se avisa por rachas de al menos estos días (con 1 día todavía no hay racha que perder)
RACHA_MINIMA = 2


def minutos(hora):
    return hora.hour * 60 + hora.minute


def pendientes(ahora):
    """Lista de (usuario, clave, título, texto) que tocan ahora y todavía no se enviaron hoy.

    `ahora` es la fecha y hora local (Costa Rica). Solo personas con al menos un
    teléfono suscripto.
    """
    hoy = ahora.date()
    hora = ahora.time()
    personas = get_user_model().objects.filter(suscripciones__isnull=False).distinct()
    ajustes = {a.usuario_id: a for a in Ajustes.objects.filter(usuario__in=personas)}
    habitos = list(
        Habito.objects.filter(usuario__in=personas, activo=True).select_related("usuario")
    )
    fechas = defaultdict(set)
    for habito_id, fecha in Registro.objects.filter(
        habito__in=habitos, fecha__gte=hoy - timedelta(days=400)
    ).values_list("habito_id", "fecha"):
        fechas[habito_id].add(fecha)
    ya_enviados = set(
        Enviado.objects.filter(fecha=hoy, usuario__in=personas).values_list("usuario_id", "clave")
    )

    resultado = []
    en_riesgo = defaultdict(list)
    for habito in habitos:
        if hoy in fechas[habito.pk]:
            continue  # ya está hecho hoy: nada que recordar
        ajuste = ajustes.get(habito.usuario_id) or Ajustes(usuario_id=habito.usuario_id)

        # ⏰ Fin de la franja: en su última hora (si ya empezó)
        if ajuste.fin_de_franja and habito.tiene_franja:
            fin = minutos(habito.hora_hasta)
            if minutos(habito.hora_desde) <= minutos(hora) < fin and minutos(hora) >= fin - 60:
                clave = f"franja:{habito.pk}"
                if (habito.usuario_id, clave) not in ya_enviados:
                    queda = fin - minutos(hora)
                    resultado.append((
                        habito.usuario,
                        clave,
                        f"⏰ Queda {'1 hora' if queda > 45 else f'{queda} minutos'} para «{habito.nombre}»",
                        f"Se puede marcar hasta las {time_format(habito.hora_hasta, 'g:i a')}.",
                    ))

        # 🔥 Racha en riesgo: a la noche, si todavía se puede marcar
        if ajuste.racha_en_riesgo and hora >= HORA_RACHA:
            todavia_se_puede = not habito.tiene_franja or habito.en_franja(hora)
            racha = calcular_racha(fechas[habito.pk], hoy)  # hasta ayer, porque hoy no está
            if todavia_se_puede and racha >= RACHA_MINIMA:
                en_riesgo[habito.usuario].append((habito.nombre, racha))

    for usuario, lista in en_riesgo.items():
        if (usuario.pk, "racha") in ya_enviados:
            continue
        nombres = ", ".join(f"{nombre} ({racha} días)" for nombre, racha in lista)
        titulo = (
            "🔥 Todavía podés salvar tu racha"
            if len(lista) == 1
            else f"🔥 Todavía podés salvar {len(lista)} rachas"
        )
        resultado.append((usuario, "racha", titulo, f"Te falta marcar: {nombres}."))
    return resultado


def momento_local(fecha, hora):
    """Para las pruebas: una fecha y hora local."""
    from django.utils import timezone

    return timezone.make_aware(datetime.combine(fecha, hora))
