from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone

from django.test import SimpleTestCase
from django.utils import timezone

from citas.disponibilidad import calcular_slots


def _proximo_dia_semana(weekday: int) -> date:
    """Próxima fecha (a partir de mañana) que caiga en `weekday` (0=lunes)."""
    hoy = date.today()
    dias_a_sumar = (weekday - hoy.weekday()) % 7
    dias_a_sumar = dias_a_sumar or 7
    return hoy + timedelta(days=dias_a_sumar)


class CalcularSlotsTests(SimpleTestCase):
    def test_martes_esta_siempre_cerrado(self):
        martes = _proximo_dia_semana(1)
        slots = calcular_slots(martes, duracion_minutos=30, citas_existentes=[])
        self.assertEqual(slots, [])

    def test_dia_habil_devuelve_slots_dentro_del_horario(self):
        lunes = _proximo_dia_semana(0)
        slots = calcular_slots(lunes, duracion_minutos=30, citas_existentes=[])

        self.assertIn(time(9, 30), slots)
        # Ningún slot debería permitir que la cita termine después del cierre (19:00).
        for inicio in slots:
            fin = (datetime.combine(lunes, inicio) + timedelta(minutes=30)).time()
            self.assertLessEqual(fin, time(19, 0))
        # Un slot que empezara a las 18:45 terminaría a las 19:15, después del cierre.
        self.assertNotIn(time(18, 45), slots)

    def test_excluye_el_almuerzo_por_completo(self):
        lunes = _proximo_dia_semana(0)
        slots = calcular_slots(lunes, duracion_minutos=30, citas_existentes=[])

        # Ningún slot de 30 min debería solaparse con 12:30-13:30, ni siquiera parcialmente.
        for inicio in slots:
            fin = (datetime.combine(lunes, inicio) + timedelta(minutes=30)).time()
            solapa_almuerzo = inicio < time(13, 30) and time(12, 30) < fin
            self.assertFalse(solapa_almuerzo, f"El slot {inicio}-{fin} se solapa con el almuerzo")

    def test_cita_existente_bloquea_su_horario_pero_libera_los_adyacentes(self):
        lunes = _proximo_dia_semana(0)
        citas_existentes = [(time(10, 0), time(10, 30))]

        slots = calcular_slots(lunes, duracion_minutos=30, citas_existentes=citas_existentes)

        self.assertNotIn(time(10, 0), slots)
        self.assertIn(time(9, 30), slots)
        self.assertIn(time(10, 30), slots)

    def test_fecha_pasada_no_tiene_slots(self):
        ayer = date.today() - timedelta(days=1)
        if ayer.weekday() == 1:  # evitar que "ayer" sea martes y de igual el mismo resultado
            ayer -= timedelta(days=1)

        slots = calcular_slots(ayer, duracion_minutos=30, citas_existentes=[])
        self.assertEqual(slots, [])

    def test_hoy_descarta_slots_ya_pasados(self):
        hoy = _proximo_dia_semana(0) if date.today().weekday() == 1 else date.today()
        if hoy.weekday() == 1:
            hoy = _proximo_dia_semana(0)
        ahora = datetime.combine(hoy, time(15, 0))

        slots = calcular_slots(hoy, duracion_minutos=30, citas_existentes=[], ahora=ahora)

        self.assertNotIn(time(9, 30), slots)
        self.assertIn(time(15, 30), slots)

    def test_duracion_mayor_reduce_la_cantidad_de_slots_disponibles(self):
        lunes = _proximo_dia_semana(0)
        slots_cortos = calcular_slots(lunes, duracion_minutos=30, citas_existentes=[])
        slots_largos = calcular_slots(lunes, duracion_minutos=90, citas_existentes=[])

        self.assertGreater(len(slots_cortos), len(slots_largos))

    def test_ahora_aware_utc_excluye_horarios_pasados_sin_romper(self):
        """Las vistas pasan `timezone.now()` (aware, en UTC), pero acá todo es hora local
        naive (America/Guayaquil). Antes del fix esto o bien tiraba TypeError (naive vs aware)
        o, según la hora del día, ni siquiera entraba a filtrar lo pasado porque la fecha en
        UTC ya era otro día — y entonces mostraba horarios de la tarde que ya habían pasado."""
        lunes = _proximo_dia_semana(0)
        ahora_local = datetime.combine(lunes, time(14, 0))  # 2:00 PM hora local
        ahora_aware = timezone.make_aware(ahora_local)

        slots = calcular_slots(lunes, duracion_minutos=40, citas_existentes=[], ahora=ahora_aware)

        self.assertNotIn(time(9, 30), slots)  # ya pasó
        self.assertIn(time(14, 10), slots)  # todavía no llega

    def test_ahora_aware_con_corrimiento_de_fecha_en_utc(self):
        lunes = _proximo_dia_semana(0)
        # 8:00 PM hora local (UTC-5) cae ya en la madrugada del día siguiente en UTC.
        ahora_local = datetime.combine(lunes, time(20, 0))
        ahora_aware = timezone.make_aware(ahora_local).astimezone(dt_timezone.utc)
        self.assertNotEqual(ahora_aware.date(), lunes)  # confirma que sí hay corrimiento

        slots = calcular_slots(lunes, duracion_minutos=40, citas_existentes=[], ahora=ahora_aware)

        self.assertEqual(slots, [])  # a las 8pm el local ya cerró (19:00)

    def test_los_horarios_se_espacian_segun_la_duracion_no_cada_15_min(self):
        """Antes el paso entre turnos era fijo (15 min) sin importar cuánto durara el corte,
        lo que hacía parecer que un corte de 40 min se podía agendar cada 15 min. Ahora el
        paso entre turnos ofrecidos es la propia duración del servicio."""
        lunes = _proximo_dia_semana(0)
        slots = calcular_slots(lunes, duracion_minutos=40, citas_existentes=[])

        self.assertIn(time(9, 30), slots)
        self.assertNotIn(time(9, 45), slots)
        self.assertNotIn(time(10, 0), slots)
        self.assertIn(time(10, 10), slots)  # 9:30 + 40 min
