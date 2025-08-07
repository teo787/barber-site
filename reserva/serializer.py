from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import *

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model=Cliente
        fields="__all__"
        read_only_fields=["id", "nombre", "email", "telefono"]

class BarberoSerializer(serializers.ModelSerializer):
    class Meta:
        model=Barbero
        fields="__all__"
        read_only_fields=["id"]

class CitaSerializer(serializers.ModelSerializer):
    cliente=ClienteSerializer()
    barbero_id=serializers.PrimaryKeyRelatedField(queryset=Barbero.objects.all(), source="barbero", write_only=True)
    barbero=BarberoSerializer(read_only=True)
    fecha_hora_fin=serializers.DateTimeField(read_only=True)

    class Meta:
        model=Cita
        fields="__all__"
        read_only_fields=["id"]

    
    def create(self, validated_data):
        cliente_data=validated_data.pop("cliente")
        cliente=None
        if cliente_data.get("telefono"):
            cliente, created=Cliente.objects.get_or_create(
                telefono=cliente_data["telefono"],
                defaults={"nombre":cliente_data.get("nombre", "Anonimo"), "email":cliente_data.get("email")}
            )
        elif cliente_data.get("email"):
            cliente, created=Cliente.objects.get_or_create(
                email=cliente_data["email"],
                defaults={"nombre":cliente_data.get("nombre", "Anonimo"), "email":cliente_data.get("email")}
            )
        else:
            cliente = Cliente.objects.create(
                nombre=cliente_data.get('nombre', 'Anónimo'),
                telefono=cliente_data.get('telefono'),
                email=cliente_data.get('email')
            )
        validated_data["cliente"]=cliente

        cita=Cita.objects.create(**validated_data)
        
        asunto = 'Nueva reserva recibida'
        mensaje = (
            f'Hola,\n\n'
            f'{cita.cliente.nombre} ha realizado una nueva reserva para el {cita.fecha_hora_inicio}\n\n'
            f'Revisa los detalles en el panel de administración.\n\n'
            f'Saludos,\nTu App'
        )

        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[cita.barbero.email],
            fail_silently=False
        )

        return cita