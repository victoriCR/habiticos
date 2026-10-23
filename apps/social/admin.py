from django.contrib import admin

from .models import Aviso, Bloqueo, DiaCompartido, Reaccion, Reporte, Seguimiento


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ["reportado", "motivo", "reportante", "creado", "revisado"]
    list_filter = ["revisado", "motivo"]
    list_editable = ["revisado"]


admin.site.register(Seguimiento)
admin.site.register(Bloqueo)
admin.site.register(DiaCompartido)
admin.site.register(Reaccion)
admin.site.register(Aviso)
