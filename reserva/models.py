from django.db import models
from django.utils import timezone

class Barbero(models.Model):
    nombre=models.CharField(max_length=50)
    imagen=models.ImageField(upload_to="imagenes-barberos")
    email=models.EmailField()
    calendar_id=models.CharField(max_length=255)

    def __str__(self):
        return self.nombre

class Cita(models.Model):
    barbero=models.ForeignKey(Barbero,on_delete=models.CASCADE)
    fecha=models.DateField()
    hora=models.TimeField()
    nombre_cliente=models.CharField(max_length=100)
    telefono_cliente=models.CharField(max_length=20)
    fecha_creacion=models.DateTimeField(auto_now_add=True)
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self):
        return f"Reserva de {self.nombre_cliente} con {self.barbero.nombre} el {self.fecha} a las {self.hora}"
    
from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(post_delete, sender=Cita)
def eliminar_en_google_calendar(sender, instance, **kwargs):
    if instance.google_event_id:
        from .api import obtener_servicio_google # Asegúrate de que la ruta sea correcta
        try:
            service = obtener_servicio_google()
            # Usamos el calendar_id del barbero o 'primary'
            cal_id = getattr(instance.barbero, 'calendar_id', 'primary') or 'primary'
            
            service.events().delete(calendarId=cal_id, eventId=instance.google_event_id).execute()
            print(f"Evento {instance.google_event_id} eliminado de Google Calendar")
        except Exception as e:
            print(f"Error al eliminar en Google: {e}")