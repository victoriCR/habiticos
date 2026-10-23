from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.perfiles.models import Perfil
from apps.pruebas import crear_usuaria
from apps.social.models import Aviso, DiaCompartido, Reaccion, Seguimiento


def con_usuario(username, nombre_usuario=None, **datos):
    """Una usuaria de prueba con @usuario (para que se la pueda encontrar y seguir)."""
    usuaria = crear_usuaria(username=username, **datos)
    Perfil.objects.filter(usuario=usuaria).update(nombre_usuario=nombre_usuario or username)
    return usuaria


class PerfilesYSeguirTests(TestCase):
    def setUp(self):
        self.ana = con_usuario("ana", first_name="Ana")
        self.maria = con_usuario("maria", first_name="María", last_name="López")
        self.client.force_login(self.ana)

    def test_perfil_de_otra_persona_solo_con_sus_habiticos_publicos(self):
        Habito.objects.create(usuario=self.maria, nombre="Leer", publico=True)
        Habito.objects.create(usuario=self.maria, nombre="Terapia", publico=False)
        respuesta = self.client.get("/@maria/")
        self.assertContains(respuesta, "María López")
        self.assertContains(respuesta, "Leer")
        self.assertNotContains(respuesta, "Terapia")
        self.assertContains(respuesta, "Seguir")

    def test_el_perfil_no_se_ve_sin_iniciar_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get("/@maria/").status_code, 302)

    def test_mi_propio_arroba_lleva_a_mi_perfil(self):
        self.assertRedirects(self.client.get("/@ana/"), "/perfil/")

    def test_un_usuario_que_no_existe_da_404(self):
        self.assertEqual(self.client.get("/@nadie/").status_code, 404)

    def test_seguir_y_dejar_de_seguir(self):
        self.client.post("/@maria/seguir/")
        self.assertTrue(Seguimiento.objects.filter(seguidor=self.ana, seguido=self.maria).exists())
        self.assertTrue(Aviso.objects.filter(destinatario=self.maria, tipo="seguir").exists())
        self.assertContains(self.client.get("/@maria/"), "Siguiendo ✓")
        self.client.post("/@maria/seguir/")
        self.assertFalse(Seguimiento.objects.exists())

    def test_seguir_solo_por_post(self):
        self.assertEqual(self.client.get("/@maria/seguir/").status_code, 405)

    def test_el_perfil_cuenta_seguidores(self):
        Seguimiento.objects.create(seguidor=self.ana, seguido=self.maria)
        self.assertContains(self.client.get("/@maria/"), "<strong>1</strong>")
        self.assertContains(self.client.get("/@maria/seguidores/"), "@ana")

    def test_buscar_por_usuario_o_nombre(self):
        self.assertContains(self.client.get("/comunidad/buscar/?q=mar"), "@maria")
        self.assertContains(self.client.get("/comunidad/buscar/?q=lópez"), "@maria")
        self.assertNotContains(self.client.get("/comunidad/buscar/?q=ana"), "@ana")  # a vos no

    def test_buscar_no_muestra_a_quien_no_eligio_usuario(self):
        crear_usuaria(username="sinusuario", first_name="Marta")
        self.assertNotContains(self.client.get("/comunidad/buscar/?q=marta"), "Marta")


