from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.identidades.models import Identidad, IdentidadElegida
from apps.perfiles.models import Perfil
from apps.pruebas import crear_usuaria


class PerfilTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(
            username="ana", first_name="Ana", last_name="Pérez", email="ana@correo.com"
        )
        self.client.force_login(self.usuaria)
        self.hoy = timezone.localdate()

    def crear(self, nombre, publico=True, dias=0, **extra):
        habito = Habito.objects.create(
            usuario=self.usuaria, nombre=nombre, publico=publico, **extra
        )
        for n in range(dias):
            Registro.objects.create(habito=habito, fecha=self.hoy - timedelta(days=n))
        return habito

    def test_pide_iniciar_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get("/perfil/").status_code, 302)

    def test_muestra_solo_los_habiticos_publicos(self):
        self.crear("Leer", publico=True, dias=6)
        self.crear("Terapia", publico=False, dias=3)
        respuesta = self.client.get("/perfil/")
        self.assertContains(respuesta, "Leer")
        self.assertContains(respuesta, "6/7 días")
        self.assertNotContains(respuesta, "Terapia")

    def test_no_muestra_archivados_ni_eliminados(self):
        self.crear("Viejo", activo=False)
        self.crear("Borrado", activo=False, eliminado=timezone.now())
        respuesta = self.client.get("/perfil/")
        self.assertNotContains(respuesta, "Viejo")
        self.assertNotContains(respuesta, "Borrado")
        self.assertContains(respuesta, "Todavía no tenés habiticos públicos")

    def test_nunca_muestra_el_email(self):
        self.assertNotContains(self.client.get("/perfil/"), "ana@correo.com")

    def test_muestra_nombre_identidades_y_datos(self):
        identidad = Identidad.objects.first()
        IdentidadElegida.objects.create(usuario=self.usuaria, identidad=identidad)
        self.crear("Leer", dias=3, identidad=identidad)
        respuesta = self.client.get("/perfil/")
        self.assertContains(respuesta, "Ana Pérez")
        self.assertContains(respuesta, identidad.nombre)
        self.assertContains(respuesta, "Elegí tu @usuario")
        self.assertContains(respuesta, "🔥 3")

    def test_editar_perfil_guarda_usuario_en_minusculas_y_sin_arroba(self):
        self.client.post("/perfil/editar/", {"nombre_usuario": "@Ana.Perez", "frase": "Paso a paso"})
        perfil = Perfil.objects.get(usuario=self.usuaria)
        self.assertEqual(perfil.nombre_usuario, "ana.perez")
        respuesta = self.client.get("/perfil/")
        self.assertContains(respuesta, "@ana.perez")
        self.assertContains(respuesta, "Paso a paso")

    def test_usuario_con_caracteres_invalidos(self):
        respuesta = self.client.post("/perfil/editar/", {"nombre_usuario": "ana pérez!"})
        self.assertContains(respuesta, "Usá de 3 a 30 letras minúsculas")
        self.assertIsNone(Perfil.objects.get(usuario=self.usuaria).nombre_usuario)

    def test_usuario_ya_usado(self):
        otra = crear_usuaria(username="otra")
        Perfil.objects.filter(usuario=otra).update(nombre_usuario="ana")
        respuesta = self.client.post("/perfil/editar/", {"nombre_usuario": "Ana"})
        self.assertEqual(respuesta.status_code, 200)  # vuelve a mostrar el formulario
        self.assertIsNone(Perfil.objects.get(usuario=self.usuaria).nombre_usuario)

    def test_publico_se_elige_al_crear_el_habitico(self):
        self.client.post("/nuevo/", {"nombre": "Caminar", "publico": "on"})
        self.assertTrue(Habito.objects.get(nombre="Caminar").publico)

    def test_por_defecto_un_habitico_es_privado(self):
        self.client.post("/nuevo/", {"nombre": "Caminar"})
        self.assertFalse(Habito.objects.get(nombre="Caminar").publico)
