from collections import defaultdict
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import time_format
from django.views.decorators.http import require_POST

from apps.orden import leer_ids, ultimo_lugar
from apps.perfiles.models import Perfil

from .calendario import (
    dias_del_mes,
    estado_del_dia,
    navegacion,
    primer_dia_del_mes,
    semanas_del_mes,
)
from .forms import HabitoForm
from .models import DIAS_EN_PAPELERA, Habito, Registro
from .rachas import calcular_racha, estadisticas


# Para sumar (crear o restaurar) un habitico, todos los activos necesitan esta racha.
# Es un bloqueo suave: se explica, pero se puede saltar con "… de todas formas".
DIAS_PARA_SUMAR = 7


def por_consolidar(habitos):
    """Los habiticos (con .racha ya calculada) que todavía no llegan a DIAS_PARA_SUMAR."""
    pendientes = [h for h in habitos if h.racha < DIAS_PARA_SUMAR]
    for habito in pendientes:
        habito.faltan = DIAS_PARA_SUMAR - habito.racha
    return pendientes


def rachas_activas(usuario):
    """Los habiticos activos, en el orden de "Mis habiticos", con su racha calculada."""
    hoy = timezone.localdate()
    habitos = en_orden_de_identidades(usuario, usuario.habitos.filter(activo=True))
    fechas = defaultdict(set)
    for habito_id, fecha in Registro.objects.filter(habito__in=habitos).values_list(
        "habito_id", "fecha"
    ):
        fechas[habito_id].add(fecha)
    for habito in habitos:
        habito.racha = calcular_racha(fechas[habito.pk], hoy)
    return habitos


def mostrar_bloqueo(request, pendientes, habito=None):
    """La explicación del bloqueo suave, con la salida "… de todas formas"."""
    return render(
        request,
        "habitos/bloqueo.html",
        {"pendientes": pendientes, "dias": DIAS_PARA_SUMAR, "habito": habito},
    )


def en_orden_de_identidades(usuario, habitos):
    """El mismo orden que "Mis hábitos": por identidad (en su orden) y "Otros" al final.

    Dentro de cada identidad se mantiene el orden de arrastre, porque sorted() no
    cambia el orden de los que empatan y los hábitos ya vienen ordenados.
    """
    posiciones = {
        eleccion.identidad_id: posicion
        for posicion, eleccion in enumerate(usuario.identidades_elegidas.all())
    }
    al_final = len(posiciones)
    return sorted(habitos, key=lambda habito: posiciones.get(habito.identidad_id, al_final))


@login_required
def inicio(request):
    # La primera vez, antes que nada: "¿En quién querés convertirte?"
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    if not perfil.bienvenida_vista and not request.user.identidades_elegidas.exists():
        return redirect(f"{reverse('identidades')}?bienvenida=1")

    vaciar_papelera(request.user)
    ahora = timezone.localtime()
    hoy = ahora.date()
    habitos = list(request.user.habitos.filter(activo=True))

    # Una sola consulta con todos los registros, agrupados por hábito
    fechas = defaultdict(set)
    marcado_hoy = {}
    registros = Registro.objects.filter(habito__in=habitos).values_list(
        "habito_id", "fecha", "marcado"
    )
    for habito_id, fecha, marcado in registros:
        fechas[habito_id].add(fecha)
        if fecha == hoy:
            marcado_hoy[habito_id] = marcado

    for habito in habitos:
        habito.racha = calcular_racha(fechas[habito.pk], hoy)
        habito.marcado_hoy = marcado_hoy.get(habito.pk)
        habito.hecho = hoy in fechas[habito.pk]
        # Fuera de su franja no se puede marcar (pero sí desmarcar)
        habito.bloqueado = not habito.hecho and not habito.en_franja(ahora.time())

    # Cada hábito cumplido es un voto por su identidad (James Clear)
    lunes = hoy - timedelta(days=hoy.weekday())
    votos = dict(
        Registro.objects.filter(
            habito__usuario=request.user,
            habito__identidad__isnull=False,
            # Esta consulta no pasa por Habito.objects: hay que excluir a mano los eliminados
            habito__eliminado__isnull=True,
            fecha__range=(lunes, hoy),
        )
        .values_list("habito__identidad")
        .annotate(total=Count("pk"))
    )
    # "Hoy" es para marcar: solo las identidades que tienen habiticos
    grupos, hay_identidades = agrupar_por_identidad(request.user, habitos, votos=votos)
    grupos = [grupo for grupo in grupos if grupo["habitos"]]

    return render(
        request,
        "habitos/hoy.html",
        {
            "grupos": grupos,
            "hay_identidades": hay_identidades,
            "hoy": hoy,
            "total": len(habitos),
            "hechos": sum(habito.hecho for habito in habitos),
        },
    )


