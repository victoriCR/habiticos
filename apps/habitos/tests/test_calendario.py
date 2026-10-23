from datetime import date, time, timedelta
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.habitos.calendario import navegacion, primer_dia_del_mes
from apps.habitos.models import Habito, Registro
from apps.pruebas import HOY, a_las, crear_usuaria


class MesTests(SimpleTestCase):
    def test_lee_el_mes_de_la_direccion(self):
        self.assertEqual(primer_dia_del_mes("2026-09", HOY), date(2026, 9, 1))

    def test_texto_invalido_usa_el_mes_actual(self):
        self.assertEqual(primer_dia_del_mes("hola", HOY), date(2026, 10, 1))
        self.assertEqual(primer_dia_del_mes(None, HOY), date(2026, 10, 1))

    def test_se_puede_ver_un_mes_futuro(self):
        self.assertEqual(primer_dia_del_mes("2027-01", HOY), date(2027, 1, 1))

    def test_un_anio_absurdo_usa_el_mes_actual(self):
        self.assertEqual(primer_dia_del_mes("0001-01", HOY), date(2026, 10, 1))

    def test_navegacion_siempre_permite_ir_y_volver(self):
        nav = navegacion(date(2026, 10, 1), HOY)
        self.assertEqual(nav["anterior"], date(2026, 9, 1))
        self.assertEqual(nav["siguiente"], date(2026, 11, 1))
        self.assertTrue(nav["es_este_mes"])

    def test_navegacion_cambia_de_anio(self):
        nav = navegacion(date(2027, 1, 1), HOY)
        self.assertEqual(nav["anterior"], date(2026, 12, 1))
        self.assertEqual(nav["siguiente"], date(2027, 2, 1))
        self.assertFalse(nav["es_este_mes"])


class CalendarioTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.habito = Habito.objects.create(usuario=self.usuaria, nombre="Leer")
        self.hoy = timezone.localdate()
        # Dos días cumplidos este mes (si hoy es día 1, solo hoy)
        self.dias = {self.hoy, self.hoy - timedelta(days=1)}
        self.dias = {d for d in self.dias if d.month == self.hoy.month}
        for dia in self.dias:
            Registro.objects.create(habito=self.habito, fecha=dia)

    def test_calendario_de_un_habito_muestra_los_dias_cumplidos(self):
        respuesta = self.client.get(f"/habitos/{self.habito.pk}/calendario/")
        self.assertEqual(respuesta.content.decode().count("✅"), len(self.dias))
        self.assertContains(respuesta, "celda editable hoy")

    def test_calendario_de_un_habito_ajeno_da_404(self):
        otra = crear_usuaria(username="otra")
        ajeno = Habito.objects.create(usuario=otra, nombre="Correr")
        respuesta = self.client.get(f"/habitos/{ajeno.pk}/calendario/")
        self.assertEqual(respuesta.status_code, 404)

    def test_tabla_del_mes_muestra_cada_habito_y_sus_dias(self):
        Habito.objects.create(usuario=self.usuaria, nombre="Meditar")
        respuesta = self.client.get("/calendario/")
        self.assertContains(respuesta, "Leer")
        self.assertContains(respuesta, "Meditar")
        self.assertEqual(respuesta.content.decode().count("✅"), len(self.dias))

    def test_tabla_no_muestra_habitos_archivados(self):
        Habito.objects.create(usuario=self.usuaria, nombre="Viejo", activo=False)
        respuesta = self.client.get("/calendario/")
        self.assertNotContains(respuesta, "Viejo")

    def test_mes_anterior_sin_registros(self):
        Habito.objects.filter(pk=self.habito.pk).update(
            creado=timezone.now() - timedelta(days=90)
        )
        mes_pasado = (self.hoy.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        respuesta = self.client.get(f"/calendario/?mes={mes_pasado}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "✅")


class RegistrarDiaTests(TestCase):
    """Corregir hoy y ayer desde el calendario individual."""

    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.habito = Habito.objects.create(
            usuario=self.usuaria,
            nombre="Última comida",
            hora_desde=time(18),
            hora_hasta=time(23),
        )
        self.hoy = timezone.localdate()
        self.ayer = self.hoy - timedelta(days=1)

    def registrar(self, fecha, hora=None, accion="guardar", ahora=(12, 0)):
        datos = {"fecha": fecha.isoformat(), "accion": accion}
        if hora:
            datos["hora"] = hora
        with mock.patch("django.utils.timezone.now", return_value=a_las(*ahora)):
            return self.client.post(
                f"/habitos/{self.habito.pk}/registrar-dia/", datos, follow=True
            )

    def hora_guardada(self, fecha):
        registro = self.habito.registros.get(fecha=fecha)
        return timezone.localtime(registro.marcado).strftime("%H:%M")

    def test_marcar_ayer_a_la_hora_olvidada(self):
        # El ejemplo: a la 1 a.m. registro la cena de ayer a las 10 p.m.
        self.registrar(self.ayer, "22:00", ahora=(1, 0))
        self.assertEqual(self.hora_guardada(self.ayer), "22:00")

    def test_cambiar_la_hora_de_un_dia_ya_marcado(self):
        self.registrar(self.ayer, "19:00")
        self.registrar(self.ayer, "21:30")
        self.assertEqual(self.habito.registros.count(), 1)
        self.assertEqual(self.hora_guardada(self.ayer), "21:30")

    def test_desmarcar(self):
        self.registrar(self.ayer, "20:00")
        self.registrar(self.ayer, accion="desmarcar")
        self.assertFalse(self.habito.registros.exists())

    def test_anteayer_no_se_puede(self):
        respuesta = self.registrar(self.hoy - timedelta(days=2), "20:00")
        self.assertFalse(self.habito.registros.exists())
        self.assertContains(respuesta, "Solo se pueden modificar hoy y ayer.")

    def test_fuera_de_la_franja_no_se_puede(self):
        respuesta = self.registrar(self.ayer, "23:30")
        self.assertFalse(self.habito.registros.exists())
        self.assertContains(respuesta, "solo se puede marcar de 6:00 p.m. a 11:00 p.m.")

    def test_hoy_a_una_hora_futura_no_se_puede(self):
        respuesta = self.registrar(self.hoy, "20:00", ahora=(19, 0))
        self.assertFalse(self.habito.registros.exists())
        self.assertContains(respuesta, "todavía no ha llegado")

    def test_hoy_a_una_hora_pasada_si_se_puede(self):
        self.registrar(self.hoy, "18:30", ahora=(19, 0))
        self.assertEqual(self.hora_guardada(self.hoy), "18:30")

    def test_hora_invalida(self):
        respuesta = self.registrar(self.ayer, "las diez")
        self.assertFalse(self.habito.registros.exists())
        self.assertContains(respuesta, "Indicá una hora válida.")

    def test_habito_ajeno_da_404(self):
        otra = crear_usuaria(username="otra")
        ajeno = Habito.objects.create(usuario=otra, nombre="Ajeno")
        respuesta = self.client.post(
            f"/habitos/{ajeno.pk}/registrar-dia/",
            {"fecha": self.ayer.isoformat(), "accion": "guardar", "hora": "20:00"},
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_el_calendario_solo_deja_tocar_hoy_y_ayer_y_muestra_la_hora(self):
        self.registrar(self.ayer, "22:00")
        respuesta = self.client.get(
            f"/habitos/{self.habito.pk}/calendario/?mes={self.ayer:%Y-%m}"
        )
        html = respuesta.content.decode()
        self.assertIn(f'data-fecha="{self.ayer.isoformat()}"', html)
        self.assertNotIn(f'data-fecha="{(self.hoy - timedelta(days=2)).isoformat()}"', html)
        self.assertIn("10:00 p.m.", html)
