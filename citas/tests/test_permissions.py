from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from citas.models import Servicio
from usuarios.models import Usuario

def _orden_paypal_falsa(monto, cita_id):
    return {
        "id": f"FAKE-ORDER-{cita_id}",
        "links": [{"rel": "approve", "href": "https://www.sandbox.paypal.com/checkoutnow?token=FAKE"}],
    }


def _proximo_lunes() -> date:
    hoy = date.today()
    dias = (0 - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=dias)


class PermisosCitaTests(APITestCase):
    def setUp(self):
        self.servicio = Servicio.objects.create(
            nombre="Corte de prueba", precio=Decimal("4.00"), duracion_minutos=30
        )
        self.cliente_a = Usuario.objects.create_user(email="a@example.com", password="claveSegura123")
        self.cliente_b = Usuario.objects.create_user(email="b@example.com", password="claveSegura123")
        self.propietario = Usuario.objects.create_user(
            email="dueno@example.com", password="claveSegura123", rol=Usuario.ROL_PROPIETARIO
        )

        parche_paypal = patch("citas.views.crear_orden", side_effect=_orden_paypal_falsa)
        parche_paypal.start()
        self.addCleanup(parche_paypal.stop)

        self.client.force_authenticate(self.cliente_a)
        respuesta = self.client.post(reverse("cita-list"), {
            "servicio": self.servicio.id,
            "fecha": str(_proximo_lunes()),
            "hora_inicio": "10:00:00",
        })
        self.cita_id = respuesta.data["id"]

    def test_cliente_no_puede_ver_calendario_semanal(self):
        self.client.force_authenticate(self.cliente_a)
        url = reverse("cita-semana")
        response = self.client.get(url, {"desde": str(date.today()), "hasta": str(date.today())})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_propietario_si_puede_ver_calendario_semanal(self):
        self.client.force_authenticate(self.propietario)
        url = reverse("cita-semana")
        response = self.client.get(url, {"desde": str(date.today()), "hasta": str(date.today() + timedelta(days=7))})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cliente_no_puede_ver_cita_de_otro_cliente(self):
        self.client.force_authenticate(self.cliente_b)
        url = reverse("cita-detail", kwargs={"pk": self.cita_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cliente_no_puede_cancelar_cita_de_otro_cliente(self):
        self.client.force_authenticate(self.cliente_b)
        url = reverse("cita-cancelar", kwargs={"pk": self.cita_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cliente_no_puede_marcar_no_show(self):
        self.client.force_authenticate(self.cliente_a)
        url = reverse("cita-marcar-no-show", kwargs={"pk": self.cita_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_autenticado_recibe_401(self):
        self.client.force_authenticate(user=None)
        url = reverse("cita-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