@login_required
def mis_habiticos(request):
    """Organizar: crear, ordenar, editar y archivar (sin marcar)."""
    habitos = rachas_activas(request.user)
    grupos, hay_identidades = agrupar_por_identidad(request.user, habitos)
    return render(
        request,
        "habitos/mis_habiticos.html",
        {
            "grupos": grupos,
            "hay_identidades": hay_identidades,
            "sumar_bloqueado": bool(por_consolidar(habitos)),
            "archivados": request.user.habitos.filter(activo=False).count(),
        },
    )


def agrupar_por_identidad(usuario, habitos, votos=None):
    """Un grupo por identidad elegida (en su orden) y "Otros habiticos" al final.

    Cada grupo es {"identidad", "habitos", "votos"}. Un hábito cuya identidad ya no
    está elegida también va a "Otros". Devuelve (grupos, hay_identidades).
    """
    votos = votos or {}
    elegidas = [e.identidad for e in usuario.identidades_elegidas.select_related("identidad")]
    grupos = [
        {"identidad": identidad, "votos": votos.get(identidad.pk, 0), "habitos": []}
        for identidad in elegidas
    ]
    por_identidad = {grupo["identidad"].pk: grupo for grupo in grupos}
    otros = {"identidad": None, "votos": 0, "habitos": []}
    for habito in habitos:
        por_identidad.get(habito.identidad_id, otros)["habitos"].append(habito)
    if otros["habitos"] or not grupos:
        grupos.append(otros)
    return grupos, bool(elegidas)


@login_required
def crear_habito(request):
    # Bloqueo suave: sin ?forzar=1, primero se explica por qué conviene esperar
    if not request.GET.get("forzar"):
        pendientes = por_consolidar(rachas_activas(request.user))
        if pendientes:
            return mostrar_bloqueo(request, pendientes)

    if request.method == "POST":
        form = HabitoForm(request.POST, usuario=request.user)
        if form.is_valid():
            habito = form.save(commit=False)
            habito.usuario = request.user
            habito.orden = ultimo_lugar(request.user.habitos)
            habito.save()
            return redirect("mis_habiticos")
    else:
        # Desde un grupo vacío de "Mis hábitos" llega con ?identidad=<id>
        form = HabitoForm(
            usuario=request.user, initial={"identidad": request.GET.get("identidad")}
        )
    return render(
        request,
        "habitos/formulario.html",
        {"form": form, "titulo": "Nuevo habitico"},
    )


