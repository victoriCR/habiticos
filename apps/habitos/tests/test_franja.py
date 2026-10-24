from datetime import time
from unittest import mock

from django.test import TestCase

from apps.habitos.forms import HabitoForm
from apps.habitos.models import Habito
from apps.pruebas import a_las, crear_usuaria


class FranjaHorariaFormTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")

    def datos(self, **extra):
        return {"nombre": "Gym", "descripcion": "", **extra}

    def test_sin_horas_es_valido(self):
        self.assertTrue(HabitoForm(usuario=self.usuaria, data=self.datos()).is_valid())

    def test_con_las_dos_horas_es_valido(self):
        form = HabitoForm(usuario=self.usuaria, data=self.datos(hora_desde="10:00", hora_hasta="17:00"))
        self.assertTrue(form.is_valid())

    def test_con_una_sola_hora_no_es_valido(self):
        form = HabitoForm(usuario=self.usuaria, data=self.datos(hora_desde="10:00"))
        self.assertFalse(form.is_valid())
        self.assertIn("Indicá las dos horas", str(form.non_field_errors()))

    def test_hasta_antes_de_desde_no_es_valido(self):
        form = HabitoForm(usuario=self.usuaria, data=self.datos(hora_desde="17:00", hora_hasta="10:00"))
        self.assertFalse(form.is_valid())
        self.assertIn("hora_hasta", form.errors)


# El botón del habitico fuera de su franja (se ve apagado; al tocarlo, explica por qué)
BOTON_BLOQUEADO = 'class="habito bloqueado"'


class FranjaHorariaMarcarTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.habito = Habito.objects.create(
            usuario=self.usuaria, nombre="Gym", hora_desde=time(10), hora_hasta=time(17)
        )

    def marcar_a_las(self, hora, minuto):
        with mock.patch("django.utils.timezone.now", return_value=a_las(hora, minuto)):
            return self.client.post(f"/habitos/{self.habito.pk}/marcar/", follow=True)

    def test_dentro_de_la_franja_se_marca(self):
        self.marcar_a_las(12, 0)
        self.assertTrue(self.habito.registros.exists())

    def test_los_extremos_cuentan(self):
        self.marcar_a_las(17, 0)
        self.assertTrue(self.habito.registros.exists())

    def test_fuera_de_la_franja_no_se_marca_y_avisa(self):
        respuesta = self.marcar_a_las(17, 1)
        self.assertFalse(self.habito.registros.exists())
        self.assertContains(respuesta, "solo se puede marcar de 10:00 a.m. a 5:00 p.m.")

    def test_desmarcar_fuera_de_la_franja_si_se_permite_durante_la_primera_hora(self):
        self.marcar_a_las(16, 59)
        self.marcar_a_las(17, 30)  # ya terminó la franja, pero no pasó 1 hora
        self.assertFalse(self.habito.registros.exists())

    def test_pasada_la_primera_hora_queda_confirmado(self):
        self.marcar_a_las(16, 59)
        respuesta = self.marcar_a_las(20, 0)
        self.assertTrue(self.habito.registros.exists())
        self.assertContains(respuesta, "ya está confirmado")

    def test_inicio_lo_muestra_bloqueado_fuera_de_la_franja(self):
        with mock.patch("django.utils.timezone.now", return_value=a_las(8, 0)):
            respuesta = self.client.get("/")
        self.assertContains(respuesta, BOTON_BLOQUEADO)
        self.assertContains(respuesta, "🕐 10:00 a.m. – 5:00 p.m.")
        self.assertContains(respuesta, 'data-mensaje="🕐 Todavía no es la hora: se puede marcar de 10:00 a.m. a 5:00 p.m."')

    def test_despues_de_la_franja_explica_que_ya_termino(self):
        with mock.patch("django.utils.timezone.now", return_value=a_las(18, 0)):
            respuesta = self.client.get("/")
        self.assertContains(respuesta, BOTON_BLOQUEADO)
        self.assertContains(
            respuesta,
            "🕐 La franja de hoy ya terminó: se podía marcar de 10:00 a.m. a 5:00 p.m. Mañana podés de nuevo.",
        )

    def test_inicio_no_lo_bloquea_dentro_de_la_franja(self):
        with mock.patch("django.utils.timezone.now", return_value=a_las(12, 0)):
            respuesta = self.client.get("/")
        self.assertNotContains(respuesta, BOTON_BLOQUEADO)
