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

import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# El scope sigue siendo el mismo
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Ruta al archivo que descargaste de "Cuentas de servicio"
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service_account.json')

def obtener_servicio_google():
    """
    Autenticación mediante Cuenta de Servicio.
    No requiere intervención humana ni genera token.json.
    """
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            logger.error(f"Archivo de credenciales no encontrado en: {SERVICE_ACCOUNT_FILE}")
            return None

        # Usamos service_account en lugar de flow/credentials
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, 
            scopes=SCOPES
        )

        return build('calendar', 'v3', credentials=creds)

    except Exception as e:
        logger.error(f"Error al obtener el servicio de Google: {e}")
        return None


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
        print("POST /api/cita ejecutado")
        print(request.data)
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


"""@csrf_exempt
def webhook_google_calendar(request):

    print("WEBHOOK GOOGLE DISPARADO")

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

            try:

                # --------------------------------
                # USAR SYNCTOKEN SI EXISTE
                # --------------------------------

                if barbero.sync_token:

                    events_result = service.events().list(

                        calendarId=barbero.calendar_id,

                        syncToken=barbero.sync_token

                    ).execute()

                else:

                    # primera sincronización
                    events_result = service.events().list(

                        calendarId=barbero.calendar_id,

                        singleEvents=True

                    ).execute()

                events = events_result.get('items', [])

                for event in events:

                    google_id = event.get('id')

                    if not google_id:
                        continue

                    # evento eliminado
                    if event.get('status') == 'cancelled':

                        Cita.objects.filter(
                            google_event_id=google_id
                        ).delete()

                        continue

                    summary = event.get(
                        'summary',
                        'Cita desde Google'
                    )

                    props = event.get(
                        'extendedProperties',
                        {}
                    ).get('private', {})

                    # ignorar eventos creados por nuestra app
                    if props.get('from_system') == 'barberia_app':
                        continue

                    start_data = event.get('start', {})

                    fecha_str = start_data.get('dateTime') or start_data.get('date')

                    if not fecha_str:
                        continue

                    fecha_dt = datetime.fromisoformat(
                        fecha_str.replace('Z', '+00:00')
                    )

                    fecha = fecha_dt.date()
                    hora = fecha_dt.time()

                    cita_existente = Cita.objects.filter(
                        google_event_id=google_id
                    ).first()

                    # -------------------------
                    # ACTUALIZAR
                    # -------------------------

                    if cita_existente:

                        if cita_existente.fecha != fecha or cita_existente.hora != hora:

                            cita_existente.fecha = fecha
                            cita_existente.hora = hora
                            cita_existente.save()

                            logger.info(
                                f"Cita {google_id} actualizada"
                            )

                        continue

                    # -------------------------
                    # PROTEGER DUPLICADOS
                    # -------------------------

                    duplicada = Cita.objects.filter(
                        barbero=barbero,
                        fecha=fecha,
                        hora=hora
                    ).exists()

                    if duplicada:
                        continue

                    # -------------------------
                    # CREAR CITA
                    # -------------------------

                    if fecha_dt > timezone.now():

                        Cita.objects.create(

                            barbero=barbero,

                            nombre_cliente=summary,

                            telefono_cliente="N/A",

                            fecha=fecha,

                            hora=hora,

                            google_event_id=google_id
                        )

                        logger.info(
                            f"Cita {google_id} creada desde Google"
                        )

                # --------------------------------
                # GUARDAR NUEVO SYNCTOKEN
                # --------------------------------

                new_sync_token = events_result.get('nextSyncToken')

                if new_sync_token:

                    barbero.sync_token = new_sync_token
                    barbero.save()

            except Exception as e:

                # token expirado → resetear
                if "Sync token is no longer valid" in str(e):

                    barbero.sync_token = None
                    barbero.save()

                    logger.warning(
                        f"syncToken reiniciado para {barbero.id}"
                    )

                else:

                    logger.error(
                        f"Error barbero {barbero.id}: {e}"
                    )

    except Exception as e:

        logger.error(f"Error en webhook: {e}")

        return HttpResponse(status=500)

    return HttpResponse(status=200)"""
    
@csrf_exempt
def webhook_google_calendar(request):
    print("WEBHOOK GOOGLE DISPARADO")
    resource_state = request.headers.get('X-Goog-Resource-State')

    if resource_state == 'sync':
        return HttpResponse(status=200)

    from .models import Cita, Barbero
    from .api import obtener_servicio_google

    try:
        service = obtener_servicio_google()
        barberos = Barbero.objects.exclude(calendar_id__isnull=True).exclude(calendar_id="")

        for barbero in barberos:
            try:
                # 1. Obtener eventos (usando syncToken si existe)
                if barbero.sync_token:
                    events_result = service.events().list(
                        calendarId=barbero.calendar_id,
                        syncToken=barbero.sync_token
                    ).execute()
                else:
                    events_result = service.events().list(
                        calendarId=barbero.calendar_id,
                        singleEvents=True
                    ).execute()

                events = events_result.get('items', [])

                for event in events:
                    google_id = event.get('id')
                    if not google_id:
                        continue

                    # 2. Manejo de eliminaciones
                    if event.get('status') == 'cancelled':
                        Cita.objects.filter(google_event_id=google_id).delete()
                        continue

                    # 3. Extraer tiempos
                    start_data = event.get('start', {})
                    fecha_str = start_data.get('dateTime') or start_data.get('date')
                    if not fecha_str:
                        continue

                    fecha_dt = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    fecha_actual = fecha_dt.date()
                    hora_actual = fecha_dt.time()
                    summary = event.get('summary', 'Cita desde Google')

                    # 4. BUSCAR SI YA EXISTE EN LA BASE DE DATOS
                    cita_existente = Cita.objects.filter(google_event_id=google_id).first()

                    if cita_existente:
                        # SI EXISTE, ACTUALIZAMOS (Aquí es donde fallaba antes)
                        if cita_existente.fecha != fecha_actual or cita_existente.hora != hora_actual:
                            cita_existente.fecha = fecha_actual
                            cita_existente.hora = hora_actual
                            cita_existente.save()
                            logger.info(f"Cita {google_id} movida en Google. DB actualizada.")
                        continue # Pasamos al siguiente evento

                    # 5. SI NO EXISTE, PROTECCIÓN CONTRA DUPLICADOS POR FECHA/HORA
                    # Esto evita crear una nueva si el Serializer apenas está guardando
                    duplicada = Cita.objects.filter(
                        barbero=barbero,
                        fecha=fecha_actual,
                        hora=hora_actual
                    ).exists()

                    if duplicada:
                        continue

                    # 6. CREAR CITA (Solo si es a futuro)
                    if fecha_dt > timezone.now():
                        Cita.objects.create(
                            barbero=barbero,
                            nombre_cliente=summary,
                            telefono_cliente="N/A",
                            fecha=fecha_actual,
                            hora=hora_actual,
                            google_event_id=google_id
                        )
                        logger.info(f"Cita {google_id} creada desde Google")

                # 7. GUARDAR NUEVO SYNCTOKEN
                new_sync_token = events_result.get('nextSyncToken')
                if new_sync_token:
                    barbero.sync_token = new_sync_token
                    barbero.save()

            except Exception as e:
                if "Sync token is no longer valid" in str(e):
                    barbero.sync_token = None
                    barbero.save()
                    logger.warning(f"syncToken reiniciado para barbero {barbero.id}")
                else:
                    logger.error(f"Error procesando eventos de barbero {barbero.id}: {e}")

    except Exception as e:
        logger.error(f"Error crítico en webhook: {e}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)
