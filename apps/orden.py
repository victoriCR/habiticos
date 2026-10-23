"""Ayudas para listas que se ordenan arrastrando (habiticos e identidades)."""

import json

from django.db.models import Max


def ultimo_lugar(consulta):
    """Posición para poner algo al final de una lista ordenada (hábitos o identidades)."""
    maximo = consulta.aggregate(maximo=Max("orden"))["maximo"]
    return 0 if maximo is None else maximo + 1


def leer_ids(request):
    """Lee {"orden": [3, 1, 2]} del cuerpo de la petición; None si no es válido."""
    try:
        ids = [int(pk) for pk in json.loads(request.body)["orden"]]
    except (ValueError, KeyError, TypeError):
        return None
    return ids if len(ids) == len(set(ids)) else None
