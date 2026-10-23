from collections import defaultdict
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.habitos.models import Registro
from apps.habitos.rachas import calcular_racha
from apps.perfiles.models import Perfil
from apps.perfiles.views import datos_de_perfil, foto_de

from .models import FRASES, HITOS, Aviso, DiaCompartido, Reaccion, Seguimiento

# La Comunidad muestra los días de las últimas dos semanas
DIAS_EN_EL_FEED = 14

# Cuántas personas muestra la columna de Seguidores / Siguiendo (el resto, en "Ver todos")
PERSONAS_EN_LA_COLUMNA = 5


# --- Ayudas ---


def persona(request, nombre_usuario):
    """El dueño de un @usuario (404 si no existe)."""
    perfil = get_object_or_404(
        Perfil.objects.select_related("usuario"), nombre_usuario=nombre_usuario.lower()
    )
    return perfil.usuario


def volver_a(request, por_defecto):
    """A dónde volver después de un botón: el "volver" del formulario si es de este sitio."""
    destino = request.POST.get("volver", "")
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(por_defecto)


def con_foto(personas):
    """Les agrega .foto a una lista de usuarios (para mostrarlos con su cara)."""
    for usuario in personas:
        usuario.foto = foto_de(usuario)
    return personas


# --- Perfiles de otras personas ---


@login_required
def perfil_publico(request, nombre_usuario):
    dueno = persona(request, nombre_usuario)
    if dueno == request.user:
        return redirect("perfil")
    return render(
        request,
        "perfiles/perfil.html",
        {
            **datos_de_perfil(dueno),
            "es_mio": False,
            "sigo": Seguimiento.objects.filter(seguidor=request.user, seguido=dueno).exists(),
            "me_sigue": Seguimiento.objects.filter(seguidor=dueno, seguido=request.user).exists(),
        },
    )


@login_required(redirect_field_name=None)
@require_POST
def seguir(request, nombre_usuario):
    """Seguir o, si ya la seguías, dejar de seguir."""
    dueno = persona(request, nombre_usuario)
    if dueno == request.user:
        raise Http404
    seguimiento = Seguimiento.objects.filter(seguidor=request.user, seguido=dueno).first()
    if seguimiento:
        seguimiento.delete()
    else:
        Seguimiento.objects.create(seguidor=request.user, seguido=dueno)
        Aviso.objects.create(destinatario=dueno, actor=request.user, tipo=Aviso.SEGUIR)
    return volver_a(request, reverse("perfil_publico", args=[dueno.perfil.nombre_usuario]))


@login_required
def lista_de_personas(request, nombre_usuario, quienes):
    """Seguidores de alguien, o a quiénes sigue."""
    dueno = persona(request, nombre_usuario)
    if quienes == "seguidores":
        relacion = Seguimiento.objects.filter(seguido=dueno).select_related("seguidor__perfil")
        personas = [s.seguidor for s in relacion]
        titulo = "Seguidores"
    else:
        relacion = Seguimiento.objects.filter(seguidor=dueno).select_related("seguido__perfil")
        personas = [s.seguido for s in relacion]
        titulo = "Sigue a"
    return render(
        request,
        "social/personas.html",
        {"dueno": dueno, "titulo": titulo, "personas": marcar_seguidos(request.user, con_foto(personas))},
    )


def marcar_seguidos(usuario, personas):
    """Les agrega .sigo (si `usuario` ya las sigue), para el botón Seguir/Siguiendo."""
    sigo = set(Seguimiento.objects.filter(seguidor=usuario).values_list("seguido_id", flat=True))
    for p in personas:
        p.sigo = p.pk in sigo
    return personas


