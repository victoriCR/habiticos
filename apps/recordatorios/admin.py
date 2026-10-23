from django.contrib import admin

from .models import Ajustes, Enviado, Suscripcion

admin.site.register(Suscripcion)
admin.site.register(Ajustes)
admin.site.register(Enviado)
