from rest_framework import serializers
from .models import FuelStop


class FuelStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelStop
        fields = [
            "opis_truckstop_id",
            "truckstop_name",
            "address",
            "city",
            "state",
            "rack_id",
            "retail_price",
            "latitude",
            "longitude",
        ]
