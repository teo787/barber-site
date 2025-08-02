from django.db import models

class Barbero(models.Model):
    nombre=models.CharField(max_length=50)
    imagen=models.ImageField(upload_to="imagenes-barberos")

class Cliente(models.Model):
    nombre=models.CharField(max_length=50)

class Cita(models.Model):
    cliente=models.ForeignKey(Cliente, on_delete=models.CASCADE)
    barbero=models.ForeignKey(Barbero,on_delete=models.CASCADE)
    horario=models.TimeField()
    direccion=models.CharField()
    fecha=models.DateField()

