from django.test import TestCase

from apps.habitos.models import Habito
from apps.pruebas import crear_usuaria


class AdminTests(TestCase):
    def test_el_mensaje_de_eliminado_tiene_el_espacio(self):
        admin = crear_usuaria(username="admin", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        habito = Habito.objects.create(usuario=admin, nombre="Probar")
        respuesta = self.client.post(
            f"/admin/habitos/habito/{habito.pk}/delete/", {"post": "yes"}, follow=True
        )
        self.assertContains(respuesta, "El habitico “Probar” fue eliminado con éxito.")
