from django.urls import path
from .views import pagina_principal,reserva
from .api import *
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', pagina_principal, name="main"),
    
    path('reserva/', reserva),
    path("api/barbero/", BarberoApi.as_view(), name="barbero-api"),
    path("api/cita/", CitaApi.as_view(), name="cita-api"),
    path("reserva/horas_disponibles/<int:barbero_id>/<str:fecha_str>/", horas_disponibles, name="horas-disponibles")
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # En producción (Render), esto ayuda a servir los archivos estáticos
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    