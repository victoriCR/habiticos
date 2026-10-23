"""Lo que convierte a Habiticos en una app instalable (PWA): manifiesto,
service worker y la pantalla "Sin conexión". Ver templates/pwa/."""

import hashlib

from django.conf import settings
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control

# Archivos que el teléfono guarda al instalar la app (el diseño, nunca tus datos)
PRECARGA = ["css/habiticos.css", "js/pwa.js", "iconos/icono-192.png"]


def manifiesto(request):
    """Le dice al teléfono el nombre, el ícono y los colores de la app."""
    return render(request, "pwa/manifest.webmanifest", content_type="application/manifest+json")


@cache_control(no_cache=True)  # que el navegador siempre busque la versión nueva
def service_worker(request):
    """Se sirve desde la raíz (/sw.js) para poder atender todas las páginas."""
    archivos = [static(ruta) for ruta in PRECARGA]
    # En producción los archivos llevan un código en el nombre que cambia con cada
    # versión: así, cada cambio de diseño cambia la versión y el teléfono se actualiza
    version = hashlib.sha256("".join(archivos).encode()).hexdigest()[:12]
    return render(
        request,
        "pwa/sw.js",
        {
            "version": version,
            "precarga": archivos,
            "prefijo_estaticos": f"/{settings.STATIC_URL.lstrip('/')}",
            "icono": static("iconos/icono-192.png"),
        },
        content_type="application/javascript",
    )


def sin_conexion(request):
    return render(request, "pwa/sin_conexion.html")


def contexto(request):
    """Disponible en todas las plantillas: el service worker solo en producción
    (en desarrollo, su caché escondería los cambios de CSS)."""
    return {"pwa_activa": not settings.DEBUG}
