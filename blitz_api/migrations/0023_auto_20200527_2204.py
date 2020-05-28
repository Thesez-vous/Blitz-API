# Generated by Django 2.2.12 on 2020-05-28 02:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blitz_api', '0022_auto_20200407_0407'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaluser',
            name='number_of_free_virtual_retreat',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Number of free virtual retreat'),
        ),
        migrations.AddField(
            model_name='user',
            name='number_of_free_virtual_retreat',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Number of free virtual retreat'),
        ),
    ]
