"""Constantes de negocio compartidas por la app `citas` (y sus tests)."""
from datetime import time

DIA_CERRADO = 1  # date.weekday(): lunes=0 ... martes=1 (la barbería descansa los martes)

HORA_APERTURA = time(9, 30)
HORA_CIERRE = time(19, 0)

ALMUERZO_INICIO = time(12, 30)
ALMUERZO_FIN = time(13, 30)

INTERVALO_SLOT_MINUTOS = 15

TARIFA_RESERVA = 1  # dólares que se suman al total por agendar online

GRACIA_NO_SHOW_MINUTOS = 15
RECORDATORIO_MINUTOS_ANTES = 10

# Ventana para completar el pago en PayPal antes de que la cita se libere automáticamente.
MINUTOS_EXPIRACION_PAGO = 15
