from django.contrib import admin

from .models import Habito, Registro


@admin.register(Habito)
class HabitoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "usuario", "activo", "eliminado"]

    def get_queryset(self, request):
        # En el admin se ven todos, también los que están en "Eliminados recientemente"
        return Habito.todos.all()


admin.site.register(Registro)
