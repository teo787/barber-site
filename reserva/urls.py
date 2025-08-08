from django.urls import path
from .views import pagina_principal, membresia,barbers,reserva
from .api import *

urlpatterns = [
    path('', pagina_principal),
    path('Membresia/', membresia),
    path('Barbers/',barbers),
    path('Reserva/', reserva),
    path("api/barbero/", BarberoApi.as_view(), name="barbero-api"),
    path("api/cita/", CitaApi.as_view(), name="cita-api")
]
