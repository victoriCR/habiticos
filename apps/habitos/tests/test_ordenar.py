import json

from django.test import TestCase

from apps.habitos.models import Habito
from apps.pruebas import crear_usuaria


class OrdenarTests(TestCase):
    def setUp(self):
        self.usuaria = crear_usuaria(username="ana")
        self.client.force_login(self.usuaria)
        self.a = Habito.objects.create(usuario=self.usuaria, nombre="Agua")
        self.b = Habito.objects.create(usuario=self.usuaria, nombre="Bici")
        self.c = Habito.objects.create(usuario=self.usuaria, nombre="Cama")

    def ordenar(self, ids):
        return self.client.post(
            "/habitos/ordenar/",
            data=json.dumps({"orden": ids}),
            content_type="application/json",
        )

    def nombres_en_inicio(self):
        html = self.client.get("/").content.decode()
        return sorted(["Agua", "Bici", "Cama"], key=html.index)

    def test_guarda_el_nuevo_orden(self):
        respuesta = self.ordenar([self.c.pk, self.a.pk, self.b.pk])
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(self.nombres_en_inicio(), ["Cama", "Agua", "Bici"])

    def test_un_habito_nuevo_va_al_final(self):
        self.ordenar([self.c.pk, self.a.pk, self.b.pk])
        # Los otros no llevan 🔥 7: se crea "de todas formas" (bloqueo suave)
        self.client.post("/nuevo/?forzar=1", {"nombre": "Dormir"})
        nuevo = Habito.objects.get(nombre="Dormir")
        self.assertEqual(list(self.usuaria.habitos.all())[-1], nuevo)

    def test_no_acepta_habitos_ajenos(self):
        otra = crear_usuaria(username="otra")
        ajeno = Habito.objects.create(usuario=otra, nombre="Ajeno")
        respuesta = self.ordenar([ajeno.pk, self.a.pk])
        self.assertEqual(respuesta.status_code, 400)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.orden, 0)

    def test_no_acepta_datos_invalidos(self):
        self.assertEqual(self.ordenar(["x"]).status_code, 400)
        self.assertEqual(self.ordenar([self.a.pk, self.a.pk]).status_code, 400)
        respuesta = self.client.post(
            "/habitos/ordenar/", data="no es json", content_type="application/json"
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_solo_acepta_post(self):
        self.assertEqual(self.client.get("/habitos/ordenar/").status_code, 405)
