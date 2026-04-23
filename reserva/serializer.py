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
from django.db import transaction  # ESTA LÍNEA CORRIGE EL ERROR DE TU IMAGEN

# 1. Definimos primero el BarberoSerializer para que esté disponible abajo
class BarberoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barbero
        fields = '__all__'

# 2. Definimos el CitaSerializer
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
            # Validación de Día de Descanso
            if barbero and fecha.weekday() == barbero.dia_descanso:
                nombre_dia = barbero.get_dia_descanso_display()
                raise serializers.ValidationError(
                    {"fecha": f"El barbero {barbero.nombre} no trabaja los días {nombre_dia}."}
                )

            # Validación de Fecha Pasada
            fecha_hora_cita = timezone.make_aware(datetime.datetime.combine(fecha, hora))
            if fecha_hora_cita < timezone.now():
                raise serializers.ValidationError(
                    {"fecha": "No se puede agendar una cita en el pasado."}
                )
        return data

""" def create(self, validated_data):
        # Importación local para evitar importaciones circulares
        from .api import obtener_servicio_google 
        
        # El bloque atomic evita que dos procesos toquen la tabla al mismo tiempo
        with transaction.atomic():
            # 1. Verificación de seguridad: ¿Ya existe esta cita exacta?
            # Esto detiene la creación de un segundo evento con ID diferente
            existente = Cita.objects.filter(
                barbero=validated_data['barbero'],
                fecha=validated_data['fecha'],
                hora=validated_data['hora'],
                nombre_cliente=validated_data['nombre_cliente']
            ).first()
            
            if existente:
                return existente

            # 2. Crear en la Base de Datos local
            cita = Cita.objects.create(**validated_data)
            
            # 3. Sincronización con Google Calendar
            service = obtener_servicio_google()
            if service:
                try:
                    start_dt = datetime.datetime.combine(cita.fecha, cita.hora)
                    end_dt = start_dt + datetime.timedelta(hours=1)
                    
                    event_body = {
                        'summary': f'Cita: {cita.nombre_cliente} - {cita.barbero.nombre}',
                        'location': 'Explicit Barber Shop',
                        'description': f'Teléfono: {cita.telefono_cliente}',
                        'start': {
                            'dateTime': start_dt.isoformat(),
                            'timeZone': 'America/Bogota', 
                        },
                        'end': {
                            'dateTime': end_dt.isoformat(),
                            'timeZone': 'America/Bogota', 
                        },
                    }

                    # Insertar en Google
                    created_event = service.events().insert(
                        calendarId=cita.barbero.calendar_id, 
                        body=event_body,
                        sendUpdates='none'
                    ).execute()

                    # Guardamos el ID de Google inmediatamente dentro de la transacción
                    cita.google_event_id = created_event.get('id')
                    cita.save(update_fields=['google_event_id'])
                
                except Exception as e:
                    print(f"Error Google Calendar: {e}")

        # 4. Notificación por Correo
        return cita"""