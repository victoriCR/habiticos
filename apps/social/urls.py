from django.urls import path

from . import views

urlpatterns = [
    path("comunidad/", views.comunidad, name="comunidad"),
    path("comunidad/buscar/", views.buscar, name="buscar"),
    path("comunidad/avisos/", views.avisos, name="avisos"),
    path("comunidad/dias/<int:pk>/apoyar/", views.apoyar, name="apoyar"),
    path("comunidad/dias/<int:pk>/animar/", views.animar, name="animar"),
    # Perfiles: habiticos.com/@usuario
    path("@<str:nombre_usuario>/", views.perfil_publico, name="perfil_publico"),
    path("@<str:nombre_usuario>/seguir/", views.seguir, name="seguir"),
    path(
        "@<str:nombre_usuario>/seguidores/",
        views.lista_de_personas,
        {"quienes": "seguidores"},
        name="seguidores",
    ),
    path(
        "@<str:nombre_usuario>/siguiendo/",
        views.lista_de_personas,
        {"quienes": "siguiendo"},
        name="siguiendo",
    ),
]
