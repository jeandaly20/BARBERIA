from decimal import Decimal

from django.test import TestCase

from citas.models import Extra, Servicio
from citas.pricing import calcular_totales, monto_a_pagar_online


class CalcularTotalesTests(TestCase):
    def setUp(self):
        self.servicio = Servicio.objects.create(
            nombre="Corte fade", precio=Decimal("4.00"), duracion_minutos=40
        )

    def test_deposito_es_la_mitad_del_total_con_tarifa_de_reserva(self):
        totales = calcular_totales(self.servicio, extras=[])

        self.assertEqual(totales["subtotal"], Decimal("4.00"))
        self.assertEqual(totales["total"], Decimal("5.00"))
        self.assertEqual(totales["deposito"], Decimal("2.50"))
        self.assertEqual(totales["duracion_minutos"], 40)

    def test_extras_suman_precio_y_duracion(self):
        barba = Extra.objects.create(nombre="Barba", precio=Decimal("2.50"), duracion_minutos=20)

        totales = calcular_totales(self.servicio, extras=[barba])

        self.assertEqual(totales["subtotal"], Decimal("6.50"))
        self.assertEqual(totales["total"], Decimal("7.50"))
        self.assertEqual(totales["deposito"], Decimal("3.75"))
        self.assertEqual(totales["duracion_minutos"], 60)

    def test_monto_a_pagar_online_completo_vs_deposito(self):
        self.assertEqual(monto_a_pagar_online(self.servicio, [], "completo"), Decimal("5.00"))
        self.assertEqual(monto_a_pagar_online(self.servicio, [], "deposito"), Decimal("2.50"))