class ComunidadTests(TestCase):
    def setUp(self):
        self.ana = con_usuario("ana", first_name="Ana")
        self.maria = con_usuario("maria", first_name="María")
        self.sofia = con_usuario("sofia", first_name="Sofía")
        Seguimiento.objects.create(seguidor=self.ana, seguido=self.maria)
        self.client.force_login(self.ana)
        self.hoy = timezone.localdate()
        self.leer = Habito.objects.create(usuario=self.maria, nombre="Leer", publico=True)

    def marcar(self, habito, dias_atras=0):
        return Registro.objects.create(habito=habito, fecha=self.hoy - timedelta(days=dias_atras))

    def test_marcar_un_habitico_publico_crea_la_tarjeta_del_dia(self):
        self.marcar(self.leer)
        self.assertTrue(DiaCompartido.objects.filter(usuario=self.maria, fecha=self.hoy).exists())
        respuesta = self.client.get("/comunidad/")
        self.assertContains(respuesta, "María")
        self.assertContains(respuesta, "Leer")

    def test_un_habitico_privado_no_crea_tarjeta(self):
        privado = Habito.objects.create(usuario=self.maria, nombre="Terapia", publico=False)
        self.marcar(privado)
        self.assertFalse(DiaCompartido.objects.exists())

    def test_desmarcar_el_ultimo_quita_la_tarjeta(self):
        registro = self.marcar(self.leer)
        registro.delete()
        self.assertFalse(DiaCompartido.objects.exists())

    def test_en_la_tarjeta_nunca_aparece_lo_privado(self):
        privado = Habito.objects.create(usuario=self.maria, nombre="Terapia", publico=False)
        self.marcar(self.leer)
        self.marcar(privado)
        respuesta = self.client.get("/comunidad/")
        self.assertContains(respuesta, "Completó 1 habitico")
        self.assertNotContains(respuesta, "Terapia")

    def test_solo_se_ven_las_personas_que_seguis_y_vos(self):
        de_sofia = Habito.objects.create(usuario=self.sofia, nombre="Correr", publico=True)
        mio = Habito.objects.create(usuario=self.ana, nombre="Agua", publico=True)
        self.marcar(de_sofia)
        self.marcar(mio)
        self.marcar(self.leer)
        respuesta = self.client.get("/comunidad/")
        self.assertNotContains(respuesta, "Correr")
        self.assertContains(respuesta, "Agua")
        self.assertContains(respuesta, "Leer")

    def test_hito_de_7_dias(self):
        for n in range(7):
            self.marcar(self.leer, dias_atras=n)
        self.assertContains(self.client.get("/comunidad/"), "🏆 7 días")

    def test_retomo_despues_de_cortar(self):
        self.marcar(self.leer, dias_atras=5)
        self.marcar(self.leer)
        self.assertContains(self.client.get("/comunidad/"), "🔁 Retomó")

    def test_apoyar_y_quitar_el_apoyo(self):
        self.marcar(self.leer)
        dia = DiaCompartido.objects.get()
        self.client.post(f"/comunidad/dias/{dia.pk}/apoyar/")
        self.assertTrue(Reaccion.objects.filter(dia=dia, usuario=self.ana, tipo="apoyo").exists())
        self.assertTrue(Aviso.objects.filter(destinatario=self.maria, tipo="apoyo").exists())
        self.assertContains(self.client.get("/comunidad/"), "Apoyar · 1")
        self.client.post(f"/comunidad/dias/{dia.pk}/apoyar/")
        self.assertFalse(Reaccion.objects.exists())

    def test_animar_con_una_frase_y_cambiarla(self):
        self.marcar(self.leer)
        dia = DiaCompartido.objects.get()
        self.client.post(f"/comunidad/dias/{dia.pk}/animar/", {"frase": "vamos"})
        self.client.post(f"/comunidad/dias/{dia.pk}/animar/", {"frase": "constancia"})
        animo = Reaccion.objects.get(tipo="animo")
        self.assertEqual(animo.frase, "constancia")  # una sola, la última
        self.assertContains(self.client.get("/comunidad/"), "«¡Qué constancia!»")

    def test_no_se_puede_escribir_texto_libre(self):
        self.marcar(self.leer)
        dia = DiaCompartido.objects.get()
        respuesta = self.client.post(f"/comunidad/dias/{dia.pk}/animar/", {"frase": "algo feo"})
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Reaccion.objects.exists())

    def test_no_se_puede_reaccionar_a_una_tarjeta_que_no_ves(self):
        de_sofia = Habito.objects.create(usuario=self.sofia, nombre="Correr", publico=True)
        self.marcar(de_sofia)
        dia = DiaCompartido.objects.get(usuario=self.sofia)
        self.assertEqual(self.client.post(f"/comunidad/dias/{dia.pk}/apoyar/").status_code, 404)

    def test_sin_seguir_a_nadie_invita_a_buscar(self):
        Seguimiento.objects.all().delete()
        self.assertContains(self.client.get("/comunidad/"), "Todavía no seguís a nadie")