@login_required
def buscar(request):
    texto = request.GET.get("q", "").strip().lstrip("@")
    personas = []
    if len(texto) >= 2:
        encontrados = (
            Perfil.objects.filter(nombre_usuario__isnull=False)
            .filter(
                Q(nombre_usuario__icontains=texto)
                | Q(usuario__first_name__icontains=texto)
                | Q(usuario__last_name__icontains=texto)
            )
            .exclude(usuario=request.user)
            .select_related("usuario")[:20]
        )
        personas = marcar_seguidos(request.user, con_foto([p.usuario for p in encontrados]))
    return render(request, "social/buscar.html", {"texto": texto, "personas": personas})


# --- Comunidad (el feed) ---


def visibles_para(usuario):
    """De quiénes ve tarjetas: las personas que sigue, y las propias."""
    siguiendo = set(Seguimiento.objects.filter(seguidor=usuario).values_list("seguido_id", flat=True))
    return siguiendo | {usuario.pk}


def armar_tarjetas(usuario, dias):
    """El contenido de cada tarjeta: los habiticos públicos cumplidos ese día, con su
    racha, los hitos 🏆, los "retomó" 🔁 y las reacciones. Las vacías no se muestran."""
    if not dias:
        return []
    duenos = {dia.usuario_id for dia in dias}
    desde = min(dia.fecha for dia in dias) - timedelta(days=max(HITOS) + 1)
    del_dia = defaultdict(list)  # (dueño, fecha) → registros públicos de ese día
    fechas = defaultdict(set)  # habito → todas sus fechas cumplidas (para la racha)
    registros = (
        Registro.objects.filter(
            habito__usuario_id__in=duenos,
            habito__publico=True,
            habito__activo=True,
            habito__eliminado__isnull=True,
            fecha__gte=desde,
        )
        .select_related("habito", "habito__identidad")
        .order_by("marcado")
    )
    for registro in registros:
        fechas[registro.habito_id].add(registro.fecha)
        del_dia[(registro.habito.usuario_id, registro.fecha)].append(registro)

    tarjetas = []
    for dia in dias:
        cumplidos = []
        for registro in del_dia.get((dia.usuario_id, dia.fecha), []):
            racha = calcular_racha(fechas[registro.habito_id], dia.fecha)
            cumplidos.append(
                {
                    "habito": registro.habito,
                    "racha": racha,
                    "hito": racha in HITOS,
                    # Volvió después de cortar: racha de 1 pero con días cumplidos antes
                    "retomo": racha == 1 and any(f < dia.fecha for f in fechas[registro.habito_id]),
                }
            )
        if not cumplidos:
            continue
        reacciones = list(dia.reacciones.all())
        tarjetas.append(
            {
                "dia": dia,
                "persona": dia.usuario,
                "foto": foto_de(dia.usuario),
                "cumplidos": cumplidos,
                "apoyos": sum(r.tipo == Reaccion.APOYO for r in reacciones),
                "yo_apoye": any(r.tipo == Reaccion.APOYO and r.usuario_id == usuario.pk for r in reacciones),
                "mi_animo": next(
                    (r.frase for r in reacciones if r.tipo == Reaccion.ANIMO and r.usuario_id == usuario.pk), ""
                ),
                "animos": [
                    {"persona": r.usuario, "frase": FRASES.get(r.frase, "")}
                    for r in reacciones
                    if r.tipo == Reaccion.ANIMO
                ],
            }
        )
    return tarjetas


@login_required
def comunidad(request):
    hoy = timezone.localdate()
    dias = list(
        DiaCompartido.objects.filter(
            usuario_id__in=visibles_para(request.user),
            fecha__gte=hoy - timedelta(days=DIAS_EN_EL_FEED),
        )
        .select_related("usuario", "usuario__perfil")
        .prefetch_related("reacciones__usuario", "usuario__socialaccount_set")[:50]
    )
    return render(
        request,
        "social/comunidad.html",
        {
            "tarjetas": armar_tarjetas(request.user, dias),
            "hoy": hoy,
            "frases": FRASES,
            "sigue_a_alguien": Seguimiento.objects.filter(seguidor=request.user).exists(),
            "tengo_usuario": bool(getattr(getattr(request.user, "perfil", None), "nombre_usuario", None)),
            **resumen_de_seguimientos(request.user),
        },
    )


