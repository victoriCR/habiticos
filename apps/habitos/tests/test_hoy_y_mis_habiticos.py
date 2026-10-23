from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.pruebas import crear_usuaria


class HoyTests(TestCase):
    """Hoy: solo marcar. Limpio, sin organizar."""

    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.agua = Habito.objects.create(usuario=self.usuaria, nombre="Agua")
        self.leer = Habito.objects.create(usuario=self.usuaria, nombre="Leer")

    def test_se_puede_marcar_pero_no_organizar(self):
        respuesta = self.client.get("/")
        self.assertContains(respuesta, f"/habitos/{self.agua.pk}/marcar/")
        self.assertNotContains(respuesta, "Nuevo habitico")
        self.assertNotContains(respuesta, f"/habitos/{self.agua.pk}/editar/")
        self.assertNotContains(respuesta, 'class="asa"')

    def test_resumen_de_cuantos_estan_hechos(self):
        Registro.objects.create(habito=self.agua, fecha=timezone.localdate())
        self.assertContains(self.client.get("/"), "1 de 2 hechos")

    def test_todos_hechos(self):
        for habito in (self.agua, self.leer):
            Registro.objects.create(habito=habito, fecha=timezone.localdate())
        self.assertContains(self.client.get("/"), "2 de 2 hechos 🎉")

    def test_sin_habiticos_invita_a_crear_el_primero(self):
        Habito.objects.all().delete()
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "Todavía no tenés habiticos.")
        self.assertContains(respuesta, 'href="/mis-habiticos/"')

    def test_marcar_vuelve_a_hoy(self):
        respuesta = self.client.post(f"/habitos/{self.agua.pk}/marcar/")
        self.assertRedirects(respuesta, "/")


class MisHabiticosTests(TestCase):
    """Mis habiticos: organizar. Sin marcar."""

    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.agua = Habito.objects.create(usuario=self.usuaria, nombre="Agua")

    def test_organiza_pero_no_marca(self):
        respuesta = self.client.get("/mis-habiticos/")
        self.assertContains(respuesta, "Nuevo habitico")
        self.assertContains(respuesta, f"/habitos/{self.agua.pk}/editar/")
        self.assertContains(respuesta, 'class="asa"')
        self.assertContains(respuesta, f"/habitos/{self.agua.pk}/calendario/")
        self.assertNotContains(respuesta, f"/habitos/{self.agua.pk}/marcar/")

    def test_enlaza_archivados_con_su_cantidad(self):
        Habito.objects.create(usuario=self.usuaria, nombre="Viejo", activo=False)
        self.assertContains(self.client.get("/mis-habiticos/"), "📦 Archivados (1)")

    def test_crear_editar_y_archivar_vuelven_a_mis_habiticos(self):
        # "Agua" no lleva 🔥 7: se crea "de todas formas" (si no, muestra el bloqueo)
        respuesta = self.client.post("/nuevo/?forzar=1", {"nombre": "Leer"})
        self.assertRedirects(respuesta, "/mis-habiticos/")
        respuesta = self.client.post(f"/habitos/{self.agua.pk}/editar/", {"nombre": "Beber agua"})
        self.assertRedirects(respuesta, "/mis-habiticos/")
        respuesta = self.client.post(f"/habitos/{self.agua.pk}/archivar/")
        self.assertRedirects(respuesta, "/mis-habiticos/")


class NavegacionCelularTests(TestCase):
    def setUp(self):
        self.client.force_login(crear_usuaria(username="ana"))

    def test_barra_de_abajo_con_hoy_mis_habiticos_y_mas(self):
        respuesta = self.client.get("/")
        self.assertContains(respuesta, 'class="pestanas"')
        self.assertContains(respuesta, 'class="pestana" href="/" aria-current="page"')
        self.assertContains(respuesta, 'class="pestana" href="/mis-habiticos/"')
        self.assertContains(respuesta, 'id="abrir-mas"')

    def test_el_panel_mas_tiene_perfil_calendario_identidades_y_cerrar_sesion(self):
        respuesta = self.client.get("/").content.decode()
        panel = respuesta[respuesta.index('<dialog class="hoja" id="mas"'):respuesta.index("</dialog>", respuesta.index('id="mas"'))]
        for enlace in ('href="/perfil/"', 'href="/calendario/"', 'href="/identidades/"', 'href="/privacidad/"'):
            self.assertIn(enlace, panel)
        self.assertIn("Cerrar sesión", panel)

    def test_mas_se_resalta_en_las_secciones_que_contiene(self):
        self.assertContains(self.client.get("/calendario/"), 'class="pestana activa"')
        self.assertNotContains(self.client.get("/"), 'class="pestana activa"')
