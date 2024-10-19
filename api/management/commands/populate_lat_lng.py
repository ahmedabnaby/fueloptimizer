import time
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from api.models import FuelStop
import requests

# Initialize the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the geolocators
nominatim = Nominatim(user_agent="fuel_optimizer")
ORS_API_KEY = "5b3ce3597851110001cf6248a96ca0d0608c40f8b8d965731df28481"  # Replace with your actual API key


class RateLimiter:
    def __init__(self, calls_per_second):
        self.calls_per_second = calls_per_second
        self.last_call = 0

    def wait(self):
        now = time.time()
        time_since_last_call = now - self.last_call
        if time_since_last_call < 1 / self.calls_per_second:
            time.sleep((1 / self.calls_per_second) - time_since_last_call)
        self.last_call = time.time()


rate_limiter = RateLimiter(1)  # 1 call per second


def rate_limited_geocode(geocoder, address):
    rate_limiter.wait()
    try:
        return geocoder.geocode(address, timeout=10)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding error: {str(e)}")
        return None


def openroute_geocode(address):
    rate_limiter.wait()
    url = f"https://api.openrouteservice.org/geocode/search?api_key={ORS_API_KEY}&text={address}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("features"):
            coordinates = data["features"][0]["geometry"]["coordinates"]
            return coordinates[1], coordinates[0]  # OpenRouteService returns [lon, lat]
    except (requests.RequestException, ValueError) as e:
        logger.warning(f"OpenRouteService geocoding error: {str(e)}")
    return None, None


def format_address(fuel_stop):
    if not fuel_stop.address:
        return ", ".join(filter(None, [fuel_stop.city, fuel_stop.state]))

    address = fuel_stop.address.split("EXIT")[0].strip()
    return ", ".join(filter(None, [address, fuel_stop.city, fuel_stop.state]))


def geocode_with_fallback(address):
    lat, lon = openroute_geocode(address)
    if lat and lon:
        return lat, lon

    location = rate_limited_geocode(nominatim, address)
    if location:
        return location.latitude, location.longitude

    return None, None


class Command(BaseCommand):
    help = "Populates latitude and longitude for fuel stops with missing data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of fuel stops to process in each batch",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]

        fuel_stops = FuelStop.objects.filter(
            latitude__isnull=True, longitude__isnull=True
        )

        if not fuel_stops.exists():
            logger.info("No fuel stops found with missing latitude and longitude.")
            return

        total_count = fuel_stops.count()
        success_count = 0

        for i in range(0, total_count, batch_size):
            batch = fuel_stops[i : i + batch_size]

            with transaction.atomic():
                for fuel_stop in batch:
                    address_str = format_address(fuel_stop)

                    lat, lng = geocode_with_fallback(address_str)

                    if lat and lng:
                        fuel_stop.latitude = lat
                        fuel_stop.longitude = lng
                        fuel_stop.save()
                        success_count += 1
                        logger.info(
                            f"Updated location for {fuel_stop.truckstop_name}: ({lat}, {lng})"
                        )
                    else:
                        logger.error(
                            f"Geocoding failed for {fuel_stop.truckstop_name} at address {address_str}"
                        )

            logger.info(f"Completed batch {(i // batch_size) + 1}")

        logger.info(
            f"Geocoding complete. Successfully updated {success_count} fuel stops."
        )
