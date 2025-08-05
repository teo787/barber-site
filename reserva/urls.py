from django.urls import path
from .views import pagina_principal, membresia,barbers

urlpatterns = [
    path('', pagina_principal),
    path('Membresia/', membresia),
    path('Barbers/',barbers)
]
