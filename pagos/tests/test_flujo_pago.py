from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from citas.disponibilidad import calcular_slots
from citas.models import Cita, Servicio
from usuarios.models import Usuario


def _proximo_lunes() -> date:
    hoy = date.today()
    dias = (0 - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=dias)


@override_settings(PAGOS_REALES_HABILITADOS=True)
class FlujoPagoTests(APITestCase):
    """Estas pruebas son específicas del flujo con PayPal real habilitado (retorno/webhook)."""

    def setUp(self):
        self.cliente = Usuario.objects.create_user(email="cliente@example.com", password="claveSegura123")
        self.servicio = Servicio.objects.create(
            nombre="Corte de prueba", precio=Decimal("4.00"), duracion_minutos=30
        )
        self.client.force_authenticate(self.cliente)
        self.lunes = _proximo_lunes()

    def _crear_cita_pendiente(self, order_id="ORDER-1"):
        orden_falsa = {"id": order_id, "links": [{"rel": "approve", "href": "http://pay.me"}]}
        with patch("citas.views.crear_orden", return_value=orden_falsa):
            respuesta = self.client.post(reverse("cita-list"), {
                "servicio": self.servicio.id,
                "fecha": str(self.lunes),
                "hora_inicio": "10:00:00",
            })
        return respuesta.data["id"]

    def test_retorno_pago_exitoso_confirma_la_cita_y_envia_emails(self):
        cita_id = self._crear_cita_pendiente()

        with patch("pagos.views.capturar_orden", return_value={"status": "COMPLETED"}):
            respuesta = self.client.get(f"{reverse('pago_retorno')}?token=ORDER-1")

        self.assertEqual(respuesta.status_code, 200)
        cita = Cita.objects.get(pk=cita_id)
        self.assertEqual(cita.estado, Cita.ESTADO_CONFIRMADA)
        self.assertEqual(len(mail.outbox), 2)  # confirmación al cliente + aviso al dueño

    def test_webhook_confirma_aunque_el_cliente_no_vuelva_al_return_url(self):
        cita_id = self._crear_cita_pendiente()

        evento = {
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"supplementary_data": {"related_ids": {"order_id": "ORDER-1"}}},
        }
        with patch("pagos.views.verificar_webhook", return_value=True):
            respuesta = self.client.post(reverse("pago_webhook"), evento, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        cita = Cita.objects.get(pk=cita_id)
        self.assertEqual(cita.estado, Cita.ESTADO_CONFIRMADA)

    def test_webhook_con_firma_invalida_se_rechaza(self):
        self._crear_cita_pendiente()

        with patch("pagos.views.verificar_webhook", return_value=False):
            respuesta = self.client.post(reverse("pago_webhook"), {"event_type": "x"}, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_no_duplica_confirmacion_si_ya_se_confirmo_por_retorno(self):
        self._crear_cita_pendiente()

        with patch("pagos.views.capturar_orden", return_value={"status": "COMPLETED"}):
            self.client.get(f"{reverse('pago_retorno')}?token=ORDER-1")
        self.assertEqual(len(mail.outbox), 2)

        evento = {
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"supplementary_data": {"related_ids": {"order_id": "ORDER-1"}}},
        }
        with patch("pagos.views.verificar_webhook", return_value=True):
            self.client.post(reverse("pago_webhook"), evento, format="json")

        # El webhook no debería reenviar los emails de confirmación ya enviados por el retorno.
        self.assertEqual(len(mail.outbox), 2)

    def test_cita_pendiente_expirada_no_bloquea_disponibilidad(self):
        cita_id = self._crear_cita_pendiente()
        cita = Cita.objects.get(pk=cita_id)
        cita.expira_en = timezone.now() - timedelta(minutes=1)
        cita.save(update_fields=["expira_en"])

        slots = calcular_slots(
            self.lunes, 30, citas_existentes=[], ahora=timezone.now()
        )
        # (la propia vista de disponibilidad ya excluye las pendiente_pago vencidas de la
        # consulta; aquí solo confirmamos que, sin esa cita en la lista, el slot reaparece)
        from datetime import time
        self.assertIn(time(10, 0), slots)

        from datetime import time as _time

        response = self.client.get(reverse("disponibilidad"), {
            "fecha": str(self.lunes), "servicio": self.servicio.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(_time(10, 0), response.data["horarios_disponibles"])
