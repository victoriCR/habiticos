import base64
import json
from datetime import time, timedelta
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.habitos.models import Habito, Registro
from apps.pruebas import crear_usuaria
from apps.recordatorios.logica import momento_local, pendientes
from apps.recordatorios.models import Ajustes, Enviado, Suscripcion


def b64url(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def suscripcion_de_prueba(usuario):
    """Una suscripción con claves reales (como las que da un navegador), para cifrar de verdad."""
    clave = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return Suscripcion.objects.create(
        usuario=usuario,
        endpoint=f"https://push.ejemplo.com/{usuario.pk}",
        p256dh=b64url(clave),
        auth=b64url(b"0123456789abcdef"),
    )


def claves_vapid():
    privada = ec.generate_private_key(ec.SECP256R1())
    publica = privada.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return b64url(publica), b64url(privada.private_numbers().private_value.to_bytes(32, "big"))


class CuandoAvisarTests(TestCase):
    def setUp(self):
        self.ana = crear_usuaria(username="ana")
        suscripcion_de_prueba(self.ana)
        self.hoy = timezone.localdate()
        self.gym = Habito.objects.create(
            usuario=self.ana, nombre="Gym", hora_desde=time(10), hora_hasta=time(17)
        )

    def a_las(self, hora, minuto=0):
        return pendientes(momento_local(self.hoy, time(hora, minuto)))

    def test_falta_una_hora_para_que_termine_la_franja(self):
        avisos = self.a_las(16, 0)
        self.assertEqual(len(avisos), 1)
        usuario, clave, titulo, texto = avisos[0]
        self.assertEqual(clave, f"franja:{self.gym.pk}")
        self.assertEqual(titulo, "Gym")
        self.assertEqual(texto, "Queda 1 hora. Se puede marcar hasta las 5:00 p.m.")

    def test_mas_tarde_dice_cuantos_minutos_quedan(self):
        self.assertEqual(self.a_las(16, 30)[0][3], "Quedan 30 minutos. Se puede marcar hasta las 5:00 p.m.")
        Enviado.objects.all().delete()
        self.assertEqual(self.a_las(16, 59)[0][3], "Queda 1 minuto. Se puede marcar hasta las 5:00 p.m.")

    def test_antes_de_la_ultima_hora_o_despues_del_fin_no_avisa(self):
        self.assertEqual(self.a_las(15, 45), [])
        self.assertEqual(self.a_las(17, 0), [])

    def test_si_ya_esta_hecho_no_avisa(self):
        Registro.objects.create(habito=self.gym, fecha=self.hoy)
        self.assertEqual(self.a_las(16, 15), [])

    def test_si_lo_desactivaste_no_avisa(self):
        Ajustes.objects.create(usuario=self.ana, fin_de_franja=False)
        self.assertEqual(self.a_las(16, 15), [])

    def test_sin_telefono_suscripto_no_hay_nada_que_mandar(self):
        Suscripcion.objects.all().delete()
        self.assertEqual(self.a_las(16, 15), [])

    def test_racha_en_riesgo_a_la_noche(self):
        leer = Habito.objects.create(usuario=self.ana, nombre="Leer")
        for n in (1, 2, 3):
            Registro.objects.create(habito=leer, fecha=self.hoy - timedelta(days=n))
        avisos = [a for a in self.a_las(20, 0) if a[1] == "racha"]
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0][2], "🔥 Todavía podés salvar tu racha")
        self.assertIn("Leer (3 días)", avisos[0][3])

    def test_racha_de_un_dia_o_antes_de_las_8_no_avisa(self):
        leer = Habito.objects.create(usuario=self.ana, nombre="Leer")
        Registro.objects.create(habito=leer, fecha=self.hoy - timedelta(days=1))
        self.assertEqual([a for a in self.a_las(21, 0) if a[1] == "racha"], [])
        Registro.objects.create(habito=leer, fecha=self.hoy - timedelta(days=2))
        self.assertEqual([a for a in self.a_las(19, 45) if a[1] == "racha"], [])

    def test_lo_ya_enviado_hoy_no_se_repite(self):
        Enviado.objects.create(usuario=self.ana, clave=f"franja:{self.gym.pk}", fecha=self.hoy)
        self.assertEqual(self.a_las(16, 15), [])


