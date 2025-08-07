from django.urls import path
from .views import pagina_principal, membresia,barbers,reserva

urlpatterns = [
    path('', pagina_principal),
    path('Membresia/', membresia),
    path('Barbers/',barbers),
    path('Reserva/', reserva),
]
