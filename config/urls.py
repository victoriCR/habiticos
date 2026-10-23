from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    # Cada app define sus propias direcciones
    path("", include("apps.habitos.urls")),
    path("identidades/", include("apps.identidades.urls")),
    path("perfil/", include("apps.perfiles.urls")),
]