@login_required
def editar_habito(request, pk):
    habito = get_object_or_404(Habito, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = HabitoForm(request.POST, instance=habito, usuario=request.user)
        if form.is_valid():
            form.save()
            return redirect("mis_habiticos" if habito.activo else "archivados")
    else:
        form = HabitoForm(instance=habito, usuario=request.user)

    fechas = set(habito.registros.values_list("fecha", flat=True))
    return render(
        request,
        "habitos/formulario.html",
        {
            "form": form,
            "habito": habito,
            "titulo": "Editar habitico",
            "estadisticas": estadisticas(fechas, timezone.localdate()),
        },
    )


@login_required(redirect_field_name=None)  # sin ?next=: tras el login, a inicio
@require_POST
def archivar_habito(request, pk):
    habito = get_object_or_404(Habito, pk=pk, usuario=request.user)
    habito.activo = False
    habito.save(update_fields=["activo"])
    return redirect("mis_habiticos")


@login_required(redirect_field_name=None)  # sin ?next=: tras el login, a inicio
@require_POST
def restaurar_habito(request, pk):
    habito = get_object_or_404(Habito, pk=pk, usuario=request.user)
    # Restaurar también suma un habitico: misma regla (y misma salida) que crear
    if not request.POST.get("forzar"):
        pendientes = por_consolidar(rachas_activas(request.user))
        if pendientes:
            return mostrar_bloqueo(request, pendientes, habito=habito)

    habito.activo = True
    habito.orden = ultimo_lugar(request.user.habitos)
    habito.save(update_fields=["activo", "orden"])
    return redirect("mis_habiticos")


@login_required
def eliminar_habito(request, pk):
    """Manda un habitico archivado a "Eliminados recientemente", tras confirmar."""
    # Solo los archivados: para eliminar uno activo, primero hay que archivarlo
    habito = get_object_or_404(Habito, pk=pk, usuario=request.user, activo=False)
    if request.method == "POST":
        habito.eliminado = timezone.now()
        habito.save(update_fields=["eliminado"])
        return redirect("archivados")
    return render(
        request,
        "habitos/eliminar.html",
        {
            "habito": habito,
            "registros": habito.registros.count(),
            "dias": DIAS_EN_PAPELERA,
        },
    )


@login_required(redirect_field_name=None)
@require_POST
def recuperar_habito(request, pk):
    """Saca un habitico de la papelera. Vuelve a Archivados (no a los activos)."""
    habito = get_object_or_404(
        Habito.todos, pk=pk, usuario=request.user, eliminado__isnull=False
    )
    habito.eliminado = None
    habito.save(update_fields=["eliminado"])
    return redirect("archivados")


def vaciar_papelera(usuario=None):
    """Borra para siempre (con sus registros) los eliminados hace más de DIAS_EN_PAPELERA.

    Con una usuaria: solo su papelera (se llama cuando entra a la app).
    Sin usuaria: la de todo el mundo (la tarea diaria: manage.py vaciar_papelera).
    Devuelve cuántos habiticos borró.
    """
    limite = timezone.now() - timedelta(days=DIAS_EN_PAPELERA)
    vencidos = Habito.todos.filter(eliminado__lte=limite)
    if usuario is not None:
        vencidos = vencidos.filter(usuario=usuario)
    borrados, por_modelo = vencidos.delete()
    return por_modelo.get("habitos.Habito", 0)


@login_required(redirect_field_name=None)  # sin ?next=: tras el login, a inicio
@require_POST
def ordenar_habitos(request):
    """Recibe {"orden": [3, 1, 2]} (ids de hábitos en el nuevo orden) y lo guarda."""
    ids = leer_ids(request)
    if ids is None:
        return HttpResponseBadRequest("Formato inválido")

    habitos = {h.pk: h for h in request.user.habitos.filter(pk__in=ids)}
    # Todos los ids deben existir y ser de esta usuaria
    if set(ids) != set(habitos):
        return HttpResponseBadRequest("Hábitos inválidos")

    for posicion, pk in enumerate(ids):
        habitos[pk].orden = posicion
    Habito.objects.bulk_update(habitos.values(), ["orden"])
    return HttpResponse(status=204)


@login_required
def archivados(request):
    vaciar_papelera(request.user)
    hoy = timezone.localdate()
    papelera = list(
        Habito.todos.filter(usuario=request.user, eliminado__isnull=False).order_by(
            "eliminado"
        )
    )
    for habito in papelera:
        habito.dias_restantes = (habito.se_borra_el - hoy).days
    return render(
        request,
        "habitos/archivados.html",
        {
            "habitos": request.user.habitos.filter(activo=False),
            "papelera": papelera,
            "dias": DIAS_EN_PAPELERA,
        },
    )


@login_required
def calendario(request):
    """Opción B: tabla del mes con todos los hábitos activos."""
    hoy = timezone.localdate()
    primero = primer_dia_del_mes(request.GET.get("mes"), hoy)
    dias = dias_del_mes(primero)
    habitos = en_orden_de_identidades(request.user, request.user.habitos.filter(activo=True))

    fechas = defaultdict(set)
    registros = Registro.objects.filter(
        habito__in=habitos, fecha__range=(dias[0], dias[-1])
    ).values_list("habito_id", "fecha")
    for habito_id, fecha in registros:
        fechas[habito_id].add(fecha)

    filas = []
    for habito in habitos:
        inicio = timezone.localdate(habito.creado)
        filas.append(
            {
                "habito": habito,
                "dias": [estado_del_dia(d, fechas[habito.pk], hoy, inicio) for d in dias],
            }
        )

    return render(
        request,
        "habitos/calendario.html",
        {
            "primero": primero,
            "dias": dias,
            "hoy": hoy,
            "filas": filas,
            **navegacion(primero, hoy),
        },
    )


@login_required
def calendario_habito(request, pk):
    """Opción A: calendario mensual de un solo hábito."""
    habito = get_object_or_404(Habito, pk=pk, usuario=request.user)
    hoy = timezone.localdate()
    editables = dias_editables(hoy)
    primero = primer_dia_del_mes(request.GET.get("mes"), hoy)
    inicio = timezone.localdate(habito.creado)
    marcados = dict(habito.registros.values_list("fecha", "marcado"))
    fechas = set(marcados)

    semanas = [
        [
            {
                **estado_del_dia(d, fechas, hoy, inicio),
                "en_mes": d.month == primero.month,
                "marcado": marcados.get(d),
                "editable": d in editables,
            }
            for d in semana
        ]
        for semana in semanas_del_mes(primero)
    ]
    return render(
        request,
        "habitos/calendario_habito.html",
        {
            "habito": habito,
            "primero": primero,
            "semanas": semanas,
            "estadisticas": estadisticas(fechas, hoy),
            **navegacion(primero, hoy),
        },
    )


def dias_editables(hoy):
    """Desde el calendario solo se pueden corregir hoy y ayer (rachas honestas)."""
    return {hoy, hoy - timedelta(days=1)}


@login_required(redirect_field_name=None)
@require_POST
def registrar_dia(request, pk):
    """Desde el calendario: marca hoy o ayer a una hora elegida, cambia la hora o desmarca."""
    habito = get_object_or_404(Habito, pk=pk, usuario=request.user)
    try:
        fecha = date.fromisoformat(request.POST["fecha"])
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Fecha inválida")
    accion = request.POST.get("accion")
    volver = redirect(f"{reverse('calendario_habito', args=[pk])}?mes={fecha:%Y-%m}")

    if fecha not in dias_editables(timezone.localdate()):
        messages.error(request, "Solo se pueden modificar hoy y ayer.")
        return volver

    if accion == "desmarcar":
        habito.registros.filter(fecha=fecha).delete()
        return volver
    if accion != "guardar":
        return HttpResponseBadRequest("Acción inválida")

    try:
        hora = datetime.strptime(request.POST.get("hora", ""), "%H:%M").time()
    except ValueError:
        messages.error(request, "Indicá una hora válida.")
        return volver

    if not habito.en_franja(hora):
        desde = time_format(habito.hora_desde, "g:i a")
        hasta = time_format(habito.hora_hasta, "g:i a")
        messages.error(
            request, f"«{habito.nombre}» solo se puede marcar de {desde} a {hasta}."
        )
        return volver

    marcado = timezone.make_aware(datetime.combine(fecha, hora))
    if marcado > timezone.now():
        messages.error(request, "No podés registrar una hora que todavía no ha llegado.")
        return volver

    Registro.objects.update_or_create(
        habito=habito, fecha=fecha, defaults={"marcado": marcado}
    )
    return volver


@login_required(redirect_field_name=None)  # sin ?next=: tras el login, a inicio
@require_POST
def marcar_habito(request, pk):
    habito = get_object_or_404(Habito, pk=pk, usuario=request.user)
    ahora = timezone.localtime()
    registro = habito.registros.filter(fecha=ahora.date()).first()

    if registro:
        # Desmarcar siempre se permite, por si fue un error
        registro.delete()
    elif habito.en_franja(ahora.time()):
        Registro.objects.get_or_create(habito=habito, fecha=ahora.date())
    else:
        desde = time_format(habito.hora_desde, "g:i a")
        hasta = time_format(habito.hora_hasta, "g:i a")
        messages.error(
            request, f"«{habito.nombre}» solo se puede marcar de {desde} a {hasta}."
        )
    return redirect("inicio")
