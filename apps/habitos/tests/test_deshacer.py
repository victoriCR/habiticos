from datetime import datetime, time, timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.pruebas import a_las, crear_usuaria

# El botón de un habitico hecho y confirmado (fijo: al tocarlo, solo muestra un aviso)
CONFIRMADO = 'class="habito hecho confirmado"'


class DeshacerDuranteLaPrimeraHoraTests(TestCase):
    """Un habitico marcado se puede deshacer durante 1 hora; después queda confirmado."""

    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.leer = Habito.objects.create(usuario=self.usuaria, nombre="Leer")

    def en(self, hora, minuto, accion):
        with mock.patch("django.utils.timezone.now", return_value=a_las(hora, minuto)):
            return accion()

    def marcar(self, hora, minuto):
        return self.en(hora, minuto, lambda: self.client.post(f"/habitos/{self.leer.pk}/marcar/", follow=True))

    def hoy(self, hora, minuto):
        return self.en(hora, minuto, lambda: self.client.get("/"))

    def test_durante_la_primera_hora_muestra_hasta_cuando_se_puede_deshacer(self):
        self.marcar(13, 50)
        respuesta = self.hoy(14, 10)
        self.assertContains(respuesta, "Tocá para deshacer · hasta las 2:50 p.m.")
        self.assertNotContains(respuesta, CONFIRMADO)

    def test_durante_la_primera_hora_se_puede_deshacer(self):
        self.marcar(13, 50)
        self.marcar(14, 49)
        self.assertFalse(self.leer.registros.exists())

    def test_pasada_la_hora_queda_confirmado_y_no_se_puede_deshacer(self):
        self.marcar(13, 50)
        respuesta = self.hoy(14, 50)
        self.assertNotContains(respuesta, "Tocá para deshacer")
        self.assertContains(respuesta, CONFIRMADO)
        # Se puede tocar, pero no se deshace: un aviso (neutral, no de error) explica por qué
        respuesta = self.marcar(15, 0)
        self.assertTrue(self.leer.registros.exists())
        self.assertContains(
            respuesta,
            '<p class="aviso aviso-info" role="status">✓ «Leer» ya está confirmado: '
            "solo se puede deshacer o cambiar durante la primera hora.</p>",
            html=True,
        )

    def test_el_confirmado_no_esta_desactivado_y_explica_por_que(self):
        self.marcar(13, 50)
        fila = self.hoy(14, 50).content.decode().split(CONFIRMADO)[1].split(">")[0]
        self.assertNotIn("disabled", fila)
        self.assertIn('data-nombre="Leer"', fila)
        self.assertIn('data-mensaje="✓ Marcado a las ', fila)
        self.assertIn("Ya está confirmado: solo se puede cambiar o deshacer durante la primera hora.", fila)

    def test_los_registros_anteriores_a_esta_regla_cuentan_como_confirmados(self):
        registro = Registro.objects.create(habito=self.leer, fecha=timezone.localdate())
        Registro.objects.filter(pk=registro.pk).update(tocado=None)
        self.assertContains(self.client.get("/"), CONFIRMADO)
        self.client.post(f"/habitos/{self.leer.pk}/marcar/")
        self.assertTrue(self.leer.registros.exists())


class CalendarioConfirmadoTests(TestCase):
    """El calendario no es una puerta trasera: un día confirmado no se cambia ni se borra."""

    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.cena = Habito.objects.create(
            usuario=self.usuaria, nombre="Última comida", hora_desde=time(18), hora_hasta=time(23)
        )
        self.hoy = timezone.localdate()
        self.ayer = self.hoy - timedelta(days=1)

    def en(self, hora, minuto, accion):
        with mock.patch("django.utils.timezone.now", return_value=a_las(hora, minuto)):
            return accion()

    def registrar(self, a_la_hora, al_minuto, **datos):
        """Registrar ayer, tocándolo a la hora simulada `a_la_hora`:`al_minuto`."""
        datos = {"fecha": self.ayer.isoformat(), "accion": "guardar", **datos}
        return self.en(a_la_hora, al_minuto, lambda: self.client.post(
            f"/habitos/{self.cena.pk}/registrar-dia/", datos, follow=True
        ))

    def calendario(self, hora, minuto):
        return self.en(hora, minuto, lambda: self.client.get(
            f"/habitos/{self.cena.pk}/calendario/?mes={self.ayer:%Y-%m}"
        )).content.decode()

    def test_registrar_ayer_cuenta_la_hora_desde_que_lo_tocaste(self):
        # A la 1 a.m. registro la cena de ayer a las 10 p.m.: igual tengo mi hora para corregir
        self.registrar(1, 0, hora="22:00")
        self.registrar(1, 30, hora="21:30")
        registro = self.cena.registros.get()
        self.assertEqual(timezone.localtime(registro.marcado).strftime("%H:%M"), "21:30")

    def test_pasada_la_hora_no_se_cambia_la_hora_ni_se_desmarca(self):
        self.registrar(1, 0, hora="22:00")
        respuesta = self.registrar(2, 30, hora="20:00")
        self.assertContains(respuesta, "ya está confirmado")
        self.registrar(2, 30, accion="desmarcar")
        registro = self.cena.registros.get()
        self.assertEqual(timezone.localtime(registro.marcado).strftime("%H:%M"), "22:00")

    def test_un_dia_confirmado_ya_no_se_puede_tocar_en_el_calendario(self):
        self.registrar(1, 0, hora="22:00")
        self.assertIn(f'data-fecha="{self.ayer.isoformat()}"', self.calendario(1, 30))
        self.assertNotIn(f'data-fecha="{self.ayer.isoformat()}"', self.calendario(2, 30))

    def test_al_tocar_un_dia_confirmado_se_explica_por_que(self):
        self.registrar(1, 0, hora="22:00")
        self.assertNotIn("celda informativa", self.calendario(1, 30))
        pagina = self.calendario(2, 30)
        self.assertIn("celda informativa", pagina)
        self.assertIn(
            "✓ Marcado a las 10:00 p.m. Ya está confirmado: solo se puede cambiar o "
            "deshacer durante la primera hora.",
            pagina,
        )

    def test_los_dias_anteriores_a_ayer_explican_que_solo_se_cambian_hoy_y_ayer(self):
        anteayer = self.ayer - timedelta(days=1)
        Registro.objects.create(
            habito=self.cena, fecha=anteayer,
            marcado=timezone.make_aware(datetime.combine(anteayer, time(19))),
        )
        pagina = self.en(12, 0, lambda: self.client.get(
            f"/habitos/{self.cena.pk}/calendario/?mes={anteayer:%Y-%m}"
        )).content.decode()
        self.assertIn("✓ Marcado a las 7:00 p.m. Solo se pueden cambiar hoy y ayer.", pagina)
