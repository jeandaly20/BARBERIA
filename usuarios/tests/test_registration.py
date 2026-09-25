from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Usuario


class RegistroTests(APITestCase):
    def setUp(self):
        cache.clear()  # el throttle de DRF guarda los conteos en el cache

    def test_registro_exitoso_crea_usuario_cliente(self):
        url = reverse("registro")
        data = {
            "email": "cliente@example.com",
            "nombre": "Juan Pérez",
            "password": "una-contraseña-segura-123",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(email="cliente@example.com")
        self.assertEqual(usuario.rol, Usuario.ROL_CLIENTE)
        self.assertTrue(usuario.check_password("una-contraseña-segura-123"))

    def test_registro_rechaza_email_duplicado(self):
        Usuario.objects.create_user(email="dup@example.com", password="contraseña-segura-123")
        url = reverse("registro")

        response = self.client.post(url, {
            "email": "dup@example.com",
            "password": "otra-contraseña-segura-456",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_devuelve_tokens_jwt(self):
        Usuario.objects.create_user(email="login@example.com", password="una-contraseña-segura-123")
        url = reverse("token_obtain_pair")

        response = self.client.post(url, {
            "email": "login@example.com",
            "password": "una-contraseña-segura-123",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_se_bloquea_tras_demasiados_intentos(self):
        Usuario.objects.create_user(email="fuerza-bruta@example.com", password="claveCorrecta123")
        url = reverse("token_obtain_pair")
        datos_incorrectos = {"email": "fuerza-bruta@example.com", "password": "clave-incorrecta"}

        for _ in range(10):
            self.client.post(url, datos_incorrectos)

        response = self.client.post(url, datos_incorrectos)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
