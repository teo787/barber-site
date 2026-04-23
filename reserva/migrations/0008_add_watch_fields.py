from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reserva', '0007_barbero_sync_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='barbero',
            name='watch_channel_id',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='barbero',
            name='watch_resource_id',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='barbero',
            name='watch_expiration',
            field=models.BigIntegerField(null=True, blank=True),
        ),
    ]
