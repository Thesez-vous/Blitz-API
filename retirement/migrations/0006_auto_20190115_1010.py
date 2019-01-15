# Generated by Django 2.0.8 on 2019-01-15 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('retirement', '0005_retirement_place_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalretirement',
            name='carpool_url',
            field=models.CharField(blank=True, max_length=2000, null=True, verbose_name='Carpool URL'),
        ),
        migrations.AddField(
            model_name='historicalretirement',
            name='review_url',
            field=models.CharField(blank=True, max_length=2000, null=True, verbose_name='Review URL'),
        ),
        migrations.AddField(
            model_name='retirement',
            name='carpool_url',
            field=models.CharField(blank=True, max_length=2000, null=True, verbose_name='Carpool URL'),
        ),
        migrations.AddField(
            model_name='retirement',
            name='review_url',
            field=models.CharField(blank=True, max_length=2000, null=True, verbose_name='Review URL'),
        ),
    ]