class EnviarTests(TestCase):
    def setUp(self):
        self.publica, self.privada = claves_vapid()
        self.ana = crear_usuaria(username="ana")
        self.suscripcion = suscripcion_de_prueba(self.ana)
        Habito.objects.create(usuario=self.ana, nombre="Gym", hora_desde=time(0), hora_hasta=time(23, 59))

    def test_el_comando_cifra_y_manda_una_sola_vez(self):
        respuesta = mock.Mock(status_code=201)
        hace_falta = momento_local(timezone.localdate(), time(23, 15))
        with override_settings(VAPID_PUBLIC_KEY=self.publica, VAPID_PRIVATE_KEY=self.privada), \
                mock.patch("pywebpush.requests.post", return_value=respuesta) as post, \
                mock.patch("django.utils.timezone.localtime", return_value=hace_falta):
            call_command("enviar_recordatorios", stdout=mock.Mock())
            call_command("enviar_recordatorios", stdout=mock.Mock())  # un minuto después
        self.assertEqual(post.call_count, 1)
        url, = post.call_args.args
        self.assertEqual(url, self.suscripcion.endpoint)
        cabeceras = post.call_args.kwargs["headers"]
        self.assertIn("vapid", cabeceras["Authorization"].lower())  # firmado con las claves del sitio
        self.assertEqual(cabeceras["Content-Encoding"], "aes128gcm")  # cifrado para ese teléfono

    def test_un_telefono_que_ya_no_existe_se_borra(self):
        from apps.recordatorios.enviar import notificar

        respuesta = mock.Mock(status_code=410, text="Gone")
        with override_settings(VAPID_PUBLIC_KEY=self.publica, VAPID_PRIVATE_KEY=self.privada), \
                mock.patch("pywebpush.requests.post", return_value=respuesta):
            self.assertEqual(notificar(self.ana, "Hola", "Prueba"), 0)
        self.assertFalse(Suscripcion.objects.exists())

    @override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY="")
    def test_sin_claves_no_hace_nada(self):
        with mock.patch("pywebpush.requests.post") as post:
            call_command("enviar_recordatorios", stdout=mock.Mock())
        post.assert_not_called()


@override_settings(VAPID_PUBLIC_KEY="publica", VAPID_PRIVATE_KEY="privada")
class PaginaRecordatoriosTests(TestCase):
    def setUp(self):
        self.ana = crear_usuaria(username="ana")
        self.client.force_login(self.ana)

    def test_la_pagina_muestra_los_ajustes(self):
        respuesta = self.client.get("/recordatorios/")
        self.assertContains(respuesta, "Fin de la franja horaria")
        self.assertContains(respuesta, 'data-clave="publica"')

    def test_guardar_ajustes(self):
        self.client.post("/recordatorios/", {"racha_en_riesgo": "on"})
        ajustes = Ajustes.objects.get(usuario=self.ana)
        self.assertFalse(ajustes.fin_de_franja)
        self.assertTrue(ajustes.racha_en_riesgo)

    def test_suscribir_y_desuscribir_este_telefono(self):
        datos = {"endpoint": "https://push.ejemplo.com/abc", "keys": {"p256dh": "x", "auth": "y"}}
        respuesta = self.client.post("/recordatorios/suscribir/", json.dumps(datos), content_type="application/json")
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(self.ana.suscripciones.count(), 1)
        self.client.post("/recordatorios/desuscribir/", json.dumps({"endpoint": datos["endpoint"]}), content_type="application/json")
        self.assertEqual(self.ana.suscripciones.count(), 0)

    def test_suscripcion_invalida(self):
        respuesta = self.client.post("/recordatorios/suscribir/", json.dumps({"endpoint": "http://malo"}), content_type="application/json")
        self.assertEqual(respuesta.status_code, 400)

    @override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY="")
    def test_sin_claves_avisa_que_no_estan_disponibles(self):
        self.assertContains(self.client.get("/recordatorios/"), "todavía no están disponibles")

    def test_aparece_en_el_menu(self):
        self.assertContains(self.client.get("/"), 'href="/recordatorios/"')
