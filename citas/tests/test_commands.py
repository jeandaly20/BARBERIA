from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from citas.models import Cita, Servicio
from usuarios.models import Usuario


class ComandosTestsBase(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user(email="cliente@example.com", password="claveSegura123")
        self.servicio = Servicio.objects.create(
            nombre="Corte de prueba", precio=Decimal("4.00"), duracion_minutos=30
        )

    def _crear_cita(self, **overrides):
        ahora = timezone.localtime(timezone.now())
        defaults = dict(
            cliente=self.cliente,
            servicio=self.servicio,
            fecha=ahora.date(),
            hora_inicio=(ahora + timedelta(minutes=5)).time(),
            hora_fin=(ahora + timedelta(minutes=35)).time(),
            duracion_total_minutos=30,
            subtotal=Decimal("4.00"),
            tarifa_reserva=Decimal("1.00"),
            precio_total=Decimal("5.00"),
            monto_a_pagar_online=Decimal("2.50"),
            estado=Cita.ESTADO_CONFIRMADA,
        )
        defaults.update(overrides)
        return Cita.objects.create(**defaults)


class LiberarCitasExpiradasTests(ComandosTestsBase):
    def test_libera_solo_las_pendientes_vencidas(self):
        vencida = self._crear_cita(
            estado=Cita.ESTADO_PENDIENTE_PAGO, expira_en=timezone.now() - timedelta(minutes=1)
        )
        vigente = self._crear_cita(
            estado=Cita.ESTADO_PENDIENTE_PAGO,
            hora_inicio=(timezone.localtime() + timedelta(hours=1)).time(),
            expira_en=timezone.now() + timedelta(minutes=10),
        )
        confirmada = self._crear_cita(
            estado=Cita.ESTADO_CONFIRMADA,
            hora_inicio=(timezone.localtime() + timedelta(hours=2)).time(),
        )

        call_command("liberar_citas_expiradas", stdout=StringIO())

        vencida.refresh_from_db()
        vigente.refresh_from_db()
        confirmada.refresh_from_db()
        self.assertEqual(vencida.estado, Cita.ESTADO_EXPIRADA)
        self.assertEqual(vigente.estado, Cita.ESTADO_PENDIENTE_PAGO)
        self.assertEqual(confirmada.estado, Cita.ESTADO_CONFIRMADA)


class EnviarRecordatoriosTests(ComandosTestsBase):
    def test_envia_recordatorio_a_cita_proxima_y_no_lo_duplica(self):
        self._crear_cita()

        call_command("enviar_recordatorios", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)

        call_command("enviar_recordatorios", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)

    def test_no_envia_a_cita_lejana(self):
        self._crear_cita(hora_inicio=(timezone.localtime() + timedelta(hours=5)).time())

        call_command("enviar_recordatorios", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 0)


class ResumenDiarioTests(ComandosTestsBase):
    def test_resumen_incluye_conteo_de_citas_de_hoy(self):
        self._crear_cita()
        self._crear_cita(hora_inicio=(timezone.localtime() + timedelta(hours=1)).time())

        call_command("resumen_diario_propietario", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("2 cita", mail.outbox[0].body)
