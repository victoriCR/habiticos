from django.contrib import admin

from .models import Aviso, DiaCompartido, Reaccion, Seguimiento

admin.site.register(Seguimiento)
admin.site.register(DiaCompartido)
admin.site.register(Reaccion)
admin.site.register(Aviso)
