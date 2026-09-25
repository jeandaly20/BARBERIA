from datetime import date, timedelta
from decimal import Decimal

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from citas.models import Cita, Servicio
from usuarios.models import Usuario


def _proximo_lunes() -> date:
    hoy = date.today()
    dias = (0 - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=dias)


@override_settings(PAGOS_REALES_HABILITADOS=False)
class PagoSimuladoTests(APITestCase):
    """Comportamiento por defecto mientras el negocio no cobra de verdad todavía: la cita se
    confirma al instante (sin PayPal) y se avisa por email."""

    def setUp(self):
        self.cliente = Usuario.objects.create_user(email="cliente@example.com", password="claveSegura123")
        self.servicio = Servicio.objects.create(
            nombre="Corte de prueba", precio=Decimal("4.00"), duracion_minutos=30
        )
        self.client.force_authenticate(self.cliente)

    def test_crear_cita_queda_confirmada_al_instante_sin_paypal(self):
        response = self.client.post(reverse("cita-list"), {
            "servicio": self.servicio.id,
            "fecha": str(_proximo_lunes()),
            "hora_inicio": "10:00:00",
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["estado"], Cita.ESTADO_CONFIRMADA)
        self.assertIsNone(response.data["link_pago"])

        cita = Cita.objects.get(pk=response.data["id"])
        self.assertIsNone(cita.paypal_order_id)
        self.assertIsNone(cita.expira_en)

    def test_crear_cita_envia_email_de_confirmacion_y_aviso_al_dueno(self):
        response = self.client.post(reverse("cita-list"), {
            "servicio": self.servicio.id,
            "fecha": str(_proximo_lunes()),
            "hora_inicio": "10:00:00",
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 2)
        destinatarios = {tuple(m.to) for m in mail.outbox}
        self.assertIn(("cliente@example.com",), destinatarios)
