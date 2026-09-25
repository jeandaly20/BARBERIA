"""Cálculo de precios/depósito. Función pura: no toca la base de datos, solo usa los objetos
Servicio/Extra ya cargados (o cualquier objeto con los atributos `precio`/`duracion_minutos`)."""
from decimal import ROUND_HALF_UP, Decimal

from core.utils import TARIFA_RESERVA


def calcular_totales(servicio, extras=()):
    duracion_minutos = servicio.duracion_minutos + sum(e.duracion_minutos for e in extras)
    subtotal = servicio.precio + sum((e.precio for e in extras), Decimal("0"))
    tarifa_reserva = Decimal(TARIFA_RESERVA)
    total = subtotal + tarifa_reserva
    deposito = (total / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "duracion_minutos": duracion_minutos,
        "subtotal": subtotal,
        "tarifa_reserva": tarifa_reserva,
        "total": total,
        "deposito": deposito,
    }


def monto_a_pagar_online(servicio, extras, tipo_pago):
    totales = calcular_totales(servicio, extras)
    if tipo_pago == "completo":
        return totales["total"]
    return totales["deposito"]
