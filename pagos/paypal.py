"""Cliente REST de PayPal (Orders API v2). Se usa `requests` directamente en vez de un SDK
oficial porque los SDKs de PayPal para Python (paypalrestsdk, checkout-server-sdk) están
deprecados. Todas las funciones son fácilmente mockeables en tests (`unittest.mock.patch`)."""
from django.conf import settings

import requests


class PayPalError(Exception):
    """Se lanza cuando PayPal responde con un error inesperado."""


def obtener_token() -> str:
    respuesta = requests.post(
        f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    if respuesta.status_code != 200:
        raise PayPalError(f"No se pudo obtener el token de PayPal: {respuesta.text}")
    return respuesta.json()["access_token"]


def crear_orden(monto, cita_id: int) -> dict:
    """Crea una orden en PayPal y devuelve su JSON (incluye 'id' y el link 'approve')."""
    token = obtener_token()
    return_url = f"{settings.SITE_URL}/pagos/retorno/"
    cancel_url = f"{settings.SITE_URL}/pagos/cancelado/"

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "custom_id": str(cita_id),
            "amount": {"currency_code": "USD", "value": f"{monto:.2f}"},
        }],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
        },
    }

    respuesta = requests.post(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    if respuesta.status_code not in (200, 201):
        raise PayPalError(f"No se pudo crear la orden en PayPal: {respuesta.text}")
    return respuesta.json()


def link_aprobacion(orden: dict) -> str | None:
    for link in orden.get("links", []):
        if link.get("rel") == "approve":
            return link.get("href")
    return None


def capturar_orden(order_id: str) -> dict:
    token = obtener_token()
    respuesta = requests.post(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )
    if respuesta.status_code not in (200, 201):
        raise PayPalError(f"No se pudo capturar la orden {order_id}: {respuesta.text}")
    return respuesta.json()


def orden_fue_capturada(respuesta_captura: dict) -> bool:
    return respuesta_captura.get("status") == "COMPLETED"


def verificar_webhook(headers: dict, body: dict) -> bool:
    """Verifica la firma del webhook contra la API de PayPal (evita procesar eventos falsos)."""
    token = obtener_token()
    payload = {
        "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
        "cert_url": headers.get("PAYPAL-CERT-URL"),
        "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
        "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
        "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
        "webhook_id": settings.PAYPAL_WEBHOOK_ID,
        "webhook_event": body,
    }
    respuesta = requests.post(
        f"{settings.PAYPAL_API_BASE}/v1/notifications/verify-webhook-signature",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    if respuesta.status_code != 200:
        return False
    return respuesta.json().get("verification_status") == "SUCCESS"
