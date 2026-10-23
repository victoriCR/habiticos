from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.habitos.rachas import constancia, dias_en_la_semana, mejor_racha
from apps.habitos.views import en_orden_de_identidades

from .forms import PerfilForm
from .models import Perfil


def foto_de(usuario):
    """La foto de Google de una persona (o None)."""
    cuenta = usuario.socialaccount_set.filter(provider="google").first()
    return cuenta.get_avatar_url() if cuenta else None


def datos_de_perfil(usuario):
    """Lo que muestra un perfil (el tuyo o el de otra persona): solo lo público."""
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    hoy = timezone.localdate()
    publicos = en_orden_de_identidades(usuario, usuario.habitos.filter(activo=True, publico=True))

    fechas = defaultdict(set)
    for habito_id, fecha in Registro.objects.filter(habito__in=publicos).values_list(
        "habito_id", "fecha"
    ):
        fechas[habito_id].add(fecha)
    for habito in publicos:
        habito.semana = dias_en_la_semana(fechas[habito.pk], hoy)

    return {
        "dueno": usuario,
        "perfil": perfil,
        "foto": foto_de(usuario),
        "identidades": [
            e.identidad for e in usuario.identidades_elegidas.select_related("identidad")
        ],
        "publicos": publicos,
        "constancia": constancia(
            [(timezone.localdate(h.creado), fechas[h.pk]) for h in publicos], hoy
        ),
        "mejor_racha": max((mejor_racha(fechas[h.pk]) for h in publicos), default=0),
        # Los vínculos de "seguir" viven en la app social (related_name en sus modelos)
        "seguidores": usuario.seguidores.count(),
        "siguiendo": usuario.siguiendo.count(),
    }


@login_required
def mi_perfil(request):
    """Tu perfil, tal como lo verán los demás: solo tus habiticos públicos."""
    return render(
        request,
        "perfiles/perfil.html",
        {**datos_de_perfil(request.user), "es_mio": True},
    )


@login_required
def editar_perfil(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    form = PerfilForm(request.POST or None, instance=perfil)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("perfil")
    return render(request, "perfiles/perfil_formulario.html", {"form": form})


# Palabra que hay que escribir para confirmar (así nadie borra su cuenta por un clic)
PALABRA_PARA_ELIMINAR = "eliminar"


@login_required
def eliminar_cuenta(request):
    """Borra la cuenta y todos sus datos para siempre, después de confirmar."""
    if request.user.is_superuser:
        # Una cuenta de administración no se borra desde aquí (evita quedarse sin admin)
        messages.error(request, "Las cuentas de administración se eliminan desde /admin/.")
        return redirect("editar_perfil")

    if request.method == "POST":
        if request.POST.get("confirmacion", "").strip().lower() != PALABRA_PARA_ELIMINAR:
            messages.error(request, f"Escribí «{PALABRA_PARA_ELIMINAR}» para confirmar.")
            return redirect("eliminar_cuenta")
        usuario = request.user
        logout(request)
        # Se borra en cascada: perfil, habiticos (también los de la papelera),
        # registros, identidades elegidas y la conexión con Google
        usuario.delete()
        return redirect("cuenta_eliminada")

    return render(
        request,
        "perfiles/eliminar_cuenta.html",
        {
            "habiticos": Habito.todos.filter(usuario=request.user).count(),
            "dias": Registro.objects.filter(habito__usuario=request.user).count(),
            "palabra": PALABRA_PARA_ELIMINAR,
        },
    )


def cuenta_eliminada(request):
    """Pública: ya no hay sesión."""
    return render(request, "perfiles/cuenta_eliminada.html")
