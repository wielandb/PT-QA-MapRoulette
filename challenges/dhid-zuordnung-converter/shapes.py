import json
from geopy.distance import geodesic

def generate_x_geojson(lat, lon, distance=0.1, properties={}):
    # Define the directions for the cross arms
    directions = [
        (distance, distance),    # Top-right
        (-distance, -distance),  # Bottom-left
        (distance, -distance),   # Bottom-right
        (-distance, distance)    # Top-left
    ]

    # Function to calculate new lat/lon given a starting point, bearing and distance
    def calculate_offset(lat, lon, lat_offset, lon_offset):
        start = (lat, lon)
        new_point = geodesic(meters=lat_offset).destination(start, 0)  # North/South
        new_lat = new_point.latitude
        new_point = geodesic(meters=lon_offset).destination((new_lat, lon), 90)  # East/West
        new_lon = new_point.longitude
        return new_lat, new_lon

    # Generate the coordinates for the X cross
    coordinates = [
        calculate_offset(lat, lon, *directions[0]),  # Top-right
        (lat, lon),                                  # Center
        calculate_offset(lat, lon, *directions[1]),  # Bottom-left
        (lat, lon),                                  # Center
        calculate_offset(lat, lon, *directions[2]),  # Bottom-right
        (lat, lon),                                  # Center
        calculate_offset(lat, lon, *directions[3]),  # Top-left
        (lat, lon)                                   # Center
    ]

    # Create the GeoJSON structure with a single LineString
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in coordinates]
                },
                "properties": properties
            }
        ]
    }

    return geojson

