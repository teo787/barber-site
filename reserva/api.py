from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from datetime import datetime
import json

class BarberoApi(APIView):
    def get(self, request):
        barberos=Barbero.objects.all()
        serializer=BarberoSerializer(barberos, many=True)
        return Response(serializer.data)

class CitaApi(APIView):
    def get(self, request):
        citas=Cita.objects.all()
        serializer=CitaSerializer(citas, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        data=request.data
        serializer=CitaSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)


def horas_disponibles(request, barbero_id, fecha_str):
    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        barbero = Barbero.objects.get(id=barbero_id)
        
        horas_trabajo = [
            '10:00', '11:00', '12:00', '13:00', '14:00', '15:00',
            '16:00', '17:00', '18:00', '19:00', '20:00'
        ]

        citas_existentes = Cita.objects.filter(
            barbero=barbero, 
            fecha=fecha_obj
        ).values_list('hora', flat=True)
        
        horas_ocupadas = [hora.strftime('%H:%M') for hora in citas_existentes]
        
        horas_disponibles = [hora for hora in horas_trabajo if hora not in horas_ocupadas]

        return JsonResponse({'horas': horas_disponibles})
    except (Barbero.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Barbero o fecha inválidos'}, status=404)
