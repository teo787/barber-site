from django.shortcuts import render
from .models import Barbero


# Create your views here.
def pagina_principal(request):
    return render(request,'Paginaprincipal.html')
def  membresia(request):
    return render(request,'Membresia.html')
def barbers(request):
    return render(request,'Barbers.html')
def reserva(request):

    barberos=Barbero.objects.all()

    context={
        "barbers":barberos,
    }

    return render(request,'Reserva.html', context)
