from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.habitos.models import Registro
from apps.habitos.rachas import constancia, dias_en_la_semana, mejor_racha
from apps.habitos.views import en_orden_de_identidades

from .forms import PerfilForm
from .models import Perfil


@login_required
def mi_perfil(request):
    """Tu perfil, tal como lo verán los demás: solo tus habiticos públicos."""
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    hoy = timezone.localdate()
    publicos = en_orden_de_identidades(
        request.user, request.user.habitos.filter(activo=True, publico=True)
    )

    fechas = defaultdict(set)
    for habito_id, fecha in Registro.objects.filter(habito__in=publicos).values_list(
        "habito_id", "fecha"
    ):
        fechas[habito_id].add(fecha)
    for habito in publicos:
        habito.semana = dias_en_la_semana(fechas[habito.pk], hoy)

    cuenta_google = request.user.socialaccount_set.filter(provider="google").first()
    return render(
        request,
        "perfiles/perfil.html",
        {
            "perfil": perfil,
            "foto": cuenta_google.get_avatar_url() if cuenta_google else None,
            "identidades": [
                e.identidad for e in request.user.identidades_elegidas.select_related("identidad")
            ],
            "publicos": publicos,
            "constancia": constancia(
                [(timezone.localdate(h.creado), fechas[h.pk]) for h in publicos], hoy
            ),
            "mejor_racha": max((mejor_racha(fechas[h.pk]) for h in publicos), default=0),
        },
    )


@login_required
def editar_perfil(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    form = PerfilForm(request.POST or None, instance=perfil)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("perfil")
    return render(request, "perfiles/perfil_formulario.html", {"form": form})
