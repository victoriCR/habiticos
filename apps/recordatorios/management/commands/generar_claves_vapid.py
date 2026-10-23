import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def b64url(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Genera el par de claves VAPID para los recordatorios (una sola vez por sitio)."

    def handle(self, *args, **options):
        privada = ec.generate_private_key(ec.SECP256R1())
        numero = privada.private_numbers().private_value.to_bytes(32, "big")
        publica = privada.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        self.stdout.write(f"VAPID_PUBLIC_KEY={b64url(publica)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={b64url(numero)}")
        self.stderr.write("Guardalas en .env (y en Render). La privada es secreta: no la compartas.")
