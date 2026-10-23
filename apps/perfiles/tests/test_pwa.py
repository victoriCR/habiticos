import json

from django.test import TestCase, override_settings

from apps.pruebas import crear_usuaria


class AppInstalableTests(TestCase):
    def test_manifiesto(self):
        respuesta = self.client.get("/manifest.webmanifest")
        self.assertEqual(respuesta["Content-Type"], "application/manifest+json")
        datos = json.loads(respuesta.content)
        self.assertEqual(datos["name"], "Habiticos")
        self.assertEqual(datos["display"], "standalone")
        self.assertEqual(datos["start_url"], "/")
        tamanos = {(icono["sizes"], icono["purpose"]) for icono in datos["icons"]}
        self.assertIn(("192x192", "any"), tamanos)
        self.assertIn(("512x512", "maskable"), tamanos)

    def test_service_worker_en_la_raiz_y_sin_cache(self):
        respuesta = self.client.get("/sw.js")
        self.assertEqual(respuesta["Content-Type"], "application/javascript")
        self.assertIn("no-cache", respuesta["Cache-Control"])
        contenido = respuesta.content.decode()
        self.assertIn('const SIN_CONEXION = "/sin-conexion/"', contenido)
        self.assertIn("css/habiticos", contenido)

    def test_la_pagina_sin_conexion_no_tiene_datos_de_nadie(self):
        usuaria = crear_usuaria(username="ana", first_name="Ana", last_name="Pérez")
        self.client.force_login(usuaria)
        respuesta = self.client.get("/sin-conexion/")
        self.assertContains(respuesta, "Sin conexión")
        self.assertNotContains(respuesta, "Ana Pérez")
        self.assertNotContains(respuesta, "csrfmiddlewaretoken")

    def test_todas_las_paginas_enlazan_el_manifiesto_y_el_icono_del_iphone(self):
        respuesta = self.client.get("/accounts/login/")
        self.assertContains(respuesta, 'rel="manifest" href="/manifest.webmanifest"')
        self.assertContains(respuesta, 'rel="apple-touch-icon"')
        self.assertContains(respuesta, "js/pwa.js")

    def test_el_aviso_para_instalar_solo_con_sesion(self):
        self.assertNotContains(self.client.get("/accounts/login/"), 'id="instalar"')
        self.client.force_login(crear_usuaria(username="ana"))
        self.assertContains(self.client.get("/"), 'id="instalar" hidden')

    @override_settings(DEBUG=True)
    def test_en_desarrollo_no_se_registra_el_service_worker(self):
        self.assertContains(self.client.get("/accounts/login/"), 'data-pwa="inactiva"')

    def test_en_produccion_si(self):
        self.assertContains(self.client.get("/accounts/login/"), 'data-pwa="activa"')
