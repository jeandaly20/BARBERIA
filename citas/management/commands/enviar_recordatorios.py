from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from citas.models import Cita
from citas.notificaciones import enviar_email_recordatorio
from core.utils import RECORDATORIO_MINUTOS_ANTES


class Command(BaseCommand):
    help = (
        "Envía un recordatorio por email a los clientes cuya cita empieza dentro de los "
        "próximos minutos. Pensado para correr cada 5-10 min (Render Cron Job)."
    )

    def handle(self, *args, **options):
        ahora = timezone.localtime(timezone.now())
        hoy = ahora.date()
        limite = ahora + timedelta(minutes=RECORDATORIO_MINUTOS_ANTES)

        candidatas = Cita.objects.filter(
            fecha=hoy,
            estado=Cita.ESTADO_CONFIRMADA,
            recordatorio_enviado=False,
        )

        enviados = 0
        for cita in candidatas:
            inicio = timezone.make_aware(datetime.combine(cita.fecha, cita.hora_inicio))
            if ahora <= inicio <= limite:
                enviar_email_recordatorio(cita)
                cita.recordatorio_enviado = True
                cita.save(update_fields=["recordatorio_enviado"])
                enviados += 1

        self.stdout.write(self.style.SUCCESS(f"{enviados} recordatorio(s) enviado(s)."))
