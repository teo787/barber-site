from django.core.management.base import BaseCommand
from reserva.api import obtener_servicio_google
from reserva.models import Barbero
import uuid


class Command(BaseCommand):

    help = "Activa el webhook de Google Calendar para todos los barberos"

    def handle(self, *args, **options):

        service = obtener_servicio_google()

        barberos = Barbero.objects.exclude(
            calendar_id__isnull=True
        ).exclude(
            calendar_id=""
        )

        if not barberos.exists():
            self.stdout.write(self.style.WARNING("⚠ No hay barberos con calendar_id"))
            return

        for barbero in barberos:

            try:

                channel_id = str(uuid.uuid4())

                body = {
                    "id": channel_id,
                    "type": "web_hook",
                    "address": "https://explicit-barber.onrender.com/webhook_google_calendar/",
                }

                response = service.events().watch(
                    calendarId=barbero.calendar_id,
                    body=body
                ).execute()

                # guardar datos del canal
                barbero.watch_channel_id = channel_id
                barbero.watch_resource_id = response.get("resourceId")
                barbero.watch_expiration = response.get("expiration")
                barbero.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Watch activado para {barbero.nombre} | calendar_id: {barbero.calendar_id}"
                    )
                )

            except Exception as e:

                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Error con {barbero.nombre} | calendar_id: {barbero.calendar_id} | {e}"
                    )
                )