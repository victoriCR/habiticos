from calendar import Calendar
from datetime import datetime, timedelta


def primer_dia_del_mes(texto, hoy):
    """Convierte "2026-10" en date(2026, 10, 1). Si no es válido, usa el mes actual."""
    este_mes = hoy.replace(day=1)
    try:
        primero = datetime.strptime(texto or "", "%Y-%m").date()
    except ValueError:
        return este_mes
    # Años absurdos (como 0001 o 9999) romperían el cálculo del mes vecino
    if not 1900 <= primero.year <= 2999:
        return este_mes
    return primero


def semanas_del_mes(primero):
    """Semanas de lunes a domingo; incluye días de los meses vecinos para completarlas."""
    return Calendar(firstweekday=0).monthdatescalendar(primero.year, primero.month)


def dias_del_mes(primero):
    return [
        dia
        for semana in semanas_del_mes(primero)
        for dia in semana
        if dia.month == primero.month
    ]


def navegacion(primero, hoy):
    """Meses anterior y siguiente, y si el mes mostrado es el actual."""
    return {
        "anterior": (primero - timedelta(days=1)).replace(day=1),
        "siguiente": (primero + timedelta(days=32)).replace(day=1),
        "es_este_mes": primero == hoy.replace(day=1),
    }


def estado_del_dia(fecha, fechas, hoy, inicio):
    hecho = fecha in fechas
    return {
        "fecha": fecha,
        "hecho": hecho,
        "hoy": fecha == hoy,
        "futuro": fecha > hoy,
        "antes": fecha < inicio and not hecho,
    }
