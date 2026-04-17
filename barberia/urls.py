from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from reserva.api import webhook_google_calendar

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reserva.urls')),  
    path ('Membresia/',include('reserva.urls')),
    path('Barbers/', include('reserva.urls')),
    path('Reserva/', include('reserva.urls')),
    path('webhook_google_calendar/', webhook_google_calendar, name='webhook_google_calendar'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)