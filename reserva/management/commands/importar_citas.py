from django.core.management.base import BaseCommand
from reserva.models import Barbero, Cita
from reserva.api import obtener_servicio_google
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importa citas futuras de Google Calendar que coincidan con el horario laboral'

    def handle(self, *args, **options):
        service = obtener_servicio_google()
        barberos = Barbero.objects.exclude(calendar_id__isnull=True).exclude(calendar_id="")
        
        # Definimos el intervalo de horas de tu página (ajústalo si es necesario)
        HORA_INICIO_LABORAL = time(10, 0)  # 08:00 AM
        HORA_FIN_LABORAL = time(20, 0)   # 08:00 PM

        for barbero in barberos:
            self.stdout.write(f"--- Sincronizando a: {barbero.nombre} ---")
            
            # 1. Filtro de Tiempo: Solo eventos desde "ahora" en adelante
            now = datetime.utcnow().isoformat() + 'Z'
            
            try:
                events_result = service.events().list(
                    calendarId=barbero.calendar_id, 
                    timeMin=now,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])

                for event in events:
                    google_id = event.get('id')
                    
                    # 2. Evitar duplicados
                    if Cita.objects.filter(google_event_id=google_id).exists():
                        continue

                    # Extraer y convertir fecha
                    start_str = event['start'].get('dateTime', event['start'].get('date'))
                    if not start_str:
                        continue
                        
                    fecha_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    hora_cita = fecha_dt.time()

                    # 3. Filtro de Horario: Solo si está en el intervalo de la página
                    if HORA_INICIO_LABORAL <= hora_cita <= HORA_FIN_LABORAL:
                        # Creamos la cita con el nombre que el barbero puso en Google
                        Cita.objects.create(
                            barbero=barbero,
                            nombre_cliente=event.get('summary', 'Cliente Google'),
                            email_cliente="importado@barberia.com", 
                            fecha=fecha_dt,
                            google_event_id=google_id
                        )
                        self.stdout.write(self.style.SUCCESS(f"  + Importada: {event.get('summary')} a las {hora_cita}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  - Ignorada (Fuera de horario): {event.get('summary')} at {hora_cita}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f" Error con {barbero.nombre}: {e}"))

        self.stdout.write(self.style.SUCCESS('Sincronización finalizada con éxito.'))