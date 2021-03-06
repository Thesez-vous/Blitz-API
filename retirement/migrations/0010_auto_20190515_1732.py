# Generated by Django 2.0.8 on 2019-05-15 21:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('retirement', '0009_reservation_orderline_allow_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalretirement',
            name='has_shared_rooms',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='retirement',
            name='has_shared_rooms',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
