from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import *
import datetime
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



class BarberoSerializer(serializers.ModelSerializer):
    class Meta:
        model=Barbero
        fields="__all__"
        read_only_fields=["id"]


CREDENTIALS_FILE = os.path.join(settings.BASE_DIR, 'engaged-context-466702-r6-363d54f059d4.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Error al autenticarse con Google Calendar: {e}")
        return None


class CitaSerializer(serializers.ModelSerializer):
    barbero_id = serializers.PrimaryKeyRelatedField(
        queryset=Barbero.objects.all(), source="barbero", write_only=True
    )
    barbero = BarberoSerializer(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Cita
        fields = ['id', 'barbero_id', 'barbero', 'fecha', 'hora', 
                  'nombre_cliente', 'telefono_cliente', 'fecha_creacion']

    def validate(self, data):
        fecha = data.get('fecha')
        hora = data.get('hora')
        
        if fecha and hora:
            fecha_hora_cita = timezone.make_aware(timezone.datetime.combine(fecha, hora))
        else:
            raise serializers.ValidationError("La fecha y la hora de la cita son obligatorias.")

        if fecha_hora_cita < timezone.now():
            raise serializers.ValidationError(
                {"fecha": "No se puede agendar una cita en el pasado."}
            )
        return data
    
    def create(self, validated_data):
        barbero_seleccionado = validated_data['barbero']
        cita = super().create(validated_data)
        
        service = get_google_calendar_service()
        if service:
            try:
                barbero_seleccionado = cita.barbero 

                start_datetime_str = f"{cita.fecha}T{cita.hora.strftime('%H:%M:%S')}"
                start_datetime_obj = datetime.datetime.fromisoformat(start_datetime_str)
                end_datetime_obj = start_datetime_obj + datetime.timedelta(hours=1)
                
                event = {
                    'summary': f'Cita de {cita.nombre_cliente} con {barbero_seleccionado.nombre}',
                    'location': 'Explicit Barber Shop',
                    'description': f'Cliente: {cita.nombre_cliente}\nTeléfono: {cita.telefono_cliente}',
                    'start': {
                        'dateTime': start_datetime_obj.isoformat(),
                        'timeZone': 'America/Bogota', 
                    },
                    'end': {
                        'dateTime': end_datetime_obj.isoformat(),
                        'timeZone': 'America/Bogota', 
                    },
                }

                created_event = service.events().insert(
                    calendarId=barbero_seleccionado.calendar_id, 
                    body=event
                ).execute()
                print(f"Evento de Google Calendar creado: {created_event.get('htmlLink')}")
            
            except HttpError as err:
                print(f"Error de la API de Google al crear evento: {err}")
            except Exception as e:
                print(f"Error inesperado al crear el evento de calendario: {e}")

        asunto = 'Nueva reserva recibida'
        mensaje = (
            f'Hola,\n\n'
            f'{cita.nombre_cliente} ha realizado una nueva reserva para el {cita.fecha} a las {cita.hora}\n\n'
            f'Revisa los detalles en el panel de administración.\n\n'
            f'Saludos,\nTu App'
        )

#        send_mail(
#            subject=asunto,
#            message=mensaje,
#            from_email=settings.EMAIL_HOST_USER,
#            recipient_list=[cita.barbero.email],
#            fail_silently=False
#        )

        return cita