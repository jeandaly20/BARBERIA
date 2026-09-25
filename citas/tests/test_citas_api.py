from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from citas.models import Cita, Extra, Servicio
from usuarios.models import Usuario

def _orden_paypal_falsa(monto, cita_id):
    return {
        "id": f"FAKE-ORDER-{cita_id}",
        "links": [{"rel": "approve", "href": "https://www.sandbox.paypal.com/checkoutnow?token=FAKE"}],
    }


def _proximo_dia_semana(weekday: int) -> date:
    hoy = date.today()
    dias_a_sumar = (weekday - hoy.weekday()) % 7
    dias_a_sumar = dias_a_sumar or 7
    return hoy + timedelta(days=dias_a_sumar)


@override_settings(PAGOS_REALES_HABILITADOS=True)
class CitaApiTestsBase(APITestCase):
    """Estas pruebas cubren el flujo con PayPal real habilitado. Ver test_pagos_simulados.py
    para el comportamiento por defecto (PAGOS_REALES_HABILITADOS=False)."""

    def setUp(self):
        self.cliente = Usuario.objects.create_user(email="cliente@example.com", password="claveSegura123")
        self.servicio = Servicio.objects.create(
            nombre="Corte de prueba", precio=Decimal("4.00"), duracion_minutos=30
        )
        self.client.force_authenticate(self.cliente)
        self.lunes = _proximo_dia_semana(0)

        parche_paypal = patch("citas.views.crear_orden", side_effect=_orden_paypal_falsa)
        self.mock_crear_orden = parche_paypal.start()
        self.addCleanup(parche_paypal.stop)

    def _crear_cita(self, **overrides):
        data = {
            "servicio": self.servicio.id,
            "fecha": str(self.lunes),
            "hora_inicio": "10:00:00",
            "tipo_pago": Cita.TIPO_PAGO_DEPOSITO,
        }
        data.update(overrides)
        return self.client.post(reverse("cita-list"), data)


class CrearCitaTests(CitaApiTestsBase):
    def test_crear_cita_calcula_precio_y_deposito(self):
        response = self._crear_cita()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["precio_total"], "5.00")
        self.assertEqual(response.data["monto_a_pagar_online"], "2.50")
        self.assertEqual(response.data["estado"], Cita.ESTADO_PENDIENTE_PAGO)
        self.assertEqual(
            response.data["link_pago"], "https://www.sandbox.paypal.com/checkoutnow?token=FAKE"
        )
        self.mock_crear_orden.assert_called_once()

        cita = Cita.objects.get(pk=response.data["id"])
        self.assertEqual(cita.paypal_order_id, f"FAKE-ORDER-{cita.id}")

    def test_si_paypal_falla_no_deja_cita_huerfana(self):
        from pagos.paypal import PayPalError

        self.mock_crear_orden.side_effect = PayPalError("boom")

        response = self._crear_cita()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Cita.objects.count(), 0)

    def test_rechaza_solapamiento(self):
        primera = self._crear_cita()
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)

        segunda = self._crear_cita(hora_inicio="10:15:00")
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_martes(self):
        martes = _proximo_dia_semana(1)
        response = self._crear_cita(fecha=str(martes))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_fecha_pasada(self):
        ayer = date.today() - timedelta(days=1)
        response = self._crear_cita(fecha=str(ayer))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_horario_de_almuerzo(self):
        response = self._crear_cita(hora_inicio="12:45:00")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelar_libera_el_slot(self):
        creada = self._crear_cita()
        cita_id = creada.data["id"]

        cancelar_url = reverse("cita-cancelar", kwargs={"pk": cita_id})
        respuesta_cancelar = self.client.post(cancelar_url)
        self.assertEqual(respuesta_cancelar.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta_cancelar.data["estado"], Cita.ESTADO_CANCELADA)

        otra = self._crear_cita()
        self.assertEqual(otra.status_code, status.HTTP_201_CREATED)

    def test_mias_solo_devuelve_las_del_cliente_autenticado(self):
        self._crear_cita()
        otro_cliente = Usuario.objects.create_user(email="otro@example.com", password="claveSegura123")
        self.client.force_authenticate(otro_cliente)

        response = self.client.get(reverse("cita-mias"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class GestionCitaPropietarioTests(CitaApiTestsBase):
    def setUp(self):
        super().setUp()
        self.propietario = Usuario.objects.create_user(
            email="dueno@example.com", password="claveSegura123", rol=Usuario.ROL_PROPIETARIO
        )
        respuesta = self._crear_cita()
        self.cita_id = respuesta.data["id"]
        self.client.force_authenticate(self.propietario)

    def test_marcar_no_show_marca_deposito_perdido(self):
        url = reverse("cita-marcar-no-show", kwargs={"pk": self.cita_id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cita = Cita.objects.get(pk=self.cita_id)
        self.assertEqual(cita.estado, Cita.ESTADO_NO_SHOW)
        self.assertTrue(cita.deposito_perdido)

    def test_confirmar_saldo(self):
        url = reverse("cita-confirmar-saldo", kwargs={"pk": self.cita_id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cita = Cita.objects.get(pk=self.cita_id)
        self.assertTrue(cita.saldo_pagado_en_persona)
