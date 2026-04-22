# reserva/management/commands/activar_watch.py
from django.core.management.base import BaseCommand
from reserva.api import obtener_servicio_google
from reserva.models import Barbero
import uuid

class Command(BaseCommand):
    help = 'Activa el webhook de Google Calendar para todos los barberos'

    def handle(self, *args, **options):
        service = obtener_servicio_google()
        barberos = Barbero.objects.exclude(calendar_id__isnull=True).exclude(calendar_id="")

        for barbero in barberos:
            channel_id = str(uuid.uuid4()) # Genera un ID único para el canal
            body = {
                'id': channel_id,
                'type': 'web_hook',
                'address': 'https://explicit-barber.onrender.com/webhook_google_calendar/'
            }
            
            try:
                # Suscribirse al calendario del barbero
                service.events().watch(calendarId=barbero.calendar_id, body=body).execute()
                self.stdout.write(self.style.SUCCESS(f'✅ Watch activado para: {barbero.nombre}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error con {barbero.nombre}: {e}'))