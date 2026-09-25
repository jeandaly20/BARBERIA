from datetime import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import EsClienteDuenoOPropietario, EsPropietario
from pagos.paypal import PayPalError, crear_orden, link_aprobacion
from .disponibilidad import calcular_slots
from .models import Cita, Extra, Servicio
from .notificaciones import confirmar_pago_y_notificar
from .pricing import calcular_totales
from .serializers import CitaSerializer, ExtraSerializer, ServicioSerializer


class ServicioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Servicio.objects.filter(activo=True)
    serializer_class = ServicioSerializer
    permission_classes = [permissions.AllowAny]


class ExtraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Extra.objects.filter(activo=True)
    serializer_class = ExtraSerializer
    permission_classes = [permissions.AllowAny]


class DisponibilidadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        fecha_str = request.query_params.get("fecha")
        servicio_id = request.query_params.get("servicio")
        if not fecha_str or not servicio_id:
            raise serializers.ValidationError("Se requieren los parámetros 'fecha' y 'servicio'.")

        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            raise serializers.ValidationError("El parámetro 'fecha' debe tener el formato YYYY-MM-DD.")

        try:
            servicio = Servicio.objects.get(pk=servicio_id, activo=True)
        except Servicio.DoesNotExist:
            raise serializers.ValidationError("Servicio no encontrado.")

        extra_ids = [e for e in request.query_params.get("extras", "").split(",") if e]
        extras = list(Extra.objects.filter(pk__in=extra_ids, activo=True))

        totales = calcular_totales(servicio, extras)
        citas_existentes = Cita.objects.filter(
            fecha=fecha, estado__in=Cita.ESTADOS_QUE_BLOQUEAN_HORARIO
        ).exclude(estado=Cita.ESTADO_PENDIENTE_PAGO, expira_en__lt=timezone.now())
        ocupados = [(c.hora_inicio, c.hora_fin) for c in citas_existentes]

        slots = calcular_slots(fecha, totales["duracion_minutos"], ocupados, ahora=timezone.now())

        return Response({
            "fecha": fecha,
            "duracion_minutos": totales["duracion_minutos"],
            "horarios_disponibles": slots,
        })


class CitaViewSet(viewsets.ModelViewSet):
    serializer_class = CitaSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Cita.objects.none()
        user = self.request.user
        if user.rol == user.ROL_PROPIETARIO:
            return Cita.objects.all()
        return Cita.objects.filter(cliente=user)

    def get_permissions(self):
        if self.action in ["semana", "marcar_completada", "marcar_no_show", "confirmar_saldo"]:
            return [permissions.IsAuthenticated(), EsPropietario()]
        if self.action in ["retrieve", "cancelar"]:
            return [permissions.IsAuthenticated(), EsClienteDuenoOPropietario()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cita = serializer.save()

        if not settings.PAGOS_REALES_HABILITADOS:
            # El negocio todavía no está cobrando de verdad (PAGOS_REALES_HABILITADOS=False):
            # se confirma la cita al instante y se avisa por email, sin pasar por PayPal.
            cita.expira_en = None
            cita.save(update_fields=["expira_en"])
            confirmar_pago_y_notificar(cita)

            data = dict(self.get_serializer(cita).data)
            data["link_pago"] = None
            headers = self.get_success_headers(serializer.data)
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

        try:
            orden = crear_orden(cita.monto_a_pagar_online, cita.id)
        except PayPalError:
            cita.delete()
            raise serializers.ValidationError(
                "No se pudo iniciar el pago con PayPal. Intenta de nuevo en unos minutos."
            )

        cita.paypal_order_id = orden["id"]
        cita.save(update_fields=["paypal_order_id"])

        data = dict(serializer.data)
        data["link_pago"] = link_aprobacion(orden)
        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=["get"])
    def mias(self, request):
        citas = Cita.objects.filter(cliente=request.user)
        return Response(self.get_serializer(citas, many=True).data)

    @action(detail=False, methods=["get"])
    def semana(self, request):
        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        if not desde or not hasta:
            raise serializers.ValidationError("Se requieren los parámetros 'desde' y 'hasta'.")

        citas = Cita.objects.filter(fecha__gte=desde, fecha__lte=hasta).exclude(
            estado=Cita.ESTADO_CANCELADA
        )
        return Response(self.get_serializer(citas, many=True).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        cita = self.get_object()
        cita.estado = Cita.ESTADO_CANCELADA
        cita.save(update_fields=["estado"])
        return Response(self.get_serializer(cita).data)

    @action(detail=True, methods=["post"], url_path="marcar-completada")
    def marcar_completada(self, request, pk=None):
        cita = self.get_object()
        cita.estado = Cita.ESTADO_COMPLETADA
        cita.save(update_fields=["estado"])
        return Response(self.get_serializer(cita).data)

    @action(detail=True, methods=["post"], url_path="marcar-no-show")
    def marcar_no_show(self, request, pk=None):
        cita = self.get_object()
        cita.estado = Cita.ESTADO_NO_SHOW
        cita.deposito_perdido = True
        cita.save(update_fields=["estado", "deposito_perdido"])
        return Response(self.get_serializer(cita).data)

    @action(detail=True, methods=["post"], url_path="confirmar-saldo")
    def confirmar_saldo(self, request, pk=None):
        cita = self.get_object()
        cita.saldo_pagado_en_persona = True
        cita.save(update_fields=["saldo_pagado_en_persona"])
        return Response(self.get_serializer(cita).data)
