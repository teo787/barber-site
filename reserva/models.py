from django.db import models
from django.utils import timezone

class Barbero(models.Model):
    nombre=models.CharField(max_length=50)
    imagen=models.ImageField(upload_to="imagenes-barberos")
    email=models.EmailField()

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    nombre=models.CharField(max_length=50)
    telefono=models.IntegerField()
    email=models.EmailField()

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    cliente=models.ForeignKey(Cliente, on_delete=models.CASCADE)
    barbero=models.ForeignKey(Barbero,on_delete=models.CASCADE)
    fecha_hora_inicio=models.DateTimeField()

    def __str__(self):
        return self.barbero