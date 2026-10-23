from datetime import timedelta

UN_DIA = timedelta(days=1)


def calcular_racha(fechas, hoy):
    """Días seguidos cumplidos hasta hoy (o hasta ayer, si hoy aún no está marcado)."""
    dia = hoy if hoy in fechas else hoy - UN_DIA
    racha = 0
    while dia in fechas:
        racha += 1
        dia -= UN_DIA
    return racha


def estadisticas(fechas, hoy):
    return {
        "racha": calcular_racha(fechas, hoy),
        "mejor": mejor_racha(fechas),
        "total": len(fechas),
    }


def mejor_racha(fechas):
    """La racha más larga de toda la historia."""
    mejor = actual = 0
    anterior = None
    for fecha in sorted(fechas):
        if anterior is not None and fecha - anterior == UN_DIA:
            actual += 1
        else:
            actual = 1
        mejor = max(mejor, actual)
        anterior = fecha
    return mejor


def dias_en_la_semana(fechas, hoy):
    """Cuántos de los últimos 7 días (hoy incluido) están cumplidos: el "6/7 días"."""
    return sum(1 for fecha in fechas if hoy - 6 * UN_DIA <= fecha <= hoy)


def constancia(habitos, hoy, dias=30):
    """Porcentaje de días cumplidos en los últimos `dias`, sumando varios habiticos.

    `habitos` es una lista de (fecha en que empezó, fechas cumplidas). Solo cuentan
    los días desde que empezó cada uno, y hoy cuenta solo si ya está marcado
    (igual que la racha: a la mañana no baja la constancia). None si no hay días.
    """
    posibles = cumplidos = 0
    for inicio, fechas in habitos:
        desde = max(inicio, hoy - (dias - 1) * UN_DIA)
        hasta = hoy if hoy in fechas else hoy - UN_DIA
        if hasta < desde:
            continue
        posibles += (hasta - desde).days + 1
        cumplidos += sum(1 for fecha in fechas if desde <= fecha <= hasta)
    return round(100 * cumplidos / posibles) if posibles else None
