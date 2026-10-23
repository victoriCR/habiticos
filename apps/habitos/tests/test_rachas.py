from datetime import timedelta

from django.test import SimpleTestCase

from apps.habitos.rachas import calcular_racha, constancia, dias_en_la_semana, mejor_racha
from apps.pruebas import HOY, dias_atras


class CalcularRachaTests(SimpleTestCase):
    def test_sin_registros(self):
        self.assertEqual(calcular_racha(set(), HOY), 0)

    def test_hoy_ayer_y_anteayer(self):
        self.assertEqual(calcular_racha(dias_atras(0, 1, 2), HOY), 3)

    def test_hoy_aun_no_marcado_no_rompe_la_racha(self):
        self.assertEqual(calcular_racha(dias_atras(1, 2), HOY), 2)

    def test_ni_hoy_ni_ayer(self):
        self.assertEqual(calcular_racha(dias_atras(2, 3, 4), HOY), 0)

    def test_un_hueco_corta_la_racha(self):
        self.assertEqual(calcular_racha(dias_atras(0, 1, 3, 4, 5), HOY), 2)


class MejorRachaTests(SimpleTestCase):
    def test_sin_registros(self):
        self.assertEqual(mejor_racha(set()), 0)

    def test_encuentra_la_mas_larga(self):
        self.assertEqual(mejor_racha(dias_atras(0, 1, 5, 6, 7, 8, 20)), 4)


class ConstanciaTests(SimpleTestCase):
    def test_sin_habiticos_no_hay_constancia(self):
        self.assertIsNone(constancia([], HOY))

    def test_solo_cuenta_desde_que_empezo_y_hoy_solo_si_esta_marcado(self):
        # Empezó hace 9 días (9 días posibles hasta ayer) y cumplió 6
        inicio = HOY - timedelta(days=9)
        self.assertEqual(constancia([(inicio, dias_atras(1, 2, 3, 5, 7, 9))], HOY), 67)
        # Si hoy también está marcado, hoy cuenta: 7 de 10
        self.assertEqual(constancia([(inicio, dias_atras(0, 1, 2, 3, 5, 7, 9))], HOY), 70)

    def test_solo_mira_los_ultimos_30_dias(self):
        hace_un_anio = HOY - timedelta(days=365)
        todos_los_dias = {HOY - timedelta(days=n) for n in range(1, 31)}
        self.assertEqual(constancia([(hace_un_anio, todos_los_dias)], HOY), 100)

    def test_dias_en_la_semana(self):
        self.assertEqual(dias_en_la_semana(dias_atras(0, 1, 2, 6, 7, 20), HOY), 4)
