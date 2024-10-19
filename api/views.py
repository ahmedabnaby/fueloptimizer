import os
from requests.exceptions import RequestException
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FuelStop
from .serializers import FuelStopSerializer
import geopy.distance
import requests
import folium
from math import radians, cos, sin, sqrt, atan2
from geopy.geocoders import Nominatim

# Initialize the geocoder
geolocator = Nominatim(user_agent="fuel_optimizer")


class OptimalFuelStopsAPIView(APIView):
    """
    API view for calculating optimal fuel stops on a route.
    """

    def get(self, request):
        """
        Handle GET requests to calculate optimal fuel stops.

        Parameters:
        - start: Starting location (query parameter)
        - finish: Finishing location (query parameter)

        Returns:
        - JSON response with route data, fuel stops, and a map URL
        """
        start_location = request.query_params.get("start")
        finish_location = request.query_params.get("finish")

        # Validate input parameters
        if not start_location or not finish_location:
            return Response(
                {"error": "Both start and finish locations are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the route data
            route = self.get_route(start_location, finish_location)
        except RequestException:
            return Response(
                {"error": "Network error when fetching route data."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            # Calculate total distance of the route
            total_distance = self.get_total_distance(route)
        except KeyError:
            return Response(
                {"error": "Invalid route data structure."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Calculate optimal fuel stops and total fuel cost
            optimal_fuel_stops, total_fuel_cost = self.calculate_optimal_fuel_stops(
                route, total_distance
            )
        except Exception:
            return Response(
                {"error": "Error calculating fuel stops."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Create and save the route map
        map_url = self.create_route_map_and_save(request, route, optimal_fuel_stops)

        # Prepare and return the response
        return Response(
            {
                "route_data": {
                    "type": "FeatureCollection",
                    "features": route["features"],
                    "bbox": route["bbox"],
                    "metadata": {
                        "start_location": start_location,
                        "finish_location": finish_location,
                        "total_distance_miles": total_distance,
                        "total_fuel_cost": total_fuel_cost,
                        "fuel_stops": optimal_fuel_stops,
                    },
                },
                "map_url": map_url,
            },
            status=status.HTTP_200_OK,
        )

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points on the earth.

        Uses the Haversine formula.
        """
        R = 3956.0  # Radius of the Earth in miles
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def get_route(self, start_location, finish_location):
        """
        Fetch route data from OpenRouteService API.
        """
        start_coords = ",".join(start_location.split(",")[::-1])
        end_coords = ",".join(finish_location.split(",")[::-1])

        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": settings.OPENROUTESERVICE_API_KEY}
        params = {"start": start_coords, "end": end_coords}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        return response.json()

    def get_total_distance(self, route):
        """
        Extract the total distance of the route in miles from the route data.
        """
        return route["features"][0]["properties"]["segments"][0]["distance"] / 1609.34

    def calculate_optimal_fuel_stops(self, route, total_distance):
        """
        Calculate optimal fuel stops along the route.

        Returns:
        - List of optimal fuel stops
        - Total fuel cost for the journey
        """
        vehicle_range = 500  # Vehicle range in miles
        mpg = 10  # Miles per gallon
        fuel_stops = []
        total_fuel_cost = 0
        current_fuel_range = vehicle_range
        remaining_distance = total_distance

        coordinates = route["features"][0]["geometry"]["coordinates"]

        for i, coord in enumerate(coordinates):
            longitude, latitude = coord
            step_distance = (
                0
                if i == 0
                else self.get_distance_between_coords(coord, coordinates[i - 1])
            )

            remaining_distance -= step_distance
            current_fuel_range -= step_distance

            if current_fuel_range <= 0:
                closest_fuel_stop = self.get_closest_fuel_stop((latitude, longitude))
                if closest_fuel_stop:
                    fuel_stops.append(FuelStopSerializer(closest_fuel_stop).data)
                    fuel_needed = (vehicle_range - current_fuel_range) / mpg
                    total_fuel_cost += (
                        float(closest_fuel_stop.retail_price) * fuel_needed
                    )
                    current_fuel_range = vehicle_range

        return fuel_stops, total_fuel_cost

    def get_distance_between_coords(self, coord1, coord2):
        """
        Calculate the distance between two coordinates using geopy.
        """
        return geopy.distance.distance(
            (coord1[1], coord1[0]), (coord2[1], coord2[0])
        ).miles

    def get_closest_fuel_stop(self, location):
        """
        Find the closest fuel stop to a given location.
        """
        fuel_stops = FuelStop.objects.exclude(
            latitude__isnull=True, longitude__isnull=True
        )
        closest_fuel_stop = min(
            fuel_stops,
            key=lambda stop: geopy.distance.distance(
                location, (stop.latitude, stop.longitude)
            ).miles,
            default=None,
        )
        return closest_fuel_stop

    def create_route_map_and_save(self, request, route, fuel_stops):
        """
        Create a Folium map with the route and fuel stops, then save it.

        Returns:
        - URL of the saved map
        """
        start_coords = route["features"][0]["geometry"]["coordinates"][0][::-1]
        route_map = folium.Map(location=start_coords, zoom_start=6)

        # Add the route to the map
        route_coords = [
            coord[::-1] for coord in route["features"][0]["geometry"]["coordinates"]
        ]
        folium.PolyLine(route_coords, color="blue", weight=5).add_to(route_map)

        # Add fuel stop markers to the map
        for stop in fuel_stops:
            if stop["latitude"] and stop["longitude"]:
                folium.Marker(
                    [stop["latitude"], stop["longitude"]],
                    popup=f"{stop['truckstop_name']} - ${stop['retail_price']}/gallon",
                    icon=folium.Icon(color="green"),
                ).add_to(route_map)

        # Save the map
        media_root = settings.MEDIA_ROOT
        map_filename = "optimal_route_map.html"
        map_path = os.path.join(media_root, map_filename)
        os.makedirs(media_root, exist_ok=True)
        route_map.save(map_path)

        # Return the URL of the saved map
        return request.build_absolute_uri(settings.MEDIA_URL + map_filename)
