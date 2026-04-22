from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Barbero, Cita
import datetime
import os
from rest_framework import serializers
from django.utils import timezone
from .models import Cita, Barbero

import datetime

class BarberoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barbero
        fields = "__all__"
        read_only_fields = ["id"]


class CitaSerializer(serializers.ModelSerializer):
    barbero_id = serializers.PrimaryKeyRelatedField(
        queryset=Barbero.objects.all(), source="barbero", write_only=True
    )
    barbero = BarberoSerializer(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Cita
        fields = [
            'id', 'barbero_id', 'barbero', 'fecha', 'hora', 
            'nombre_cliente', 'telefono_cliente', 'fecha_creacion'
        ]

    def validate(self, data):
        fecha = data.get('fecha')
        hora = data.get('hora')
        barbero = data.get('barbero')

        if fecha and hora:
            # 1. Validación de Día de Descanso
            dia_semana_cita = fecha.weekday()
            if barbero and dia_semana_cita == barbero.dia_descanso:
                nombre_dia = barbero.get_dia_descanso_display()
                raise serializers.ValidationError(
                    {"fecha": f"El barbero {barbero.nombre} no trabaja los días {nombre_dia}."}
                )

            # 2. Validación de Fecha/Hora pasada
            # Combinamos para obtener un objeto datetime consciente de la zona horaria
            fecha_hora_cita = timezone.make_aware(datetime.datetime.combine(fecha, hora))
            if fecha_hora_cita < timezone.now():
                raise serializers.ValidationError(
                    {"fecha": "No se puede agendar una cita en el pasado."}
                )
        return data

    def create(self, validated_data):
        from .api import obtener_servicio_google 
        from django.core.mail import send_mail
        from django.conf import settings

        # 1. Crear en la Base de Datos local primero
        cita = super().create(validated_data)
        
        # 2. Sincronización con Google Calendar
        service = obtener_servicio_google()
        
        # Verificamos si service existe y si aún NO tiene google_event_id (para evitar duplicados)
        if service and not cita.google_event_id:
            try:
                # Preparar tiempos
                start_dt = datetime.datetime.combine(cita.fecha, cita.hora)
                end_dt = start_dt + datetime.timedelta(hours=1)
                
                event_body = {
                    'summary': f'Cita: {cita.nombre_cliente} - {cita.barbero.nombre}',
                    'location': 'Explicit Barber Shop',
                    'description': f'Teléfono cliente: {cita.telefono_cliente}',
                    'start': {
                        'dateTime': start_dt.isoformat(),
                        'timeZone': 'America/Bogota', 
                    },
                    'end': {
                        'dateTime': end_dt.isoformat(),
                        'timeZone': 'America/Bogota', 
                    },
                }

                # Insertar evento en el calendario del barbero
                created_event = service.events().insert(
                    calendarId=cita.barbero.calendar_id, 
                    body=event_body,
                    sendUpdates='none'
                ).execute()

                # Guardamos el ID retornado por Google de inmediato
                # update_fields asegura que no disparemos señales de guardado innecesarias
                cita.google_event_id = created_event.get('id')
                cita.save(update_fields=['google_event_id'])
                
                print(f"Evento sincronizado correctamente con ID: {cita.google_event_id}")
            
            except Exception as e:
                print(f"Error al sincronizar con Google Calendar: {e}")

        # 3. Notificación por Correo al Barbero
        try:
            asunto = f"Nueva Cita: {cita.nombre_cliente}"
            mensaje = (
                f"Hola {cita.barbero.nombre},\n\n"
                f"Tienes una nueva cita agendada:\n"
                f"- Cliente: {cita.nombre_cliente}\n"
                f"- Teléfono: {cita.telefono_cliente}\n"
                f"- Fecha: {cita.fecha}\n"
                f"- Hora: {cita.hora}\n\n"
                f"La cita ya ha sido agregada a tu Google Calendar."
            )

            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [cita.barbero.email], # Usamos el email real del barbero
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error enviando correo: {e}")

        return cita