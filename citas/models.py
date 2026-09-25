from django.conf import settings
from django.db import models


class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=6, decimal_places=2)
    duracion_minutos = models.PositiveIntegerField()
    precio_desde = models.BooleanField(
        default=False, help_text="Marca el precio como 'desde $X' (ej. Corte fade desde $4.00)."
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Extra(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=6, decimal_places=2)
    duracion_minutos = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    TIPO_PAGO_DEPOSITO = "deposito"
    TIPO_PAGO_COMPLETO = "completo"
    TIPO_PAGO_CHOICES = [
        (TIPO_PAGO_DEPOSITO, "Depósito"),
        (TIPO_PAGO_COMPLETO, "Pago completo"),
    ]

    ESTADO_PENDIENTE_PAGO = "pendiente_pago"
    ESTADO_CONFIRMADA = "confirmada"
    ESTADO_COMPLETADA = "completada"
    ESTADO_CANCELADA = "cancelada"
    ESTADO_NO_SHOW = "no_show"
    ESTADO_EXPIRADA = "expirada"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE_PAGO, "Pendiente de pago"),
        (ESTADO_CONFIRMADA, "Confirmada"),
        (ESTADO_COMPLETADA, "Completada"),
        (ESTADO_CANCELADA, "Cancelada"),
        (ESTADO_NO_SHOW, "No se presentó"),
        (ESTADO_EXPIRADA, "Expirada"),
    ]

    # Estados que efectivamente ocupan un horario (usados por disponibilidad.py).
    ESTADOS_QUE_BLOQUEAN_HORARIO = [ESTADO_PENDIENTE_PAGO, ESTADO_CONFIRMADA, ESTADO_COMPLETADA]

    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="citas")
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="citas")
    extras = models.ManyToManyField(Extra, blank=True, related_name="citas")

    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_total_minutos = models.PositiveIntegerField()

    subtotal = models.DecimalField(max_digits=6, decimal_places=2)
    tarifa_reserva = models.DecimalField(max_digits=6, decimal_places=2)
    precio_total = models.DecimalField(max_digits=6, decimal_places=2)

    tipo_pago = models.CharField(max_length=10, choices=TIPO_PAGO_CHOICES, default=TIPO_PAGO_DEPOSITO)
    monto_a_pagar_online = models.DecimalField(max_digits=6, decimal_places=2)
    saldo_pagado_en_persona = models.BooleanField(default=False)

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE_PAGO)
    deposito_perdido = models.BooleanField(default=False)
    recordatorio_enviado = models.BooleanField(default=False)

    paypal_order_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    expira_en = models.DateTimeField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["fecha", "hora_inicio"])]
        ordering = ["fecha", "hora_inicio"]

    def __str__(self):
        return f"{self.cliente} - {self.servicio} - {self.fecha} {self.hora_inicio}"
