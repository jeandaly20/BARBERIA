from django.core.management.base import BaseCommand
from django.utils import timezone

from citas.models import Cita
from citas.notificaciones import enviar_email_resumen_diario


class Command(BaseCommand):
    help = "Envía al dueño un resumen de las citas del día. Pensado para correr una vez al día."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        citas_de_hoy = list(
            Cita.objects.filter(fecha=hoy)
            .exclude(estado=Cita.ESTADO_CANCELADA)
            .order_by("hora_inicio")
        )
        enviar_email_resumen_diario(citas_de_hoy)
        self.stdout.write(self.style.SUCCESS(f"Resumen enviado ({len(citas_de_hoy)} cita(s))."))
