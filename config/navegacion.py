"""A qué sección de la navegación pertenece cada página (para resaltarla)."""

# nombre de la URL → sección. Lo que no está aquí no resalta nada.
SECCIONES = {
    "inicio": "hoy",
    "mis_habiticos": "mis_habiticos",
    "crear_habito": "mis_habiticos",
    "editar_habito": "mis_habiticos",
    "calendario_habito": "mis_habiticos",
    "archivados": "mis_habiticos",
    "eliminar_habito": "mis_habiticos",
    "calendario": "calendario",
    "comunidad": "comunidad",
    "recordatorios": "recordatorios",
    "buscar": "comunidad",
    "avisos": "comunidad",
    "perfil_publico": "comunidad",
    "seguidores": "comunidad",
    "siguiendo": "comunidad",
    "identidades": "identidades",
    "perfil": "perfil",
    "editar_perfil": "perfil",
    "eliminar_cuenta": "perfil",
}

# Las que en el celular están dentro de "Más" (la barra de abajo solo tiene Hoy y Mis
# habiticos; Mi perfil se abre desde la franja de arriba)
EN_MAS = {"calendario", "identidades", "recordatorios"}


def seccion(request):
    """Disponible en todas las plantillas como {{ seccion }} y {{ seccion_en_mas }}."""
    coincidencia = getattr(request, "resolver_match", None)
    actual = SECCIONES.get(coincidencia.url_name if coincidencia else None)
    return {"seccion": actual, "seccion_en_mas": actual in EN_MAS}
