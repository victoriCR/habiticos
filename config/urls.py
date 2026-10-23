from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from config import pwa


def pagina_legal(plantilla):
    """Una página pública (sin iniciar sesión), con el correo de contacto."""
    return TemplateView.as_view(
        template_name=plantilla, extra_context={"contacto": settings.CONTACTO_EMAIL}
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("privacidad/", pagina_legal("legal/privacidad.html"), name="privacidad"),
    path("terminos/", pagina_legal("legal/terminos.html"), name="terminos"),
    # App instalable (PWA)
    path("manifest.webmanifest", pwa.manifiesto, name="manifiesto"),
    path("sw.js", pwa.service_worker, name="service_worker"),
    path("sin-conexion/", pwa.sin_conexion, name="sin_conexion"),
    # Cada app define sus propias direcciones
    path("", include("apps.habitos.urls")),
    path("identidades/", include("apps.identidades.urls")),
    path("perfil/", include("apps.perfiles.urls")),
]
