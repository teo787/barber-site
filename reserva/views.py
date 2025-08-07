from django.shortcuts import render

# Create your views here.
def pagina_principal(request):
    return render(request,'Paginaprincipal.html')
def  membresia(request):
    return render(request,'Membresia.html')
def barbers(request):
    return render(request,'Barbers.html')
def reserva(request):
    return render(request,'Reserva.html')
