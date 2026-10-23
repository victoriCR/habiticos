from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.identidades.models import Identidad, IdentidadElegida
from apps.pruebas import crear_usuaria


class EliminarHabiticoTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.habito = Habito.objects.create(usuario=self.usuaria, nombre="Gym", activo=False)
        Registro.objects.create(habito=self.habito, fecha=timezone.localdate())

    def eliminar(self):
        self.client.post(f"/habitos/{self.habito.pk}/eliminar/")

    def test_pide_confirmacion_antes_de_eliminar(self):
        respuesta = self.client.get(f"/habitos/{self.habito.pk}/eliminar/")
        self.assertContains(respuesta, "¿Eliminar «Gym»?")
        self.assertContains(respuesta, "Podés recuperarlo durante 30 días")
        self.assertContains(respuesta, "1 día cumplido")
        self.assertTrue(Habito.objects.filter(pk=self.habito.pk).exists())

    def test_eliminar_lo_manda_a_la_papelera_sin_borrar_nada(self):
        self.eliminar()
        # Desaparece de la app…
        self.assertFalse(Habito.objects.filter(pk=self.habito.pk).exists())
        self.assertFalse(self.usuaria.habitos.filter(pk=self.habito.pk).exists())
        # …pero sigue guardado, con sus registros
        self.assertTrue(Habito.todos.filter(pk=self.habito.pk).exists())
        self.assertTrue(Registro.objects.filter(habito_id=self.habito.pk).exists())

    def test_archivados_lo_muestra_en_eliminados_recientemente(self):
        self.eliminar()
        respuesta = self.client.get("/archivados/")
        self.assertContains(respuesta, "Eliminados recientemente")
        self.assertContains(respuesta, f"/habitos/{self.habito.pk}/recuperar/")
        self.assertNotContains(respuesta, f"/habitos/{self.habito.pk}/eliminar/")

    def test_recuperar_lo_devuelve_a_archivados(self):
        self.eliminar()
        self.client.post(f"/habitos/{self.habito.pk}/recuperar/")
        self.habito.refresh_from_db()
        self.assertIsNone(self.habito.eliminado)
        self.assertFalse(self.habito.activo)  # archivado, no activo

    def test_un_eliminado_no_se_puede_editar_ni_marcar(self):
        self.eliminar()
        self.assertEqual(self.client.get(f"/habitos/{self.habito.pk}/editar/").status_code, 404)
        self.assertEqual(
            self.client.post(f"/habitos/{self.habito.pk}/marcar/").status_code, 404
        )

    def test_a_los_30_dias_se_borra_para_siempre(self):
        self.eliminar()
        # (Se vuelve a iniciar sesión en cada fecha simulada: la sesión caduca a medianoche)
        dentro_de_29 = timezone.now() + timedelta(days=29)
        with mock.patch("django.utils.timezone.now", return_value=dentro_de_29):
            self.client.force_login(self.usuaria)
            self.assertEqual(self.client.get("/archivados/").status_code, 200)
        self.assertTrue(Habito.todos.filter(pk=self.habito.pk).exists())

        dentro_de_30 = timezone.now() + timedelta(days=30, minutes=1)
        with mock.patch("django.utils.timezone.now", return_value=dentro_de_30):
            self.client.force_login(self.usuaria)
            self.assertEqual(self.client.get("/archivados/").status_code, 200)
        self.assertFalse(Habito.todos.filter(pk=self.habito.pk).exists())
        self.assertFalse(Registro.objects.filter(habito_id=self.habito.pk).exists())

    def test_los_votos_no_cuentan_los_eliminados(self):
        identidad = Identidad.objects.first()
        IdentidadElegida.objects.create(usuario=self.usuaria, identidad=identidad)
        self.habito.identidad = identidad
        self.habito.save()
        self.eliminar()
        self.assertContains(self.client.get("/"), "🗳️ 0 votos esta semana")

    def test_no_se_puede_recuperar_uno_ajeno(self):
        otra = crear_usuaria(username="otra")
        ajeno = Habito.objects.create(
            usuario=otra, nombre="Ajeno", activo=False, eliminado=timezone.now()
        )
        respuesta = self.client.post(f"/habitos/{ajeno.pk}/recuperar/")
        self.assertEqual(respuesta.status_code, 404)

    def test_un_habitico_activo_no_se_puede_eliminar(self):
        self.habito.activo = True
        self.habito.save()
        self.assertEqual(self.client.post(f"/habitos/{self.habito.pk}/eliminar/").status_code, 404)
        self.assertTrue(Habito.objects.filter(pk=self.habito.pk).exists())

    def test_no_se_puede_eliminar_uno_ajeno(self):
        otra = crear_usuaria(username="otra")
        ajeno = Habito.objects.create(usuario=otra, nombre="Ajeno", activo=False)
        self.assertEqual(self.client.post(f"/habitos/{ajeno.pk}/eliminar/").status_code, 404)
        self.assertTrue(Habito.objects.filter(pk=ajeno.pk).exists())

    def test_archivados_muestra_el_boton_eliminar(self):
        self.assertContains(self.client.get("/archivados/"), f"/habitos/{self.habito.pk}/eliminar/")

    def test_archivados_muestra_fecha_y_hora_del_borrado(self):
        self.eliminar()
        self.habito.refresh_from_db()
        momento = timezone.localtime(self.habito.se_borra_a)
        hora = f"{momento:%-I:%M} {'a.m.' if momento.hour < 12 else 'p.m.'}"
        respuesta = self.client.get("/archivados/")
        self.assertContains(respuesta, f"{momento.year}, {hora}")
