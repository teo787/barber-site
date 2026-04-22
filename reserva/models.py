from django.db import models
from django.utils import timezone
from datetime import datetime
from django.db import models

from django.db import models
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver

class Barbero(models.Model):
    nombre = models.CharField(max_length=50)
    imagen = models.CharField(
        max_length=255, 
        help_text="Ruta estática. Ej: Barberia/Imagenes/Pimpon.jpeg"
    )
    email = models.EmailField()
    calendar_id = models.CharField(max_length=255)
    
    DIA_DESCANSO_CHOICES = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]
    
    dia_descanso = models.IntegerField(choices=DIA_DESCANSO_CHOICES, default=6)

    def __str__(self):
        return self.nombre

class Cita(models.Model):
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora = models.TimeField()
    nombre_cliente = models.CharField(max_length=100)
    telefono_cliente = models.CharField(max_length=20)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    google_event_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    last_sync = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reserva de {self.nombre_cliente} con {self.barbero.nombre} el {self.fecha} a las {self.hora}"

# Señal para borrar en Google cuando se borra en Django
@receiver(post_delete, sender=Cita)
def eliminar_en_google_calendar(sender, instance, **kwargs):
    if instance.google_event_id:
        from .api import obtener_servicio_google 
        try:
            service = obtener_servicio_google()
            cal_id = getattr(instance.barbero, 'calendar_id', 'primary') or 'primary'
            service.events().delete(calendarId=cal_id, eventId=instance.google_event_id).execute()
        except Exception as e:
            print(f"Error al eliminar en Google: {e}")
            

def es_dia_laboral(fecha_elegida, barbero):
    """
    Recibe una fecha (objeto date) y un objeto Barbero.
    Retorna True si el barbero trabaja, False si es su día de descanso.
    """
    # weekday() devuelve 0 para Lunes y 6 para Domingo
    dia_semana_cita = fecha_elegida.weekday()
    
    if dia_semana_cita == barbero.dia_descanso:
        return False  # Es su día de descanso
    return True