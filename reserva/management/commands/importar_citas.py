from django.core.management.base import BaseCommand
from reserva.models import Barbero, Cita
from reserva.api import obtener_servicio_google
from datetime import datetime, time, timedelta
import pytz

class Command(BaseCommand):
    help = 'Importa citas ocupando todo el rango de tiempo del evento de Google'

    def handle(self, *args, **options):
        service = obtener_servicio_google()
        if not service:
            self.stdout.write(self.style.ERROR("Error de conexión con Google."))
            return

        barberos = Barbero.objects.exclude(calendar_id__isnull=True).exclude(calendar_id="")
        tz_local = pytz.timezone('America/Bogota')
        
        # Límites de la barbería
        HORA_INICIO_LABORAL = time(10, 0)
        HORA_FIN_LABORAL = time(20, 0)

        for barbero in barberos:
            self.stdout.write(f"--- Procesando agenda de: {barbero.nombre} ---")
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
                    summary = event.get('summary', 'Ocupado (Google)')
                    
                    # 1. Obtener inicio y fin del evento
                    start_str = event['start'].get('dateTime', event['start'].get('date'))
                    end_str = event['end'].get('dateTime', event['end'].get('date'))
                    
                    if not start_str or not end_str:
                        continue

                    # Convertir a zona horaria local
                    dt_inicio = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(tz_local)
                    dt_fin = datetime.fromisoformat(end_str.replace('Z', '+00:00')).astimezone(tz_local)

                    # 2. Bucle para marcar cada hora como ocupada
                    # Empezamos en el inicio y sumamos 1 hora hasta llegar al fin
                    temp_dt = dt_inicio
                    while temp_dt < dt_fin:
                        hora_actual = temp_dt.time()
                        fecha_actual = temp_dt.date()

                        # 3. Solo si está dentro del horario de la barbería
                        if HORA_INICIO_LABORAL <= hora_actual <= HORA_FIN_LABORAL:
                            # Generar un ID único por cada hora bloqueada para evitar duplicados
                            # Ejemplo: "id_evento_2024-04-23_18:00"
                            unique_id = f"{event.get('id')}_{fecha_actual}_{hora_actual.hour}"

                            if not Cita.objects.filter(google_event_id=unique_id).exists():
                                Cita.objects.create(
                                    barbero=barbero,
                                    nombre_cliente=summary,
                                    telefono_cliente="Bloqueado por Calendario",
                                    fecha=fecha_actual,
                                    hora=hora_actual,
                                    google_event_id=unique_id
                                )
                                self.stdout.write(self.style.SUCCESS(f"  [Bloqueado] {hora_actual} - {summary}"))

                        # Avanzar a la siguiente hora
                        temp_dt += timedelta(hours=1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f" Error con {barbero.nombre}: {e}"))

        self.stdout.write(self.style.SUCCESS('Sincronización de rangos completa.'))
