"""Cálculo de horarios disponibles.

`calcular_slots` es una función pura (sin acceso a la base de datos): recibe la lista de citas
ya existentes para la fecha y devuelve los horarios de inicio válidos. Esto permite testear toda
la lógica de negocio (martes cerrado, almuerzo, solapamientos, etc.) sin tocar el ORM.
"""
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from core.utils import ALMUERZO_FIN, ALMUERZO_INICIO, DIA_CERRADO, HORA_APERTURA, HORA_CIERRE


def _a_datetime(fecha: date, hora: time) -> datetime:
    return datetime.combine(fecha, hora)


def _se_solapan(inicio_a: datetime, fin_a: datetime, inicio_b: datetime, fin_b: datetime) -> bool:
    return inicio_a < fin_b and inicio_b < fin_a


def calcular_slots(
    fecha: date,
    duracion_minutos: int,
    citas_existentes: list[tuple[time, time]],
    ahora: datetime | None = None,
) -> list[time]:
    """Devuelve los horarios de inicio disponibles para `fecha` dada una duración total.

    `citas_existentes` es una lista de tuplas (hora_inicio, hora_fin) de citas que ya ocupan
    horario ese día (normalmente `pendiente_pago` no vencidas, `confirmada` o `completada`).
    """
    if fecha.weekday() == DIA_CERRADO:
        return []

    if ahora is None:
        ahora = datetime.now()
    elif timezone.is_aware(ahora):
        # `timezone.now()` (lo que pasan las vistas) viene en UTC; acá todo lo demás es hora
        # local naive (America/Guayaquil), así que hay que convertir antes de comparar — si no,
        # en ciertos horarios del día "ahora.date()" cae en el día siguiente (UTC ya cambió de
        # fecha aunque localmente siga siendo hoy) y el filtro de "ya pasó" se salta entero.
        ahora = timezone.localtime(ahora).replace(tzinfo=None)

    if fecha < ahora.date():
        return []

    duracion = timedelta(minutes=duracion_minutos)
    almuerzo_inicio_dt = _a_datetime(fecha, ALMUERZO_INICIO)
    almuerzo_fin_dt = _a_datetime(fecha, ALMUERZO_FIN)
    cierre_dt = _a_datetime(fecha, HORA_CIERRE)

    ocupados = [
        (_a_datetime(fecha, inicio), _a_datetime(fecha, fin))
        for inicio, fin in citas_existentes
    ]

    slots = []
    candidato = _a_datetime(fecha, HORA_APERTURA)
    # El paso entre turnos ofrecidos es la propia duración del servicio (+extras): así se
    # ofrecen bloques consecutivos de verdad (ej. cada 40 min) en vez de cada 15 min fijos,
    # que hacía parecer que el corte dura 15 minutos cuando en realidad ocupa mucho más.
    paso = duracion

    while candidato + duracion <= cierre_dt:
        fin_candidato = candidato + duracion

        if fecha == ahora.date() and candidato <= ahora:
            candidato += paso
            continue

        if _se_solapan(candidato, fin_candidato, almuerzo_inicio_dt, almuerzo_fin_dt):
            candidato += paso
            continue

        if any(_se_solapan(candidato, fin_candidato, oc_inicio, oc_fin) for oc_inicio, oc_fin in ocupados):
            candidato += paso
            continue

        slots.append(candidato.time())
        candidato += paso

    return slots
