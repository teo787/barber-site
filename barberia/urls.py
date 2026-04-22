from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from reserva.api import webhook_google_calendar

urlpatterns = [
    # Panel de administración
    path('admin/', admin.site.urls),
    
    # Rutas de la aplicación reserva
    path('', include('reserva.urls')),  
    
    # Webhook para Google Calendar
    path('webhook_google_calendar/', webhook_google_calendar, name='webhook_google_calendar'),
]

# Configuración para servir archivos estáticos y media en desarrollo y producción
# WhiteNoise se encargará de los STATIC en producción, pero estas rutas ayudan a Django
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)