import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .enviar import activos, notificar
from .models import Ajustes, Suscripcion


@login_required
def recordatorios(request):
    ajustes, _ = Ajustes.objects.get_or_create(usuario=request.user)
    if request.method == "POST":
        ajustes.fin_de_franja = "fin_de_franja" in request.POST
        ajustes.racha_en_riesgo = "racha_en_riesgo" in request.POST
        ajustes.save()
        return redirect(f"{request.path}?guardado=1")
    return render(
        request,
        "recordatorios/recordatorios.html",
        {
            "ajustes": ajustes,
            "activos": activos(),
            "clave_publica": settings.VAPID_PUBLIC_KEY,
            "dispositivos": request.user.suscripciones.count(),
            "guardado": request.GET.get("guardado"),
            "prueba": request.GET.get("prueba"),
        },
    )


def leer_json(request):
    try:
        return json.loads(request.body)
    except (ValueError, TypeError):
        return None


@login_required(redirect_field_name=None)
@require_POST
def suscribir(request):
    """El navegador manda sus datos después de que la persona aceptó las notificaciones."""
    datos = leer_json(request)
    try:
        endpoint = datos["endpoint"]
        p256dh = datos["keys"]["p256dh"]
        auth = datos["keys"]["auth"]
    except (KeyError, TypeError):
        return HttpResponseBadRequest("Suscripción inválida")
    if not str(endpoint).startswith("https://"):
        return HttpResponseBadRequest("Suscripción inválida")
    # Si este teléfono ya estaba (de esta u otra cuenta), pasa a ser de quien lo activó ahora
    Suscripcion.objects.update_or_create(
        endpoint=endpoint, defaults={"usuario": request.user, "p256dh": p256dh, "auth": auth}
    )
    return HttpResponse(status=204)


@login_required(redirect_field_name=None)
@require_POST
def desuscribir(request):
    datos = leer_json(request) or {}
    request.user.suscripciones.filter(endpoint=datos.get("endpoint", "")).delete()
    return HttpResponse(status=204)


@login_required(redirect_field_name=None)
@require_POST
def probar(request):
    enviados = notificar(
        request.user, "🌱 ¡Listo!", "Así se van a ver tus recordatorios de Habiticos.", url="/"
    )
    return redirect(f"/recordatorios/?prueba={enviados}")
