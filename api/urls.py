from django.urls import path
from .views import OptimalFuelStopsAPIView

urlpatterns = [
    path("fuel-stops/", OptimalFuelStopsAPIView.as_view(), name="optimal_fuel_stops"),
]
