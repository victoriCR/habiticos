from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito
from apps.perfiles.signals import proxima_medianoche
from apps.pruebas import crear_usuaria


class SesionMedianocheTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)

    def test_proxima_medianoche_es_las_00_de_manana_en_hora_local(self):
        medianoche = timezone.localtime(proxima_medianoche())
        self.assertEqual(medianoche.date(), timezone.localdate() + timedelta(days=1))
        self.assertEqual((medianoche.hour, medianoche.minute), (0, 0))

    def test_al_iniciar_sesion_caduca_a_medianoche(self):
        self.assertEqual(self.client.session.get_expiry_date(), proxima_medianoche())

    def test_antes_de_medianoche_sigue_dentro(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_despues_de_medianoche_pide_login_otra_vez(self):
        un_minuto_despues = proxima_medianoche() + timedelta(minutes=1)
        with mock.patch("django.utils.timezone.now", return_value=un_minuto_despues):
            respuesta = self.client.get("/")
        self.assertRedirects(respuesta, "/accounts/login/?next=/", fetch_redirect_response=False)

    def test_marcar_despues_de_medianoche_lleva_al_login_sin_volver_a_marcar(self):
        habito = Habito.objects.create(usuario=self.usuaria, nombre="Leer")
        un_minuto_despues = proxima_medianoche() + timedelta(minutes=1)
        with mock.patch("django.utils.timezone.now", return_value=un_minuto_despues):
            respuesta = self.client.post(f"/habitos/{habito.pk}/marcar/")
        # Sin ?next=: después del login irá a inicio, no a una dirección que solo acepta POST
        self.assertRedirects(respuesta, "/accounts/login/", fetch_redirect_response=False)
        self.assertFalse(habito.registros.exists())
