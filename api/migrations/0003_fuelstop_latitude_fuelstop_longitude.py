# Generated by Django 4.2.6 on 2024-10-19 18:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_fuelstop_retail_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuelstop',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='fuelstop',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
