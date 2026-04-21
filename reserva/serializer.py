from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Barbero, Cita
import datetime
import os

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
        fields = ['id', 'barbero_id', 'barbero', 'fecha', 'hora', 
                  'nombre_cliente', 'telefono_cliente', 'fecha_creacion']

    def validate(self, data):
        fecha = data.get('fecha')
        hora = data.get('hora')
        barbero = data.get('barbero') # Obtenemos el objeto barbero de los datos de entrada
        
        if fecha and hora:
            # --- NUEVA VALIDACIÓN: DÍA DE DESCANSO DEL BARBERO ---
            # weekday() en Python: 0=Lunes, 1=Martes... 6=Domingo
            dia_semana_cita = fecha.weekday()
            
            if barbero and dia_semana_cita == barbero.dia_descanso:
                # Obtenemos el nombre del día para el mensaje de error
                nombre_dia = barbero.get_dia_descanso_display()
                raise serializers.ValidationError(
                    {"fecha": f"El barbero {barbero.nombre} no trabaja los días {nombre_dia}."}
                )
            # ------------------------------------------------------

            # Validación de fecha pasada
            fecha_hora_cita = timezone.make_aware(datetime.datetime.combine(fecha, hora))
            if fecha_hora_cita < timezone.now():
                raise serializers.ValidationError(
                    {"fecha": "No se puede agendar una cita en el pasado."}
                )
        return data

    def create(self, validated_data):
        from .api import obtener_servicio_google 
        
        # 1. Crear en la Base de Datos local (PostgreSQL)
        cita = super().create(validated_data)
        
        # 2. Sincronización con Google Calendar via OAuth
        service = obtener_servicio_google()
        if service:
            try:
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
                    'attendees': [],
                }

                created_event = service.events().insert(
                    calendarId=cita.barbero.calendar_id, 
                    body=event_body,
                    sendUpdates='none'
                ).execute()

                cita.google_event_id = created_event.get('id')
                cita.save()
                
                print(f"Evento sincronizado en Google con ID: {cita.google_event_id}")
            
            except Exception as e:
                print(f"Error al sincronizar con Google Calendar: {e}")

        # 3. Notificación por Correo
        try:
            asunto_notificacion = f"Aviso de Gestión: Registro {cita.id}"
            mensaje_notificacion = (
                f"Se ha confirmado una nueva entrada en el sistema.\n\n"
                f"Información técnica:\n"
                f"- Referencia: {cita.nombre_cliente}\n"
                f"- Profesional: {cita.barbero.nombre}\n"
                f"- Día registrado: {cita.fecha}\n"
                f"- Bloque: {cita.hora}\n\n"
                f"Verificar detalles en el panel administrativo."
            )

            send_mail(
                asunto_notificacion,
                mensaje_notificacion,
                settings.DEFAULT_FROM_EMAIL,
                [cita.barbero.calendar_id], 
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error silencioso en envío de correo: {e}")

        return cita