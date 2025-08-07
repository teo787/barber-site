from django.db import models
from django.utils import timezone

class Barbero(models.Model):
    nombre=models.CharField(max_length=50)
    imagen=models.ImageField(upload_to="imagenes-barberos")

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    nombre=models.CharField(max_length=50)
    telefono=models.IntegerField()
    email=models.EmailField()

    def __str__(self):
        return self.nombre

class Servicio(models.Model):
    nombre=models.CharField(max_length=100)
    duracion=models.PositiveIntegerField()
    precio=models.FloatField()

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    cliente=models.ForeignKey(Cliente, on_delete=models.CASCADE)
    barbero=models.ForeignKey(Barbero,on_delete=models.CASCADE)
    servicio=models.ForeignKey(Servicio, on_delete=models.CASCADE)
    fecha_hora_inicio=models.DateTimeField()
    fecha_hora_fin=models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.barbero

    def save(self, *args, **kwargs):
        if self.fecha_hora_inicio and self.servicio and not self.fecha_hora_fin:
            self.fecha_hora_fin=self.fecha_hora_inicio+timezone.timedelta(minutes=self.servicio.duracion)

        if self.pk:
            overlapping_appointments=Cita.objects.filter(
                barbero=self.barbero,
                fecha_hora_inicio__lt=self.fecha_hora_inicio,
                fecha_hora_fin__gt=self.fecha_hora_fin,
            ).exclude(pk=self.pk)

        if overlapping_appointments.exists():
            print(f"ADVERTENCIA: Cita superpuesta para el barbero: {self.barbero.nombre}")
        super().save(*args, **kwargs)
