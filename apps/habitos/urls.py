from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("mis-habiticos/", views.mis_habiticos, name="mis_habiticos"),
    path("nuevo/", views.crear_habito, name="crear_habito"),
    path("archivados/", views.archivados, name="archivados"),
    path("calendario/", views.calendario, name="calendario"),
    path("habitos/ordenar/", views.ordenar_habitos, name="ordenar_habitos"),
    path("habitos/<int:pk>/calendario/", views.calendario_habito, name="calendario_habito"),
    path("habitos/<int:pk>/registrar-dia/", views.registrar_dia, name="registrar_dia"),
    path("habitos/<int:pk>/marcar/", views.marcar_habito, name="marcar_habito"),
    path("habitos/<int:pk>/editar/", views.editar_habito, name="editar_habito"),
    path("habitos/<int:pk>/archivar/", views.archivar_habito, name="archivar_habito"),
    path("habitos/<int:pk>/restaurar/", views.restaurar_habito, name="restaurar_habito"),
    path("habitos/<int:pk>/eliminar/", views.eliminar_habito, name="eliminar_habito"),
    path("habitos/<int:pk>/recuperar/", views.recuperar_habito, name="recuperar_habito"),
]
