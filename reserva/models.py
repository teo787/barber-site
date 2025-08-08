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

    def __str__(self):
        return f"Reserva de {self.nombre_cliente} con {self.barbero.nombre} el {self.fecha} a las {self.hora}"