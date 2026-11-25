"""
Marca como VENCIDA toda membresía ACTIVA cuya fecha de término ya pasó.

Pensado para ejecutarse una vez al día con cron en el servidor (EC2):
    5 0 * * *  cd /ruta/fitlife_backend && venv/bin/python manage.py actualizar_membresias
"""
from django.core.management.base import BaseCommand

from membresias.models import Membresia


class Command(BaseCommand):
    help = "Marca como vencidas las membresías activas cuya fecha de término ya pasó."

    def handle(self, *args, **options):
        total = Membresia.actualizar_vencidas()
        self.stdout.write(self.style.SUCCESS(f"{total} membresía(s) marcadas como VENCIDA."))
