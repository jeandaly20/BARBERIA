from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from pagos.paypal import PayPalError, capturar_orden, crear_orden, link_aprobacion, verificar_webhook


def _respuesta(status_code, json_data):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


@override_settings(
    PAYPAL_API_BASE="https://api-m.sandbox.paypal.com",
    PAYPAL_CLIENT_ID="id-de-prueba",
    PAYPAL_CLIENT_SECRET="secreto-de-prueba",
    PAYPAL_WEBHOOK_ID="webhook-de-prueba",
    SITE_URL="http://testserver",
)
class PayPalClientTests(SimpleTestCase):
    @patch("pagos.paypal.requests.post")
    def test_crear_orden_arma_el_payload_correcto_y_devuelve_json(self, mock_post):
        mock_post.side_effect = [
            _respuesta(200, {"access_token": "token-falso"}),
            _respuesta(201, {"id": "ORDER-1", "links": [{"rel": "approve", "href": "http://pay.me"}]}),
        ]

        orden = crear_orden(2.5, cita_id=42)

        self.assertEqual(orden["id"], "ORDER-1")
        segunda_llamada = mock_post.call_args_list[1]
        payload = segunda_llamada.kwargs["json"]
        self.assertEqual(payload["purchase_units"][0]["amount"]["value"], "2.50")
        self.assertEqual(payload["purchase_units"][0]["custom_id"], "42")
        self.assertEqual(link_aprobacion(orden), "http://pay.me")

    @patch("pagos.paypal.requests.post")
    def test_crear_orden_lanza_error_si_paypal_responde_mal(self, mock_post):
        mock_post.side_effect = [
            _respuesta(200, {"access_token": "token-falso"}),
            _respuesta(500, {"error": "boom"}),
        ]

        with self.assertRaises(PayPalError):
            crear_orden(2.5, cita_id=42)

    @patch("pagos.paypal.requests.post")
    def test_capturar_orden(self, mock_post):
        mock_post.side_effect = [
            _respuesta(200, {"access_token": "token-falso"}),
            _respuesta(201, {"status": "COMPLETED"}),
        ]

        resultado = capturar_orden("ORDER-1")

        self.assertEqual(resultado["status"], "COMPLETED")

    @patch("pagos.paypal.requests.post")
    def test_verificar_webhook_exitoso(self, mock_post):
        mock_post.side_effect = [
            _respuesta(200, {"access_token": "token-falso"}),
            _respuesta(200, {"verification_status": "SUCCESS"}),
        ]

        self.assertTrue(verificar_webhook({}, {"event_type": "PAYMENT.CAPTURE.COMPLETED"}))

    @patch("pagos.paypal.requests.post")
    def test_verificar_webhook_firma_invalida(self, mock_post):
        mock_post.side_effect = [
            _respuesta(200, {"access_token": "token-falso"}),
            _respuesta(200, {"verification_status": "FAILURE"}),
        ]

        self.assertFalse(verificar_webhook({}, {"event_type": "PAYMENT.CAPTURE.COMPLETED"}))
