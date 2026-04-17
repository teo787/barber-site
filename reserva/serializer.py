from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Barbero, Cita  # Importación específica para evitar errores
import datetime
import os

# --- YA NO NECESITAS get_google_calendar_service CON SERVICE ACCOUNT ---
# Mantenemos BarberoSerializer igual
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
        
        if fecha and hora:
            # Combinar fecha y hora para validar que no sea en el pasado
            fecha_hora_cita = timezone.make_aware(datetime.datetime.combine(fecha, hora))
            if fecha_hora_cita < timezone.now():
                raise serializers.ValidationError(
                    {"fecha": "No se puede agendar una cita en el pasado."}
                )
        return data

    def create(self, validated_data):
        # Importación interna para romper el ciclo circular
        from .api import obtener_servicio_google 
        
        # 1. Crear en la Base de Datos local (PostgreSQL)
        cita = super().create(validated_data)
        
        # 2. Sincronización con Google Calendar via OAuth
        service = obtener_servicio_google()
        if service:
            try:
                # Calculamos tiempos
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
                    'attendees': [], # Vacío para evitar invitaciones extra
                }

                # Insertamos en el calendario del barbero
                created_event = service.events().insert(
                    calendarId=cita.barbero.calendar_id, 
                    body=event_body,
                    sendUpdates='none' # Evita notificaciones que duplican eventos
                ).execute()

                # GUARDAMOS EL ID DE GOOGLE (Vital para que el borrado funcione)
                cita.google_event_id = created_event.get('id')
                cita.save()
                
                print(f"Evento sincronizado en Google con ID: {cita.google_event_id}")
            
            except Exception as e:
                print(f"Error al sincronizar con Google Calendar: {e}")

        # 3. Notificación por Correo (Corregido para evitar el error de la 'ñ' y eventos fantasma)
        try:
            # Usamos un lenguaje que Google no interprete como una "invitación"
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
                fail_silently=True, # Si falla el mail por la 'ñ', la cita NO se rompe
            )
        except Exception as e:
            print(f"Error silencioso en envío de correo: {e}")

        return cita

#        send_mail(
#            subject=asunto,
#            message=mensaje,
#            from_email=settings.EMAIL_HOST_USER,
#            recipient_list=[cita.barbero.email],
#            fail_silently=False
#        )

       