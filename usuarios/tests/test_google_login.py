from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Usuario


class GoogleLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("google_login")

    @patch("usuarios.views.google_id_token.verify_oauth2_token")
    def test_credencial_valida_crea_usuario_si_no_existia(self, mock_verify):
        mock_verify.return_value = {
            "email": "nuevo.google@example.com",
            "email_verified": True,
            "name": "Usuario Google",
        }

        response = self.client.post(self.url, {"credential": "token-falso"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        usuario = Usuario.objects.get(email="nuevo.google@example.com")
        self.assertEqual(usuario.nombre, "Usuario Google")
        self.assertEqual(usuario.rol, Usuario.ROL_CLIENTE)
        self.assertFalse(usuario.has_usable_password())

    @patch("usuarios.views.google_id_token.verify_oauth2_token")
    def test_credencial_valida_reutiliza_cuenta_existente(self, mock_verify):
        existente = Usuario.objects.create_user(email="ya.existe@example.com", password="claveSegura123")
        mock_verify.return_value = {
            "email": "ya.existe@example.com",
            "email_verified": True,
            "name": "Nombre de Google",
        }

        response = self.client.post(self.url, {"credential": "token-falso"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Usuario.objects.filter(email="ya.existe@example.com").count(), 1)
        existente.refresh_from_db()
        self.assertTrue(existente.check_password("claveSegura123"))  # no se pisa la contraseña

    @patch("usuarios.views.google_id_token.verify_oauth2_token")
    def test_token_invalido_es_rechazado(self, mock_verify):
        mock_verify.side_effect = ValueError("token inválido")

        response = self.client.post(self.url, {"credential": "token-malo"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("usuarios.views.google_id_token.verify_oauth2_token")
    def test_email_no_verificado_es_rechazado(self, mock_verify):
        mock_verify.return_value = {
            "email": "sinverificar@example.com",
            "email_verified": False,
            "name": "Sin Verificar",
        }

        response = self.client.post(self.url, {"credential": "token-falso"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Usuario.objects.filter(email="sinverificar@example.com").exists())
