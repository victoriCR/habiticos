from django.urls import path

from . import views

urlpatterns = [
    path("", views.recordatorios, name="recordatorios"),
    path("suscribir/", views.suscribir, name="suscribir"),
    path("desuscribir/", views.desuscribir, name="desuscribir"),
    path("probar/", views.probar, name="probar_recordatorio"),
]
