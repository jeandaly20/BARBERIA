"""Envío de correos relacionados a citas. Todo pasa por aquí (nunca se arma el cuerpo de un
email directamente en una vista o management command) para que los tests puedan verificar
`django.core.mail.outbox` de forma consistente."""
from django.conf import settings
from django.core.mail import send_mail


def enviar_email_confirmacion_cliente(cita):
    send_mail(
        subject="Tu cita en la barbería fue confirmada",
        message=(
            f"Hola {cita.cliente.nombre or cita.cliente.email},\n\n"
            f"Tu cita para {cita.servicio.nombre} el {cita.fecha} a las {cita.hora_inicio} "
            "quedó confirmada. Te esperamos 10 minutos antes; si no llegas dentro de los "
            "primeros 15 minutos, pierdes el turno y el depósito pagado.\n\n"
            "¡Nos vemos pronto!"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cita.cliente.email],
        fail_silently=True,
    )


def enviar_email_nueva_cita_propietario(cita):
    send_mail(
        subject="Nueva cita agendada",
        message=(
            f"Jean, {cita.cliente.nombre or cita.cliente.email} agendó una cita para "
            f"{cita.servicio.nombre} el {cita.fecha} a las {cita.hora_inicio}."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.OWNER_NOTIFICATION_EMAIL],
        fail_silently=True,
    )


def enviar_email_recordatorio(cita):
    send_mail(
        subject="Recordatorio de tu cita hoy",
        message=(
            f"Hola {cita.cliente.nombre or cita.cliente.email}, tu cita de "
            f"{cita.servicio.nombre} es hoy a las {cita.hora_inicio}. Llega 10 minutos antes; "
            "la tolerancia máxima es de 15 minutos o se pierde el turno."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cita.cliente.email],
        fail_silently=True,
    )


def confirmar_pago_y_notificar(cita) -> bool:
    """Marca la cita como confirmada si todavía no lo estaba y envía los emails de
    confirmación/aviso. Devuelve True si la confirmó en esta llamada — se usa tanto para el
    pago real de PayPal (retorno del navegador y webhook pueden llegar los dos, en cualquier
    orden) como para el modo simulado, así nunca se duplican los emails."""
    from .models import Cita

    if cita.estado == Cita.ESTADO_CONFIRMADA:
        return False

    cita.estado = Cita.ESTADO_CONFIRMADA
    cita.save(update_fields=["estado"])
    enviar_email_confirmacion_cliente(cita)
    enviar_email_nueva_cita_propietario(cita)
    return True


def enviar_email_resumen_diario(citas_de_hoy):
    if not citas_de_hoy:
        cuerpo = "Jean, hoy no tienes citas agendadas."
    else:
        lineas = [
            f"- {c.hora_inicio} · {c.cliente.nombre or c.cliente.email} · {c.servicio.nombre}"
            for c in citas_de_hoy
        ]
        cuerpo = f"Jean, hoy tienes {len(citas_de_hoy)} cita(s):\n\n" + "\n".join(lineas)

    send_mail(
        subject="Resumen de citas de hoy",
        message=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.OWNER_NOTIFICATION_EMAIL],
        fail_silently=True,
    )
