from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from datetime import datetime, timedelta
import os.path
from django.http import HttpResponse
# Librerías de Google Calendar API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from django.http import HttpResponse, JsonResponse 
from django.views.decorators.csrf import csrf_exempt
import uuid
from .models import Cita
import logging
# Permisos para leer/escribir en el calendario
SCOPES = ['https://www.googleapis.com/auth/calendar']

def obtener_servicio_google():
    """Maneja la autenticación y devuelve el objeto del servicio de Google."""
    creds = None
    # El archivo token.json se crea automáticamente al iniciar sesión la primera vez
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

class BarberoApi(APIView):
    def get(self, request):
        barberos = Barbero.objects.all()
        serializer = BarberoSerializer(barberos, many=True)
        return Response(serializer.data)

class CitaApi(APIView):
    def get(self, request):
        citas = Cita.objects.all()
        serializer = CitaSerializer(citas, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        data = request.data
        serializer = CitaSerializer(data=data)
        
        if serializer.is_valid():
            # 1. Guardar en PostgreSQL
            cita = serializer.save()
            
            try:
                # 2. Conectar con Google Calendar
                service = obtener_servicio_google()
                
                # Combinamos fecha y hora para el formato ISO de Google
                start_datetime = datetime.combine(cita.fecha, cita.hora)
                end_datetime = start_datetime + timedelta(hours=1) # Duración de 1 hora

                evento = {
                    'summary': f'Cita Barbería: {cita.nombre_cliente}',
                    'description': f'Servicio agendado para el barbero {cita.barbero.nombre}',
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': 'America/Bogota', # Cambia según tu ubicación
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': 'America/Bogota',
                    },
                }

                # 3. Crear el evento en el calendario del barbero
                # Usamos el calendar_id del barbero, si no tiene usamos el principal ('primary')
                cal_id = getattr(cita.barbero, 'calendar_id', 'primary')
                if not cal_id: cal_id = 'primary'

                google_event = service.events().insert(calendarId=cal_id, body=evento).execute()
                
                # 4. Guardar el ID de Google en nuestra DB para futuras cancelaciones
                cita.google_event_id = google_event.get('id')
                cita.save()

                return Response(serializer.data)

            except Exception as e:
                # Si falla Google, la cita en DB ya quedó guardada. Avisamos del error.
                return Response({
                    "mensaje": "Cita guardada localmente, pero falló la conexión con Google Calendar.",
                    "error": str(e),
                    "data": serializer.data
                }, status=201)
                
        return Response(serializer.errors, status=400)

def horas_disponibles(request, barbero_id, fecha_str):
    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        citas_existentes = Cita.objects.filter(
            barbero_id=barbero_id, 
            fecha=fecha_obj
        ).values_list('hora', flat=True)
        
        horas_ocupadas = [h.strftime('%H:%M') for h in citas_existentes]

        horas_trabajo = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', 
                         '16:00', '17:00', '18:00', '19:00', '20:00']

        disponibles = [h for h in horas_trabajo if h not in horas_ocupadas]

        return JsonResponse({'horas': disponibles})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    

def suscribir_webhook(url_webhook):
    """
    Recibe la URL de ngrok dinámicamente para registrar el webhook en Google.
    """
    service = obtener_servicio_google()
    if not service:
        print("No se pudo obtener el servicio de Google.")
        return
    
    # Generamos un ID único para esta sesión de vigilancia
    subscription_id = str(uuid.uuid4())
    
    body = {
        'id': subscription_id, 
        'type': 'web_hook',
        'address': url_webhook # La URL que pasas desde la shell
    }
    
    try:
        # Le decimos a Google que empiece a mandar notificaciones a esa URL
        watch_response = service.events().watch(calendarId='primary', body=body).execute()
        print("--- SUSCRIPCIÓN EXITOSA ---")
        print(f"ID de suscripción: {watch_response.get('id')}")
        print(f"Google ahora vigila tu calendario en: {url_webhook}")
        return watch_response
    except Exception as e:
        print(f"Error al suscribir el webhook: {e}")
        return None

logger = logging.getLogger(__name__)

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def webhook_google_calendar(request):
    resource_state = request.headers.get('X-Goog-Resource-State')
    
    if resource_state == 'sync':
        return HttpResponse(status=200)

    from .models import Cita, Barbero
    from .api import obtener_servicio_google

    logger.info("--- NOTIFICACIÓN DE CAMBIO DETECTADA EN GOOGLE ---")

    try:
        service = obtener_servicio_google()
        barberos = Barbero.objects.exclude(calendar_id__isnull=True).exclude(calendar_id="")
        
        for barbero in barberos:
            # Traemos los eventos actuales de Google para este barbero
            events_result = service.events().list(calendarId=barbero.calendar_id).execute()
            events = events_result.get('items', [])
            
            # Mapeamos los eventos de Google por ID
            google_events_dict = {e.get('id'): e for e in events}
            
            # Filtramos las citas locales que pertenecen a este barbero
            citas_locales = Cita.objects.filter(barbero=barbero).exclude(google_event_id__isnull=True)

            for cita in citas_locales:
                # CASO 1: La cita fue eliminada en Google
                if cita.google_event_id not in google_events_dict:
                    logger.info(f"Cita {cita.id} no encontrada en Google. Eliminando de la base de datos...")
                    cita.delete()
                
                # CASO 2: La cita existe, verificar si cambió la fecha/hora
                else:
                    evento_google = google_events_dict[cita.google_event_id]
                    start_data = evento_google.get('start', {})
                    # Google usa 'dateTime' para horas específicas y 'date' para todo el día
                    nueva_fecha_str = start_data.get('dateTime') or start_data.get('date')

                    if nueva_fecha_str:
                        # Limpiamos el formato ISO de Google para que Python lo entienda (manejo de 'Z' y offsets)
                        fecha_limpia = nueva_fecha_str.replace('Z', '+00:00')
                        nueva_fecha_dt = datetime.fromisoformat(fecha_limpia)

                        # IMPORTANTE: Solo actualizamos si hay una diferencia real
                        # Comparamos quitando microsegundos por si acaso
                        if cita.fecha.replace(microsecond=0) != nueva_fecha_dt.replace(microsecond=0):
                            logger.info(f"Reprogramación detectada: Cita {cita.id} pasa de {cita.fecha} a {nueva_fecha_dt}")
                            cita.fecha = nueva_fecha_dt
                            cita.save()

    except Exception as e:
        logger.error(f"Error crítico en el webhook: {e}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)