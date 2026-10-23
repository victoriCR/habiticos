from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.pruebas import crear_usuaria


class SumarHabiticosTests(TestCase):
    """Regla: para sumar (crear o restaurar) uno, todos los activos necesitan 🔥 7."""

    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.hoy = timezone.localdate()

    def crear_con_racha(self, nombre, dias):
        habito = Habito.objects.create(usuario=self.usuaria, nombre=nombre)
        for n in range(1, dias + 1):  # de ayer hacia atrás
            Registro.objects.create(habito=habito, fecha=self.hoy - timedelta(days=n))
        return habito

    def test_el_primero_se_crea_cuando_quieras(self):
        self.client.post("/nuevo/", {"nombre": "Agua"})
        self.assertTrue(Habito.objects.filter(nombre="Agua").exists())

    def test_con_todos_en_7_se_puede_crear(self):
        self.crear_con_racha("Agua", 7)
        self.crear_con_racha("Leer", 10)
        self.assertContains(self.client.get("/"), "+ Nuevo habitico")
        self.client.post("/nuevo/", {"nombre": "Gym"})
        self.assertTrue(Habito.objects.filter(nombre="Gym").exists())

    def test_si_uno_no_llega_explica_y_no_crea(self):
        self.crear_con_racha("Agua", 7)
        self.crear_con_racha("Leer", 4)
        self.assertContains(self.client.get("/"), "🔒 Nuevo habitico")

        respuesta = self.client.get("/nuevo/")
        self.assertContains(respuesta, "Todavía no es momento")
        self.assertContains(respuesta, "🔥 4 de 7 · faltan 3 días")
        self.assertNotContains(respuesta, ">Agua<")  # ese ya cumple: no se lista
        self.assertContains(respuesta, "Crear de todas formas")

        self.client.post("/nuevo/", {"nombre": "Gym"})
        self.assertFalse(Habito.objects.filter(nombre="Gym").exists())

    def test_crear_de_todas_formas(self):
        self.crear_con_racha("Leer", 1)
        respuesta = self.client.get("/nuevo/?forzar=1")
        self.assertContains(respuesta, 'name="nombre"')
        self.client.post("/nuevo/?forzar=1", {"nombre": "Gym"})
        self.assertTrue(Habito.objects.filter(nombre="Gym").exists())

    def test_los_archivados_no_cuentan(self):
        self.crear_con_racha("Agua", 7)
        viejo = self.crear_con_racha("Viejo", 0)
        viejo.activo = False
        viejo.save()
        self.client.post("/nuevo/", {"nombre": "Gym"})
        self.assertTrue(Habito.objects.filter(nombre="Gym").exists())

    def test_restaurar_sigue_la_misma_regla(self):
        self.crear_con_racha("Leer", 2)
        archivado = Habito.objects.create(usuario=self.usuaria, nombre="Gym", activo=False)

        respuesta = self.client.post(f"/habitos/{archivado.pk}/restaurar/")
        self.assertContains(respuesta, "Restaurar de todas formas")
        archivado.refresh_from_db()
        self.assertFalse(archivado.activo)

        self.client.post(f"/habitos/{archivado.pk}/restaurar/", {"forzar": "1"})
        archivado.refresh_from_db()
        self.assertTrue(archivado.activo)
