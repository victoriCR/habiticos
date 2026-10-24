import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .enviar import activos, notificar
from .logica import HORAS_PENDIENTES
from .models import Ajustes, Suscripcion


@login_required
def recordatorios(request):
    ajustes, _ = Ajustes.objects.get_or_create(usuario=request.user)
    if request.method == "POST":
        ajustes.fin_de_franja = "fin_de_franja" in request.POST
        ajustes.racha_en_riesgo = "racha_en_riesgo" in request.POST
        ajustes.pendientes_del_dia = "pendientes_del_dia" in request.POST
        # Solo una de las horas de la lista (si llega otra cosa, queda la que estaba)
        elegida = {h.strftime("%H:%M"): h for h in HORAS_PENDIENTES}.get(request.POST.get("hora_pendientes"))
        if elegida:
            ajustes.hora_pendientes = elegida
        ajustes.save()
        return redirect(f"{request.path}?guardado=1")
    return render(
        request,
        "recordatorios/recordatorios.html",
        {
            "ajustes": ajustes,
            "horas_pendientes": HORAS_PENDIENTES,
            "activos": activos(),
            "clave_publica": settings.VAPID_PUBLIC_KEY,
            "dispositivos": request.user.suscripciones.order_by("creado"),
            "guardado": request.GET.get("guardado"),
            "prueba": request.GET.get("prueba"),
        },
    )


def tipo_y_nombre(datos):
    """Lo que el navegador dice de sí mismo, validado ("dispositivo" si no se sabe)."""
    tipo = datos.get("tipo")
    if tipo not in dict(Suscripcion.TIPOS):
        tipo = Suscripcion.DISPOSITIVO
    return {"tipo": tipo, "nombre": str(datos.get("nombre") or "")[:60]}


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
    defaults = {"usuario": request.user, "p256dh": p256dh, "auth": auth, **tipo_y_nombre(datos)}
    if datos.get("solo_actualizar"):
        # Al abrir la página en un dispositivo ya activado: completar tipo y nombre.
        # Si se quitó desde otro dispositivo, no se vuelve a crear (404: el navegador lo apaga)
        actualizados = Suscripcion.objects.filter(endpoint=endpoint, usuario=request.user).update(
            **tipo_y_nombre(datos)
        )
        return HttpResponse(status=204 if actualizados else 404)
    Suscripcion.objects.update_or_create(endpoint=endpoint, defaults=defaults)
    return HttpResponse(status=204)


@login_required(redirect_field_name=None)
@require_POST
def desuscribir(request):
    datos = leer_json(request) or {}
    request.user.suscripciones.filter(endpoint=datos.get("endpoint", "")).delete()
    return HttpResponse(status=204)


@login_required(redirect_field_name=None)
@require_POST
def quitar_dispositivo(request, pk):
    """Dejar de mandarle avisos a otro dispositivo (por ejemplo, uno que ya no usás)."""
    get_object_or_404(Suscripcion, pk=pk, usuario=request.user).delete()
    return redirect("recordatorios")


@login_required(redirect_field_name=None)
@require_POST
def probar(request):
    enviados = notificar(
        request.user, "🌱 ¡Listo!", "Así se van a ver tus recordatorios de Habiticos.", url="/"
    )
    return redirect(f"/recordatorios/?prueba={enviados}")
