import datetime

from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import CodigoRecuperacion, Usuario


class RecuperacionPasswordTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user(email="olvido@example.com", password="claveOriginal123")

    def test_solicitar_codigo_para_email_existente_envia_correo(self):
        url = reverse("recuperar_solicitar")
        response = self.client.post(url, {"email": "olvido@example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(CodigoRecuperacion.objects.filter(email="olvido@example.com").exists())

    def test_solicitar_codigo_para_email_inexistente_no_revela_nada(self):
        url = reverse("recuperar_solicitar")
        response = self.client.post(url, {"email": "noexiste@example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(CodigoRecuperacion.objects.filter(email="noexiste@example.com").exists())

    def test_confirmar_con_codigo_valido_cambia_la_contraseña(self):
        CodigoRecuperacion.objects.create(email="olvido@example.com", codigo="123456")
        url = reverse("recuperar_confirmar")

        response = self.client.post(url, {
            "email": "olvido@example.com",
            "codigo": "123456",
            "nueva_password": "claveNuevaSegura123",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("claveNuevaSegura123"))

    def test_no_se_puede_reutilizar_el_mismo_codigo(self):
        CodigoRecuperacion.objects.create(email="olvido@example.com", codigo="123456")
        url = reverse("recuperar_confirmar")
        datos = {"email": "olvido@example.com", "codigo": "123456", "nueva_password": "claveNuevaSegura123"}

        primera = self.client.post(url, datos)
        segunda = self.client.post(url, datos)

        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)

    def test_codigo_expirado_es_rechazado(self):
        registro = CodigoRecuperacion.objects.create(email="olvido@example.com", codigo="123456")
        registro.creado_en = timezone.now() - datetime.timedelta(minutes=11)
        registro.save(update_fields=["creado_en"])

        url = reverse("recuperar_confirmar")
        response = self.client.post(url, {
            "email": "olvido@example.com",
            "codigo": "123456",
            "nueva_password": "claveNuevaSegura123",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_codigo_incorrecto_es_rechazado(self):
        CodigoRecuperacion.objects.create(email="olvido@example.com", codigo="123456")
        url = reverse("recuperar_confirmar")

        response = self.client.post(url, {
            "email": "olvido@example.com",
            "codigo": "000000",
            "nueva_password": "claveNuevaSegura123",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
