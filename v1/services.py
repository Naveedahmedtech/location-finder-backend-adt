import requests
import math

def geocode_address(address):
    """
    Use Nominatim (OpenStreetMap) to geocode the address.
    Returns (latitude, longitude) or None if not found.
    Note: Be mindful of usage policies and rate limits.
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "howmanyhours.com (your_email@example.com)"
        }
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        data = resp.json()

        if len(data) == 0:
            return None
        
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return (lat, lon)
    except:
        # Log the error in production
        return None

def get_route_data(origin_coords, destination_coords):
    """W
    Fetch route data from an OSRM server (or GraphHopper, or similar).
    Returns dictionary with distance (m), duration (s), geometry (optional).
    """
    try:
        # Example with OSRM public demo server
        # For production, consider hosting your own OSRM instance.
        base_url = "https://router.project-osrm.org/route/v1/driving"
        
        loc_string = f"{origin_coords[1]},{origin_coords[0]};{destination_coords[1]},{destination_coords[0]}"
        params = {
            "geometries": "geojson",  
            "alternatives": "true",
        }
        url = f"{base_url}/{loc_string}"
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        
        route_data = response.json()
        if not route_data.get("routes"):
            return None
        routes_out = []
        for route in route_data["routes"]:
            routes_out.append({
                "distance": route["distance"],
                "duration": route["duration"],
                "geometry": route["geometry"]
            })
        
        return {
            "code": route_data.get("code"),
            "routes": routes_out,                  
            "waypoints": route_data.get("waypoints")
        }
    
    except Exception as e:
        # Log error in production
        return None

def convert_distance(distance_meters, unit_system="metric"):
    """
    Convert distance in meters to km (metric) or miles (imperial).
    """
    if unit_system == "imperial":
        # 1 mile = 1609.34 meters
        miles = distance_meters / 1609.34
        return round(miles, 2), "miles"
    else:
        # Default: kilometers
        km = distance_meters / 1000.0
        return round(km, 2), "km"



def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Returns the great-circle distance in meters using the haversine formula.
    """
    R = 6371000  # Earth radius in meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    a = (math.sin(dlat/2)**2
         + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_air_distance(origin_str, destination_str):
    """
    Geocode origin/destination, compute the straight-line distance, 
    and return a dict containing:
      {
        "distance_m": <float>,
        "origin_coords": (lat, lon),
        "destination_coords": (lat, lon)
      }
    or None if geocoding fails.
    """
    origin_coords = geocode_address(origin_str)
    destination_coords = geocode_address(destination_str)
    
    if not origin_coords or not destination_coords:
        return None
    
    # Haversine distance in meters
    distance_m = haversine_distance(
        origin_coords[0], origin_coords[1],
        destination_coords[0], destination_coords[1]
    )
    
    return {
        "distance_m": distance_m,
        "origin_coords": origin_coords,
        "destination_coords": destination_coords
    }


def estimate_flight_time(distance_meters, speed_kmh=900):
    """
    Estimate flight time based on a constant speed in km/h.
    Returns (hours, minutes) as integers.
    """
    distance_km = distance_meters / 1000.0
    time_hours = distance_km / speed_kmh
    hours = int(time_hours)
    minutes = int((time_hours - hours) * 60)
    return hours, minutes
