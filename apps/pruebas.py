"""Ayudas para las pruebas de las apps (no son pruebas: no empieza con test_)."""

from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.perfiles.models import Perfil

HOY = date(2026, 10, 23)


def crear_usuaria(**datos):
    """Una usuaria de prueba que ya vio la bienvenida (si no, "/" la manda a Identidades)."""
    usuaria = get_user_model().objects.create_user(**datos)
    Perfil.objects.create(usuario=usuaria, bienvenida_vista=True)
    return usuaria


def dias_atras(*numeros):
    return {HOY - timedelta(days=n) for n in numeros}


def a_las(hora, minuto):
    """Un 'ahora' falso: hoy a esa hora local (para simular la hora en las pruebas)."""
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))
