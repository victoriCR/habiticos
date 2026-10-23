from django.test import TestCase, override_settings

from apps.pruebas import crear_usuaria


class PaginasLegalesTests(TestCase):
    def test_privacidad_y_terminos_son_publicas(self):
        # Google las revisa sin iniciar sesión
        privacidad = self.client.get("/privacidad/")
        self.assertContains(privacidad, "Política de privacidad")
        self.assertContains(privacidad, "Ley N.º 8968")
        terminos = self.client.get("/terminos/")
        self.assertContains(terminos, "Términos de uso")

    def test_el_login_enlaza_las_dos(self):
        respuesta = self.client.get("/accounts/login/")
        self.assertContains(respuesta, 'href="/privacidad/"')
        self.assertContains(respuesta, 'href="/terminos/"')

    def test_la_barra_lateral_enlaza_las_dos(self):
        self.client.force_login(crear_usuaria(username="ana"))
        respuesta = self.client.get("/")
        self.assertContains(respuesta, 'class="pie-legal"')

    @override_settings(CONTACTO_EMAIL="")
    def test_sin_correo_de_contacto_no_se_muestra_ninguno(self):
        self.assertNotContains(self.client.get("/privacidad/"), "mailto:")

    def test_con_correo_de_contacto_se_muestra(self):
        # extra_context se calcula al cargar las URLs: se prueba con la vista directamente
        from django.test import RequestFactory

        from config.urls import pagina_legal

        with self.settings(CONTACTO_EMAIL="hola@habiticos.com"):
            vista = pagina_legal("legal/privacidad.html")
            respuesta = vista(RequestFactory().get("/privacidad/"))
            respuesta.render()
        self.assertIn("mailto:hola@habiticos.com", respuesta.content.decode())
