import logging

from django.shortcuts import get_object_or_404, render
from django.views import View
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from citas.models import Cita
from citas.notificaciones import confirmar_pago_y_notificar
from .paypal import PayPalError, capturar_orden, orden_fue_capturada, verificar_webhook

logger = logging.getLogger(__name__)


class RetornoPagoView(View):
    """PayPal redirige aquí el navegador del cliente tras aprobar el pago (?token=<order_id>)."""

    def get(self, request):
        order_id = request.GET.get("token")
        cita = get_object_or_404(Cita, paypal_order_id=order_id)

        if cita.estado != Cita.ESTADO_CONFIRMADA:
            try:
                resultado = capturar_orden(order_id)
            except PayPalError:
                logger.exception("Fallo al capturar la orden de PayPal %s", order_id)
                return render(request, "pagos/resultado.html", {
                    "icono": "⚠️", "color": "#ffb4ab", "titulo": "No pudimos confirmar tu pago",
                    "mensaje": "Por favor contáctanos para resolverlo.",
                }, status=502)

            if not orden_fue_capturada(resultado):
                return render(request, "pagos/resultado.html", {
                    "icono": "⏳", "titulo": "El pago no se completó",
                    "mensaje": "Tu horario sigue reservado por unos minutos más; podés intentar pagar de nuevo.",
                })

            confirmar_pago_y_notificar(cita)

        return render(request, "pagos/resultado.html", {
            "icono": "✅", "titulo": "¡Pago confirmado!",
            "mensaje": f"Tu cita de {cita.servicio.nombre} el {cita.fecha} a las {cita.hora_inicio} "
                       "quedó agendada. Te esperamos 10 minutos antes.",
        })


class CanceladoPagoView(View):
    def get(self, request):
        order_id = request.GET.get("token")
        cita = get_object_or_404(Cita, paypal_order_id=order_id)

        if cita.estado == Cita.ESTADO_PENDIENTE_PAGO:
            cita.estado = Cita.ESTADO_CANCELADA
            cita.save(update_fields=["estado"])

        return render(request, "pagos/resultado.html", {
            "icono": "❌", "titulo": "Reserva cancelada", "mensaje": "No se realizó ningún cobro.",
        })


class WebhookPayPalView(APIView):
    """Confirmación server-to-server, independiente de que el cliente vuelva a `return_url`."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not verificar_webhook(request.headers, request.data):
            return Response({"detail": "Firma inválida"}, status=status.HTTP_400_BAD_REQUEST)

        evento = request.data
        if evento.get("event_type") != "PAYMENT.CAPTURE.COMPLETED":
            return Response(status=status.HTTP_200_OK)

        recurso = evento.get("resource", {})
        order_id = recurso.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        if not order_id:
            return Response(status=status.HTTP_200_OK)

        try:
            cita = Cita.objects.get(paypal_order_id=order_id)
        except Cita.DoesNotExist:
            return Response(status=status.HTTP_200_OK)

        confirmar_pago_y_notificar(cita)
        return Response(status=status.HTTP_200_OK)
