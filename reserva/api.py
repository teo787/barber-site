from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
from django.utils import timezone
import os.path
import uuid
import logging

# Librerías de Google Calendar API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


# ===============================
# AUTENTICACIÓN GOOGLE
# ===============================

def obtener_servicio_google():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES
            )

            creds = flow.run_local_server(
                port=8080,
                access_type='offline',
                prompt='consent'
            )

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


# ===============================
# API BARBEROS
# ===============================

class BarberoApi(APIView):

    def get(self, request):
        barberos = Barbero.objects.all()
        serializer = BarberoSerializer(barberos, many=True)
        return Response(serializer.data)


# ===============================
# API CITAS
# ===============================

class CitaApi(APIView):

    def get(self, request):
        citas = Cita.objects.all()
        serializer = CitaSerializer(citas, many=True)
        return Response(serializer.data)


    def post(self, request):

        data = request.data
        serializer = CitaSerializer(data=data)

        if serializer.is_valid():

            cita = serializer.save()

            try:

                service = obtener_servicio_google()

                start_datetime = datetime.combine(cita.fecha, cita.hora)
                end_datetime = start_datetime + timedelta(hours=1)

                # 🔴 IMPORTANTE
                # añadimos extendedProperties para que el webhook
                # sepa que el evento fue creado por nuestro sistema

                evento = {

                    'summary': f'Cita Barbería: {cita.nombre_cliente}',

                    'description': f'Servicio con {cita.barbero.nombre}',

                    'extendedProperties': {
                        'private': {
                            'from_system': 'barberia_app'
                        }
                    },

                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': 'America/Bogota'
                    },

                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': 'America/Bogota'
                    }
                }

                cal_id = cita.barbero.calendar_id or "primary"

                google_event = service.events().insert(
                    calendarId=cal_id,
                    body=evento
                ).execute()

                # guardamos el id de google
                cita.google_event_id = google_event.get('id')
                cita.save()

                return Response(serializer.data)

            except Exception as e:

                return Response({
                    "mensaje": "Cita guardada pero falló Google Calendar",
                    "error": str(e)
                }, status=201)

        return Response(serializer.errors, status=400)


# ===============================
# HORAS DISPONIBLES
# ===============================

def horas_disponibles(request, barbero_id, fecha_str):

    try:

        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        citas_existentes = Cita.objects.filter(
            barbero_id=barbero_id,
            fecha=fecha_obj
        ).values_list('hora', flat=True)

        horas_ocupadas = [h.strftime('%H:%M') for h in citas_existentes]

        horas_trabajo = [
            '10:00','11:00','12:00','13:00','14:00',
            '15:00','16:00','17:00','18:00','19:00','20:00'
        ]

        disponibles = [
            h for h in horas_trabajo
            if h not in horas_ocupadas
        ]

        return JsonResponse({'horas': disponibles})

    except Exception as e:

        return JsonResponse({'error': str(e)}, status=400)


# ===============================
# WEBHOOK GOOGLE CALENDAR
# ===============================

@csrf_exempt
def webhook_google_calendar(request):

    resource_state = request.headers.get('X-Goog-Resource-State')

    if resource_state == 'sync':
        return HttpResponse(status=200)

    try:

        service = obtener_servicio_google()

        barberos = Barbero.objects.exclude(
            calendar_id__isnull=True
        ).exclude(
            calendar_id=""
        )

        for barbero in barberos:

            events_result = service.events().list(
                calendarId=barbero.calendar_id
            ).execute()

            events = events_result.get('items', [])

            google_ids = []

            for event in events:

                google_id = event.get('id')
                google_ids.append(google_id)

                summary = event.get('summary', 'Cita desde Google')

                # 🔴 ignorar eventos creados por nuestro sistema
                props = event.get('extendedProperties', {}).get('private', {})

                if props.get('from_system') == 'barberia_app':
                    continue

                start_data = event.get('start', {})

                fecha_str = start_data.get('dateTime') or start_data.get('date')

                if not fecha_str:
                    continue

                fecha_dt = datetime.fromisoformat(
                    fecha_str.replace('Z', '+00:00')
                )

                cita_existente = Cita.objects.filter(
                    google_event_id=google_id
                ).first()

                if cita_existente:

                    # actualizar si cambió fecha u hora
                    if cita_existente.fecha != fecha_dt.date() or \
                       cita_existente.hora != fecha_dt.time():

                        cita_existente.fecha = fecha_dt.date()
                        cita_existente.hora = fecha_dt.time()
                        cita_existente.save()

                        logger.info(f"Cita {google_id} actualizada")

                else:

                    if fecha_dt > timezone.now():

                        Cita.objects.create(

                            barbero=barbero,

                            nombre_cliente=summary,

                            telefono_cliente="N/A",

                            fecha=fecha_dt.date(),

                            hora=fecha_dt.time(),

                            google_event_id=google_id
                        )

                        logger.info(
                            f"Cita {google_id} creada desde Google"
                        )

            # 🔴 ELIMINAR CITAS QUE YA NO EXISTEN EN GOOGLE

            Cita.objects.filter(
                barbero=barbero
            ).exclude(
                google_event_id__in=google_ids
            ).delete()

    except Exception as e:

        logger.error(f"Error en webhook: {e}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)