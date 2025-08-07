from rest_framework import serializers
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


class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model=Servicio
        fields="__all__"
        read_only_fields=["id", "nombre", "duracion", "precio"]


class CitaSerializer(serializers.ModelSerializer):
    cliente=ClienteSerializer()
    barbero_id=serializers.PrimaryKeyRelatedField(queryset=Barbero.objects.all(), source="barbero", write_only=True)
    servicio_id=serializers.PrimaryKeyRelatedField(queryset=Servicio.objects.all(), source="servicio", write_only=True)
    barbero=BarberoSerializer(read_only=True)
    servicio=ServicioSerializer(read_only=True)
    fecha_hora_fin=serializers.DateTimeField(read_only=True)

    class Meta:
        model=Cita
        fields="__all__"
        read_only_fields=["id"]


    def validate(self, data):
        fecha_hora_inicio=data.get("fecha_hora_inicio")
        barbero=data.get("barbero")
        servicio=data.get("servicio")

        if fecha_hora_inicio<timezone.now():
            raise serializers.ValidationError(
                {"fecha_hora_inicio":"No se puede agendar una cita en el pasado"}
            )
        
        fecha_hora_fin=fecha_hora_inicio+timezone.timedelta(minutes=servicio.duracion)
        data["fecha_hora_fin"]=fecha_hora_fin

        if barbero:
            overlapping_appointments=Cita.objects.filter(
                barbero=barbero,
                fecha_hora_inicio__lt=fecha_hora_inicio,
                fecha_hora_fin__gt=fecha_hora_fin
            )

            if self.instance:
                overlapping_appointments = overlapping_appointments.exclude(pk=self.instance.pk)
            
            if overlapping_appointments.exists():
                raise serializers.ValidationError(
                    {"fecha_hora_inicio": f"El barbero {barbero.nombre} ya tiene una cita agendada en este horario."}
                )
        else:
            raise serializers.ValidationError({"barbero_id": "Barbero no válido."})
        return data
    
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
        
        return cita