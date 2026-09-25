from django.urls import path

from .views import CanceladoPagoView, RetornoPagoView, WebhookPayPalView

# Vistas de redirección del navegador (las visita PayPal, no un cliente de la API).
urlpatterns_redirect = [
    path("retorno/", RetornoPagoView.as_view(), name="pago_retorno"),
    path("cancelado/", CanceladoPagoView.as_view(), name="pago_cancelado"),
]

# Endpoint de API para el webhook server-to-server.
urlpatterns_api = [
    path("webhook/", WebhookPayPalView.as_view(), name="pago_webhook"),
]
