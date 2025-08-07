from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework.response import Response

class BarberoApi(APIView):
    def get(self, request):
        barberos=Barbero.objects.all()
        serializer=BarberoSerializer(data=barberos, many=True)
        return Response(serializer.data)

class ClienteApi(APIView):
    def get(self, request):
        clientes=Cliente.objects.all()
        serializer=ClienteSerializer(data=clientes, many=True)
        return Response(serializer.data)
    
class CitaApi(APIView):
    def get(self, request):
        citas=Cita.objects.all()
        serializer=CitaSerializer(data=citas, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer=CitaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
