from django.urls import path

from . import views

# Van debajo de /perfil/ (ver config/urls.py)
urlpatterns = [
    path("", views.mi_perfil, name="perfil"),
    path("editar/", views.editar_perfil, name="editar_perfil"),
]
