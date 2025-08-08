from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework.response import Response
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
