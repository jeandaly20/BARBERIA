from django.core.management.base import BaseCommand
from django.utils import timezone

from citas.models import Cita


class Command(BaseCommand):
    help = (
        "Pasa a 'expirada' las citas en 'pendiente_pago' cuyo plazo de pago venció, "
        "liberando su horario. Pensado para correr cada pocos minutos (Render Cron Job)."
    )

    def handle(self, *args, **options):
        citas_vencidas = Cita.objects.filter(
            estado=Cita.ESTADO_PENDIENTE_PAGO, expira_en__lt=timezone.now()
        )
        total = citas_vencidas.update(estado=Cita.ESTADO_EXPIRADA)
        self.stdout.write(self.style.SUCCESS(f"{total} cita(s) expirada(s)."))
