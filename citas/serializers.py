from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from core.utils import MINUTOS_EXPIRACION_PAGO
from .disponibilidad import calcular_slots
from .models import Cita, Extra, Servicio
from .pricing import calcular_totales


class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ["id", "nombre", "precio", "duracion_minutos", "precio_desde"]


class ExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Extra
        fields = ["id", "nombre", "precio", "duracion_minutos"]


class CitaSerializer(serializers.ModelSerializer):
    extras = serializers.PrimaryKeyRelatedField(
        queryset=Extra.objects.filter(activo=True), many=True, required=False
    )

    class Meta:
        model = Cita
        fields = [
            "id", "servicio", "extras", "fecha", "hora_inicio", "tipo_pago",
            "hora_fin", "precio_total", "monto_a_pagar_online", "estado",
            "saldo_pagado_en_persona", "creado_en",
        ]
        read_only_fields = [
            "id", "hora_fin", "precio_total", "monto_a_pagar_online", "estado",
            "saldo_pagado_en_persona", "creado_en",
        ]

    def validate_servicio(self, servicio):
        if not servicio.activo:
            raise serializers.ValidationError("Este servicio ya no está disponible.")
        return servicio

    def validate(self, data):
        servicio = data["servicio"]
        extras = data.get("extras", [])
        fecha = data["fecha"]
        hora_inicio = data["hora_inicio"]

        totales = calcular_totales(servicio, extras)

        citas_existentes = Cita.objects.filter(
            fecha=fecha, estado__in=Cita.ESTADOS_QUE_BLOQUEAN_HORARIO
        )
        instance = getattr(self, "instance", None)
        if instance is not None:
            citas_existentes = citas_existentes.exclude(pk=instance.pk)
        citas_existentes = citas_existentes.exclude(
            estado=Cita.ESTADO_PENDIENTE_PAGO, expira_en__lt=timezone.now()
        )
        ocupados = [(c.hora_inicio, c.hora_fin) for c in citas_existentes]

        slots_disponibles = calcular_slots(
            fecha, totales["duracion_minutos"], ocupados, ahora=timezone.now()
        )
        if hora_inicio not in slots_disponibles:
            raise serializers.ValidationError(
                "Ese horario ya no está disponible para el servicio elegido."
            )

        data["_totales"] = totales
        return data

    def create(self, validated_data):
        extras = validated_data.pop("extras", [])
        totales = validated_data.pop("_totales")
        tipo_pago = validated_data.get("tipo_pago", Cita.TIPO_PAGO_DEPOSITO)
        monto_online = totales["total"] if tipo_pago == Cita.TIPO_PAGO_COMPLETO else totales["deposito"]

        hora_fin = (
            datetime.combine(validated_data["fecha"], validated_data["hora_inicio"])
            + timedelta(minutes=totales["duracion_minutos"])
        ).time()

        cita = Cita.objects.create(
            cliente=self.context["request"].user,
            hora_fin=hora_fin,
            duracion_total_minutos=totales["duracion_minutos"],
            subtotal=totales["subtotal"],
            tarifa_reserva=totales["tarifa_reserva"],
            precio_total=totales["total"],
            monto_a_pagar_online=monto_online,
            expira_en=timezone.now() + timedelta(minutes=MINUTOS_EXPIRACION_PAGO),
            **validated_data,
        )
        cita.extras.set(extras)
        return cita
