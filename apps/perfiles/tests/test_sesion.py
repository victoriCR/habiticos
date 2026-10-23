from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito
from apps.pruebas import crear_usuaria

SIETE_DIAS = timedelta(days=7)


class SesionDeSieteDiasTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.inicio = timezone.now()

    def test_la_sesion_dura_7_dias(self):
        caduca = self.client.session.get_expiry_date()
        self.assertAlmostEqual(caduca, self.inicio + SIETE_DIAS, delta=timedelta(minutes=1))

    def test_a_los_6_dias_sigue_dentro(self):
        with mock.patch("django.utils.timezone.now", return_value=self.inicio + timedelta(days=6)):
            self.assertEqual(self.client.get("/").status_code, 200)

    def test_pasados_7_dias_pide_login_otra_vez(self):
        despues = self.inicio + SIETE_DIAS + timedelta(minutes=1)
        with mock.patch("django.utils.timezone.now", return_value=despues):
            respuesta = self.client.get("/")
        self.assertRedirects(respuesta, "/accounts/login/?next=/", fetch_redirect_response=False)

    def test_marcar_con_la_sesion_vencida_lleva_al_login_sin_volver_a_marcar(self):
        habito = Habito.objects.create(usuario=self.usuaria, nombre="Leer")
        despues = self.inicio + SIETE_DIAS + timedelta(minutes=1)
        with mock.patch("django.utils.timezone.now", return_value=despues):
            respuesta = self.client.post(f"/habitos/{habito.pk}/marcar/")
        # Sin ?next=: después del login va a inicio, no a una dirección que solo acepta POST
        self.assertRedirects(respuesta, "/accounts/login/", fetch_redirect_response=False)
        self.assertFalse(habito.registros.exists())
