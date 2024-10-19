Optimal Fuel Stops API
Overview
This project is a Django-based API for calculating optimal fuel stops on a route. The API fetches route data from OpenRouteService, calculates fuel stops based on a given vehicle's range, and returns a map with fuel stops and route information.

Features
Calculate optimal fuel stops along a route.
Fetch route data from OpenRouteService API.
Calculate total distance and fuel cost for a trip.
Generate a map with the route and fuel stops using Folium.
API response includes detailed route, fuel stop information, and a link to the map.
Installation
Clone the repository:

git clone https://github.com/ahmedabnaby/fueloptimizer.git
cd optimal-fuel-stops-api
Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate # For Windows: venv\Scripts\activate
Install the required packages:

pip install -r requirements.txt
Set up environment variables:

Add the following environment variables in your settings file:

OPENROUTESERVICE_API_KEY=your_openrouteservice_api_key
MEDIA_ROOT=/path/to/media/folder
MEDIA_URL=/media/

Apply migrations:

python manage.py migrate
Run the Django development server:

python manage.py runserver
API Endpoints
Optimal Fuel Stops Calculation
URL: /api/fuel-stops/
example: http://127.0.0.1:8000/api/fuel-stops/?start=47.6062,-122.3321&finish=45.5155,-122.6793
Method: GET

Parameters:

start: Starting location (latitude,longitude)
finish: Finishing location (latitude,longitude)
Response:

{
"route_data": {
"type": "FeatureCollection",
"features": [...],
"bbox": [...],
"metadata": {
"start_location": "start_location_name",
"finish_location": "finish_location_name",
"total_distance_miles": 100.5,
"total_fuel_cost": 50.25,
"fuel_stops": [
{
"truckstop_name": "Stop Name",
"latitude": 37.7749,
"longitude": -122.4194,
"retail_price": "3.50"
}
]
}
},
"map_url": "https://example.com/media/optimal_route_map.html"
}
How It Works
Input: The user provides the starting and finishing locations in latitude and longitude format.
Route Fetching: The API fetches the route data from OpenRouteService using the coordinates.
Fuel Stops Calculation: The API calculates optimal fuel stops along the route based on vehicle range and fuel efficiency.
Map Generation: A Folium map with the route and fuel stops is generated and saved in the media folder.
Response: The API returns the route details, fuel stop information, and a URL to the map.
Requirements
Django
Django REST Framework
Geopy
Folium
OpenRouteService API key
License
