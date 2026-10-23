from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.identidades.models import Identidad, IdentidadElegida
from apps.pruebas import crear_usuaria


class BarraLateralTests(TestCase):
    def test_sin_sesion_no_hay_barra(self):
        respuesta = self.client.get("/accounts/login/")
        self.assertNotContains(respuesta, 'class="barra"')

    def test_con_sesion_muestra_nombre_inicial_y_cerrar_sesion(self):
        usuaria = crear_usuaria(
            username="ana", first_name="Ana", last_name="Pérez"
        )
        self.client.force_login(usuaria)
        respuesta = self.client.get("/")
        self.assertContains(respuesta, 'class="barra"')
        self.assertContains(respuesta, "Ana Pérez")
        # Sin cuenta de Google no hay foto: se muestra la inicial
        self.assertContains(respuesta, '<span class="avatar" aria-hidden="true">A</span>')
        self.assertContains(respuesta, "Cerrar sesión")

    def test_la_navegacion_marca_la_pagina_actual(self):
        usuaria = crear_usuaria(username="ana")
        self.client.force_login(usuaria)

        respuesta = self.client.get("/")
        self.assertContains(respuesta, 'href="/" aria-current="page">Hoy')
        self.assertContains(respuesta, 'href="/mis-habiticos/">Mis habiticos')

        # Archivados está dentro de "Mis habiticos": resalta esa sección
        respuesta = self.client.get("/archivados/")
        self.assertContains(respuesta, 'href="/">Hoy')
        self.assertContains(respuesta, 'href="/mis-habiticos/" aria-current="page">Mis habiticos')


class RachaEnPaginasTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.habito = Habito.objects.create(usuario=self.usuaria, nombre="Leer")
        hoy = timezone.localdate()
        for n in (1, 2, 3):
            Registro.objects.create(habito=self.habito, fecha=hoy - timedelta(days=n))

    def test_inicio_muestra_la_racha(self):
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "🔥 3")

    def test_marcar_hoy_sube_la_racha(self):
        self.client.post(f"/habitos/{self.habito.pk}/marcar/")
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "🔥 4")

    def test_marcar_hoy_muestra_la_hora(self):
        self.client.post(f"/habitos/{self.habito.pk}/marcar/")
        registro = self.habito.registros.get(fecha=timezone.localdate())
        hora = timezone.localtime(registro.marcado)
        respuesta = self.client.get("/")
        self.assertContains(respuesta, f"{hora:%-I:%M}")
        self.assertContains(respuesta, 'class="hora"')

    def test_registro_antiguo_sin_hora_no_muestra_hora(self):
        # auto_now_add siempre pone la hora al crear; la quitamos después
        registro = Registro.objects.create(habito=self.habito, fecha=timezone.localdate())
        Registro.objects.filter(pk=registro.pk).update(marcado=None)
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "🔥 4")
        self.assertNotContains(respuesta, 'class="hora"')

    def test_editar_muestra_estadisticas(self):
        respuesta = self.client.get(f"/habitos/{self.habito.pk}/editar/")
        self.assertContains(respuesta, "Racha actual: 3 días")
        self.assertContains(respuesta, "Mejor racha: 3 días")
        self.assertContains(respuesta, "Total: 3 días")


class GruposPorIdentidadTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.saludable = Identidad.objects.get(nombre="Soy una persona saludable")
        self.activa = Identidad.objects.get(nombre="Soy una persona activa")
        for posicion, identidad in enumerate([self.activa, self.saludable]):
            IdentidadElegida.objects.create(
                usuario=self.usuaria, identidad=identidad, orden=posicion
            )
        self.gym = Habito.objects.create(usuario=self.usuaria, nombre="Gym", identidad=self.activa)
        self.agua = Habito.objects.create(
            usuario=self.usuaria, nombre="Agua", identidad=self.saludable
        )
        self.leer = Habito.objects.create(usuario=self.usuaria, nombre="Leer")

    def test_los_grupos_siguen_el_orden_de_las_identidades_y_otros_va_al_final(self):
        html = self.client.get("/").content.decode()
        posiciones = [
            html.index("Soy una persona activa"),
            html.index("Gym"),
            html.index("Soy una persona saludable"),
            html.index("Agua"),
            html.index("Otros habiticos"),
            html.index("Leer"),
        ]
        self.assertEqual(posiciones, sorted(posiciones))

    def test_votos_de_esta_semana(self):
        hoy = timezone.localdate()
        lunes = hoy - timedelta(days=hoy.weekday())
        Registro.objects.create(habito=self.gym, fecha=hoy)
        Registro.objects.create(habito=self.gym, fecha=lunes - timedelta(days=1))  # semana pasada
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "🗳️ 1 voto esta semana")
        self.assertContains(respuesta, "🗳️ 0 votos esta semana")

    def test_sin_identidades_no_hay_titulos_de_grupo(self):
        self.usuaria.identidades_elegidas.all().delete()
        respuesta = self.client.get("/")
        self.assertNotContains(respuesta, "Otros habiticos")
        self.assertContains(respuesta, "Gym")

    def test_una_identidad_sin_habitos_invita_a_agregar_uno(self):
        Habito.objects.filter(identidad=self.activa).delete()
        # En "Mis habiticos" (organizar); "Hoy" no muestra grupos vacíos
        respuesta = self.client.get("/mis-habiticos/")
        self.assertContains(respuesta, f"/nuevo/?identidad={self.activa.pk}")
        self.assertNotContains(self.client.get("/"), "Soy una persona activa")

    def test_el_calendario_usa_el_mismo_orden_que_mis_habitos(self):
        # Leer (sin identidad) se creó último pero se arrastra al principio:
        # igual va al final, porque "Otros habiticos" siempre va al final
        Habito.objects.filter(pk=self.leer.pk).update(orden=0)
        Habito.objects.filter(pk__in=[self.gym.pk, self.agua.pk]).update(orden=5)
        html = self.client.get("/calendario/").content.decode()
        posiciones = [html.index(">Gym<"), html.index(">Agua<"), html.index(">Leer<")]
        self.assertEqual(posiciones, sorted(posiciones))
