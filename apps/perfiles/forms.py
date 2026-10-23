from django import forms

from .models import Perfil


class PerfilForm(forms.ModelForm):
    # Campo propio (sin los validadores del modelo) para poder pasar a minúsculas y
    # quitar la "@" antes de validar; el modelo valida después el formato y que no esté usado
    nombre_usuario = forms.CharField(
        label="Tu @usuario",
        max_length=31,
        help_text="Letras minúsculas, números, puntos o guiones bajos. Así te van a encontrar.",
        widget=forms.TextInput(attrs={"placeholder": "carlos", "autocapitalize": "none"}),
    )

    class Meta:
        model = Perfil
        fields = ["nombre_usuario", "frase"]
        labels = {"frase": "Tu frase (opcional)"}
        help_texts = {"frase": "Aparece debajo de tu nombre."}
        widgets = {
            "frase": forms.TextInput(attrs={"placeholder": "Un poquito mejor cada día 🌱"}),
        }

    def clean_nombre_usuario(self):
        return self.cleaned_data["nombre_usuario"].strip().lstrip("@").lower()
