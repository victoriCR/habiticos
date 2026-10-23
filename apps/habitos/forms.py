from django import forms
from django.db.models import Case, When

from apps.identidades.models import Identidad

from .models import Habito

campo_hora = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")


class HabitoForm(forms.ModelForm):
    class Meta:
        model = Habito
        fields = ["nombre", "descripcion", "identidad", "publico", "hora_desde", "hora_hasta"]
        labels = {
            "descripcion": "Descripción (opcional)",
            "identidad": "¿A qué identidad pertenece? (opcional)",
            "publico": "Público",
            "hora_desde": "Se puede marcar desde (opcional)",
            "hora_hasta": "Hasta",
        }
        help_texts = {
            "publico": "Se muestra en tu perfil. Si no, solo lo ves vos.",
            "hora_hasta": "Dejá las dos horas vacías para poder marcarlo a cualquier hora.",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            # Tarjetas para tocar en vez de un desplegable (el menú del sistema
            # en macOS es semitransparente y deja ver el fondo)
            "identidad": forms.RadioSelect,
            "hora_desde": campo_hora,
            "hora_hasta": campo_hora,
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo las identidades que eligió, en su orden (y la actual del hábito,
        # aunque ya no esté elegida, para no perderla al guardar)
        pks = list(usuario.identidades_elegidas.values_list("identidad_id", flat=True))
        actual = self.instance.identidad_id
        if actual and actual not in pks:
            pks.append(actual)

        campo = self.fields["identidad"]
        campo.empty_label = "Ninguna"
        if pks:
            orden = Case(*[When(pk=pk, then=posicion) for posicion, pk in enumerate(pks)])
            campo.queryset = Identidad.objects.filter(pk__in=pks).order_by(orden)
        else:
            campo.queryset = Identidad.objects.none()
            campo.help_text = "Primero elegí tus identidades en «Identidades»."

    def clean(self):
        datos = super().clean()
        desde = datos.get("hora_desde")
        hasta = datos.get("hora_hasta")
        if (desde is None) != (hasta is None):
            raise forms.ValidationError("Indicá las dos horas, o dejá ambas vacías.")
        if desde is not None and desde >= hasta:
            self.add_error("hora_hasta", "Debe ser posterior a la hora de inicio.")
        return datos
