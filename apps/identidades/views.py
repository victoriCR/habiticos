from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.orden import leer_ids, ultimo_lugar
from apps.perfiles.models import Perfil

from .models import Identidad, IdentidadElegida


@login_required
def identidades(request):
    Perfil.objects.update_or_create(
        usuario=request.user, defaults={"bienvenida_vista": True}
    )
    elegidas = list(request.user.identidades_elegidas.select_related("identidad"))
    disponibles = Identidad.objects.exclude(
        pk__in=[eleccion.identidad_id for eleccion in elegidas]
    )
    return render(
        request,
        "identidades/identidades.html",
        {
            "elegidas": elegidas,
            "disponibles": disponibles,
            "bienvenida": request.GET.get("bienvenida") == "1",
        },
    )


@login_required(redirect_field_name=None)
@require_POST
def elegir_identidad(request, pk):
    """Tocar una identidad: si no estaba elegida, se agrega al final; si lo estaba, se quita."""
    identidad = get_object_or_404(Identidad, pk=pk)
    elecciones = request.user.identidades_elegidas
    eleccion = elecciones.filter(identidad=identidad).first()
    if eleccion:
        # Sus hábitos conservan la identidad: si se vuelve a elegir, vuelven a su grupo
        eleccion.delete()
    else:
        IdentidadElegida.objects.create(
            usuario=request.user, identidad=identidad, orden=ultimo_lugar(elecciones)
        )
    sufijo = "?bienvenida=1" if request.POST.get("bienvenida") else ""
    return redirect(reverse("identidades") + sufijo)


@login_required(redirect_field_name=None)
@require_POST
def ordenar_identidades(request):
    """Recibe {"orden": [2, 1, 3]} (ids de identidades elegidas en el nuevo orden)."""
    ids = leer_ids(request)
    if ids is None:
        return HttpResponseBadRequest("Formato inválido")

    elecciones = {
        e.identidad_id: e
        for e in request.user.identidades_elegidas.filter(identidad_id__in=ids)
    }
    if set(ids) != set(elecciones):
        return HttpResponseBadRequest("Identidades inválidas")

    for posicion, pk in enumerate(ids):
        elecciones[pk].orden = posicion
    IdentidadElegida.objects.bulk_update(elecciones.values(), ["orden"])
    return HttpResponse(status=204)
