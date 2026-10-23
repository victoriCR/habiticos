from django.urls import path

from . import views

# Van debajo de /identidades/ (ver config/urls.py)
urlpatterns = [
    path("", views.identidades, name="identidades"),
    path("ordenar/", views.ordenar_identidades, name="ordenar_identidades"),
    path("<int:pk>/elegir/", views.elegir_identidad, name="elegir_identidad"),
]
