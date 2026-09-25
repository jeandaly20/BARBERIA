from datetime import date, datetime, time, timedelta

from django.test import SimpleTestCase

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
