from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.identidades.models import Identidad, IdentidadElegida
from apps.perfiles.models import Perfil
from apps.pruebas import crear_usuaria


class EliminarCuentaTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.habito = Habito.objects.create(usuario=self.usuaria, nombre="Leer")
        Registro.objects.create(habito=self.habito, fecha=timezone.localdate())
        Registro.objects.create(habito=self.habito, fecha=timezone.localdate() - timedelta(days=1))
        Habito.objects.create(
            usuario=self.usuaria, nombre="Viejo", activo=False, eliminado=timezone.now()
        )
        IdentidadElegida.objects.create(usuario=self.usuaria, identidad=Identidad.objects.first())

    def test_pide_iniciar_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get("/perfil/eliminar-cuenta/").status_code, 302)

    def test_muestra_cuanto_se_va_a_borrar(self):
        respuesta = self.client.get("/perfil/eliminar-cuenta/")
        self.assertContains(respuesta, "2 habiticos")  # también el de la papelera
        self.assertContains(respuesta, "2 días cumplidos")

    def test_sin_escribir_eliminar_no_borra_nada(self):
        respuesta = self.client.post("/perfil/eliminar-cuenta/", {"confirmacion": "si"}, follow=True)
        self.assertContains(respuesta, "Escribí «eliminar» para confirmar.")
        self.assertTrue(get_user_model().objects.filter(pk=self.usuaria.pk).exists())

    def test_borra_la_cuenta_y_todos_sus_datos(self):
        otra = crear_usuaria(username="otra")
        ajeno = Habito.objects.create(usuario=otra, nombre="Ajeno")

        respuesta = self.client.post("/perfil/eliminar-cuenta/", {"confirmacion": " Eliminar "})

        self.assertRedirects(respuesta, "/perfil/cuenta-eliminada/")
        self.assertFalse(get_user_model().objects.filter(pk=self.usuaria.pk).exists())
        self.assertFalse(Habito.todos.filter(usuario_id=self.usuaria.pk).exists())
        self.assertFalse(Registro.objects.filter(habito_id=self.habito.pk).exists())
        self.assertFalse(Perfil.objects.filter(usuario_id=self.usuaria.pk).exists())
        self.assertFalse(IdentidadElegida.objects.filter(usuario_id=self.usuaria.pk).exists())
        # Lo de otras personas y el catálogo no se tocan
        self.assertTrue(Habito.objects.filter(pk=ajeno.pk).exists())
        self.assertEqual(Identidad.objects.count(), 10)

    def test_despues_queda_sin_sesion(self):
        self.client.post("/perfil/eliminar-cuenta/", {"confirmacion": "eliminar"})
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertContains(self.client.get("/perfil/cuenta-eliminada/"), "Tu cuenta fue eliminada")

    def test_una_cuenta_de_administracion_no_se_borra_desde_aca(self):
        admin = get_user_model().objects.create_superuser(username="admin", password="x")
        Perfil.objects.create(usuario=admin, bienvenida_vista=True)
        self.client.force_login(admin)
        self.client.post("/perfil/eliminar-cuenta/", {"confirmacion": "eliminar"})
        self.assertTrue(get_user_model().objects.filter(pk=admin.pk).exists())

    def test_editar_perfil_enlaza_eliminar_mi_cuenta(self):
        self.assertContains(self.client.get("/perfil/editar/"), 'href="/perfil/eliminar-cuenta/"')
