from django.core.management.base import BaseCommand
from reserva.models import Barbero, Cita
from reserva.api import obtener_servicio_google
from datetime import datetime, time
import logging
import pytz  # Para manejar la zona horaria de Colombia

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importa citas futuras de Google Calendar que coincidan con el horario laboral (10 AM - 8 PM)'

    def handle(self, *args, **options):
        service = obtener_servicio_google()
        
        # Validación de seguridad: Si el servicio falló por credenciales, detenemos
        if not service:
            self.stdout.write(self.style.ERROR("No se pudo conectar con Google. Revisa service_account.json"))
            return

        barberos = Barbero.objects.exclude(calendar_id__isnull=True).exclude(calendar_id="")
        
        # Definimos el intervalo de la barbería
        HORA_INICIO_LABORAL = time(10, 0)  # 10:00 AM
        HORA_FIN_LABORAL = time(20, 0)    # 08:00 PM
        
        # Definimos la zona horaria local (Colombia)
        tz_local = pytz.timezone('America/Bogota')

        for barbero in barberos:
            self.stdout.write(f"--- Sincronizando a: {barbero.nombre} ---")
            
            # Filtro de Tiempo: Solo eventos desde "ahora"
            # Usamos UTC para la consulta a la API de Google
            now = datetime.utcnow().isoformat() + 'Z'
            
            try:
                events_result = service.events().list(
                    calendarId=barbero.calendar_id, 
                    timeMin=now,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])

                if not events:
                    self.stdout.write(f"No hay citas futuras para {barbero.nombre}.")

                for event in events:
                    google_id = event.get('id')
                    
                    # 1. Evitar duplicados
                    if Cita.objects.filter(google_event_id=google_id).exists():
                        continue

                    # 2. Extraer y convertir fecha/hora
                    start_str = event['start'].get('dateTime', event['start'].get('date'))
                    if not start_str:
                        continue
                        
                    # Convertimos a la zona horaria de Colombia para comparar bien las horas
                    fecha_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(tz_local)
                    hora_cita = fecha_dt.time()
                    fecha_cita = fecha_dt.date()

                    # 3. Filtro de Horario Laboral (10 AM a 8 PM)
                    if HORA_INICIO_LABORAL <= hora_cita <= HORA_FIN_LABORAL:
                        # NOTA: Quité 'email_cliente' porque daba error. 
                        # Si tu campo se llama diferente (ej. 'correo'), cámbialo aquí.
                        Cita.objects.create(
                            barbero=barbero,
                            nombre_cliente=event.get('summary', 'Cita desde Google'),
                            telefono_cliente="N/A", # Campo por defecto
                            fecha=fecha_cita,
                            hora=hora_cita,
                            google_event_id=google_id
                        )
                        self.stdout.write(self.style.SUCCESS(f"  + Importada: {event.get('summary')} | {fecha_cita} {hora_cita}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  - Ignorada (Fuera de horario): {event.get('summary')} a las {hora_cita}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f" Error con {barbero.nombre}: {e}"))

        self.stdout.write(self.style.SUCCESS('Sincronización finalizada con éxito.'))