def resumen_de_seguimientos(usuario):
    """Para la columna de la Comunidad: cuántos seguidores y seguidos, y los más recientes.

    Solo se listan quienes tienen @usuario (sin él no hay perfil al que llevar)."""
    seguidos = (
        Seguimiento.objects.filter(seguidor=usuario, seguido__perfil__nombre_usuario__isnull=False)
        .select_related("seguido__perfil")
        .prefetch_related("seguido__socialaccount_set")
        .order_by("-creado")[:PERSONAS_EN_LA_COLUMNA]
    )
    seguidores = (
        Seguimiento.objects.filter(seguido=usuario, seguidor__perfil__nombre_usuario__isnull=False)
        .select_related("seguidor__perfil")
        .prefetch_related("seguidor__socialaccount_set")
        .order_by("-creado")[:PERSONAS_EN_LA_COLUMNA]
    )
    return {
        "cuantos_sigo": Seguimiento.objects.filter(seguidor=usuario).count(),
        "cuantos_me_siguen": Seguimiento.objects.filter(seguido=usuario).count(),
        "ultimos_seguidos": con_foto([s.seguido for s in seguidos]),
        # Con .sigo, para el botón "Seguir" a quien te sigue y vos no
        "ultimos_seguidores": marcar_seguidos(usuario, con_foto([s.seguidor for s in seguidores])),
    }


def dia_visible(request, pk):
    """Una tarjeta que esta persona puede ver (si no, 404)."""
    return get_object_or_404(DiaCompartido, pk=pk, usuario_id__in=visibles_para(request.user))


@login_required(redirect_field_name=None)
@require_POST
def apoyar(request, pk):
    """❤️ Apoyar o, si ya habías apoyado, quitarlo."""
    dia = dia_visible(request, pk)
    apoyo = dia.reacciones.filter(usuario=request.user, tipo=Reaccion.APOYO).first()
    if apoyo:
        apoyo.delete()
    else:
        Reaccion.objects.create(dia=dia, usuario=request.user, tipo=Reaccion.APOYO)
        if dia.usuario != request.user:
            Aviso.objects.create(destinatario=dia.usuario, actor=request.user, tipo=Aviso.APOYO, dia=dia)
    return redirect(f"{reverse('comunidad')}#dia-{dia.pk}")


@login_required(redirect_field_name=None)
@require_POST
def animar(request, pk):
    """💬 Animar con una frase; la misma frase otra vez la quita."""
    dia = dia_visible(request, pk)
    frase = request.POST.get("frase", "")
    if frase not in FRASES:
        raise Http404
    animo = dia.reacciones.filter(usuario=request.user, tipo=Reaccion.ANIMO).first()
    if animo and animo.frase == frase:
        animo.delete()
    else:
        Reaccion.objects.update_or_create(
            dia=dia, usuario=request.user, tipo=Reaccion.ANIMO, defaults={"frase": frase}
        )
        if dia.usuario != request.user:
            Aviso.objects.create(
                destinatario=dia.usuario, actor=request.user, tipo=Aviso.ANIMO, dia=dia, frase=frase
            )
    return redirect(f"{reverse('comunidad')}#dia-{dia.pk}")


@login_required
def avisos(request):
    lista = list(
        request.user.avisos.select_related("actor__perfil", "dia")[:50]
    )
    # Se ven como "nuevos" esta vez y quedan leídos
    request.user.avisos.filter(leido=False).update(leido=True)
    return render(request, "social/avisos.html", {"avisos": con_foto_actor(lista), "frases": FRASES})


def con_foto_actor(lista):
    for aviso in lista:
        aviso.foto = foto_de(aviso.actor)
        aviso.texto_frase = FRASES.get(aviso.frase, "")
    return lista


def contexto(request):
    """Disponible en todas las plantillas: cuántos avisos sin leer (la campanita)."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    return {"avisos_sin_leer": request.user.avisos.filter(leido=False).count()}