class AvisosTests(TestCase):
    def setUp(self):
        self.ana = con_usuario("ana")
        self.maria = con_usuario("maria", first_name="María")
        self.client.force_login(self.ana)

    def test_la_campanita_cuenta_los_avisos_y_se_marcan_leidos_al_verlos(self):
        Aviso.objects.create(destinatario=self.ana, actor=self.maria, tipo="seguir")
        self.assertContains(self.client.get("/"), 'class="globito"')
        respuesta = self.client.get("/comunidad/avisos/")
        self.assertContains(respuesta, "te empezó a seguir")
        self.assertFalse(Aviso.objects.filter(leido=False).exists())
        self.assertNotContains(self.client.get("/"), 'class="globito"')


class EliminarCuentaConDatosSocialesTests(TestCase):
    def test_eliminar_la_cuenta_borra_tambien_lo_social(self):
        ana = con_usuario("ana")
        maria = con_usuario("maria")
        Seguimiento.objects.create(seguidor=ana, seguido=maria)
        habito = Habito.objects.create(usuario=ana, nombre="Leer", publico=True)
        Registro.objects.create(habito=habito, fecha=timezone.localdate())
        self.client.force_login(ana)
        self.client.post("/perfil/eliminar-cuenta/", {"confirmacion": "eliminar"})
        self.assertFalse(Seguimiento.objects.exists())
        self.assertFalse(DiaCompartido.objects.exists())


class ColumnaDeSeguimientosTests(TestCase):
    def setUp(self):
        self.ana = con_usuario("ana", first_name="Ana")
        self.maria = con_usuario("maria", first_name="María")
        self.sofia = con_usuario("sofia", first_name="Sofía")
        Seguimiento.objects.create(seguidor=self.ana, seguido=self.maria)
        Seguimiento.objects.create(seguidor=self.maria, seguido=self.ana)
        Seguimiento.objects.create(seguidor=self.sofia, seguido=self.ana)
        self.client.force_login(self.ana)

    def lado(self):
        """La columna de la derecha, tal como se ve."""
        return self.client.get("/comunidad/").content.decode().split('<aside class="lado"')[1]

    def test_muestra_cuantos_y_quienes(self):
        respuesta = self.client.get("/comunidad/")
        self.assertContains(respuesta, "Siguiendo (1)")
        self.assertContains(respuesta, "Seguidores (2)")
        self.assertContains(respuesta, "<strong>2</strong> seguidores")
        self.assertContains(respuesta, 'href="/@ana/seguidores/"')
        self.assertContains(respuesta, "@sofia")

    def test_a_quien_te_sigue_y_no_seguis_le_ofrece_seguir(self):
        seguidores = self.lado().split("Seguidores (")[1]
        sofia = seguidores.split("@sofia</span>")[1].split("</li>")[0]
        maria = seguidores.split("@maria</span>")[1].split("</li>")[0]
        self.assertIn(">Seguir</button>", sofia)
        self.assertIn("Siguiendo ✓", maria)

    def test_primero_los_mas_recientes_y_solo_cinco(self):
        for n in range(6):
            Seguimiento.objects.create(seguidor=self.ana, seguido=con_usuario(f"p{n}"))
        siguiendo = self.lado().split("Seguidores (")[0]
        self.assertIn("Siguiendo (7)", siguiendo)
        self.assertEqual(siguiendo.count('class="mini-persona"'), 5)
        self.assertLess(siguiendo.index("@p5<"), siguiendo.index("@p4<"))
        self.assertNotIn("@maria<", siguiendo)
