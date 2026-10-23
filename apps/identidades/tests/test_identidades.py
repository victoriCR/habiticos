import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.habitos.forms import HabitoForm
from apps.habitos.models import Habito
from apps.identidades.models import Identidad
from apps.pruebas import crear_usuaria


class IdentidadesTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.saludable = Identidad.objects.get(nombre="Soy una persona saludable")
        self.activa = Identidad.objects.get(nombre="Soy una persona activa")

    def elegir(self, identidad):
        return self.client.post(f"/identidades/{identidad.pk}/elegir/")

    def elegidas(self):
        return [e.identidad for e in self.usuaria.identidades_elegidas.all()]

    def test_el_catalogo_trae_las_10_identidades(self):
        self.assertEqual(Identidad.objects.count(), 10)

    def test_tocar_elige_y_volver_a_tocar_quita(self):
        self.elegir(self.saludable)
        self.elegir(self.activa)
        self.assertEqual(self.elegidas(), [self.saludable, self.activa])
        self.elegir(self.saludable)
        self.assertEqual(self.elegidas(), [self.activa])

    def test_ordenar_identidades(self):
        self.elegir(self.saludable)
        self.elegir(self.activa)
        respuesta = self.client.post(
            "/identidades/ordenar/",
            data=json.dumps({"orden": [self.activa.pk, self.saludable.pk]}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(self.elegidas(), [self.activa, self.saludable])

    def test_ordenar_rechaza_identidades_no_elegidas(self):
        self.elegir(self.saludable)
        respuesta = self.client.post(
            "/identidades/ordenar/",
            data=json.dumps({"orden": [self.activa.pk, self.saludable.pk]}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_el_formulario_de_habito_solo_ofrece_las_identidades_elegidas(self):
        self.elegir(self.activa)
        opciones = [str(i) for i in HabitoForm(usuario=self.usuaria).fields["identidad"].queryset]
        self.assertEqual(opciones, ["💪 Soy una persona activa"])

    def test_editar_un_habito_conserva_su_identidad_aunque_ya_no_este_elegida(self):
        habito = Habito.objects.create(
            usuario=self.usuaria, nombre="Correr", identidad=self.saludable
        )
        form = HabitoForm(usuario=self.usuaria, instance=habito)
        self.assertIn(self.saludable, form.fields["identidad"].queryset)

    def test_la_identidad_se_elige_con_tarjetas_y_no_con_un_desplegable(self):
        self.elegir(self.activa)
        respuesta = self.client.get("/nuevo/")
        self.assertNotContains(respuesta, "<select")
        self.assertContains(respuesta, 'type="radio"', count=2)  # Ninguna + activa
        self.assertContains(respuesta, "Ninguna")
        self.assertContains(respuesta, "💪 Soy una persona activa")

    def test_crear_habito_desde_un_grupo_vacio_viene_con_su_identidad(self):
        self.elegir(self.activa)
        respuesta = self.client.get(f"/nuevo/?identidad={self.activa.pk}")
        self.assertEqual(respuesta.context["form"].initial["identidad"], str(self.activa.pk))


class BienvenidaTests(TestCase):
    def test_la_primera_vez_muestra_identidades_y_despues_ya_no(self):
        nueva = get_user_model().objects.create_user(username="nueva")
        self.client.force_login(nueva)
        self.assertRedirects(
            self.client.get("/"), "/identidades/?bienvenida=1", fetch_redirect_response=False
        )
        respuesta = self.client.get("/identidades/?bienvenida=1")
        self.assertContains(respuesta, "Ahora no")
        # Ya la vio (aunque no eligió ninguna): no se vuelve a mostrar
        self.assertEqual(self.client.get("/").status_code, 200)
