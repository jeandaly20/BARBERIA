from django.conf import settings
from django.core.mail import send_mail


def enviar_email_codigo_recuperacion(email, codigo):
    send_mail(
        subject="Código de recuperación — Jean Barber Atelier",
        message=(
            f"Tu código para restablecer tu contraseña es: {codigo}\n\n"
            "Vence en 10 minutos. Si no lo pediste vos, podés ignorar este correo."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )
