from django.urls import path
from .views import pagina_principal,reserva
from .api import *

urlpatterns = [
    path('', pagina_principal, name="main"),
    
    path('reserva/', reserva),
    path("api/barbero/", BarberoApi.as_view(), name="barbero-api"),
    path("api/cita/", CitaApi.as_view(), name="cita-api"),
    path("reserva/horas_disponibles/<int:barbero_id>/<str:fecha_str>/", horas_disponibles, name="horas-disponibles")
]
