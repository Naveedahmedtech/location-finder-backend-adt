from flask import jsonify
import requests
import math
from typing import List, Optional, Dict
from bson import ObjectId
from pymongo import ReturnDocument
from db import homepage_texts_collection, city_collection
from datetime import datetime
from pydantic import BaseModel, Field

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

def process_routes(route_info, unit_system):
    """
    Process the raw route data and convert it into a format suitable for the response.
    This function processes the distance and duration, converts them to the appropriate units,
    and formats the geometry for the response.

    :param route_info: Raw route data from the route service (OSRM or other).
    :param unit_system: The unit system for the response ('metric' or 'imperial').

    :return: List of processed routes with distance, duration, and geometry.
    """
    routes_out = []

    for r in route_info["routes"]:
        dist_m = r["distance"]  # Distance in meters
        dur_s = r["duration"]  # Duration in seconds

        # Convert distance
        dist_conv, dist_unit = convert_distance(dist_m, unit_system)

        # Convert duration to hours and minutes
        hrs = int(dur_s // 3600)
        mins = int((dur_s % 3600) // 60)

        # Add the processed route to the output list
        routes_out.append({
            "distance": dist_conv,
            "distance_unit": dist_unit,
            "duration_hours": hrs,
            "duration_minutes": mins,
            "geometry": r["geometry"]  # GeoJSON geometry
        })

    return routes_out

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

class HomepageText(BaseModel):
    language: str = Field(..., description="e.g. 'en', 'es', 'pt', 'fr'")
    headline: str
    intro_paragraph: str
    features: List[str]
    cta: str

class SingleLanguageData(BaseModel):
    headline: str
    intro_paragraph: str
    features: List[str]
    cta: str

class LanguageData(BaseModel):
    language: str
    content: SingleLanguageData

class MultiLanguageData(BaseModel):
    languages: Dict[str, SingleLanguageData]

class SingleLanguageAboutInfo(BaseModel):
    title: str
    paragraphs: List[str]

class MultiLanguageAboutInfo(BaseModel):
    languages: Dict[str, SingleLanguageAboutInfo]


def convert_object_id(doc: dict) -> dict:
    """
    Converts the _id field (if present) from ObjectId to string.
    Returns the same doc with _id as a string.
    """
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc
# CREATE
def create_homepage_text(homepage_text_data: HomepageText) -> dict:
    """
    Inserts a new document for a particular language.
    Records created_at and updated_at timestamps.
    """
    # Convert pydantic model to dict
    doc = homepage_text_data
    
    # Add timestamps
    now = datetime.utcnow()
    doc["created_at"] = now
    doc["updated_at"] = now
    
    # Insert into DB
    result = homepage_texts_collection.insert_one(doc)
    
    # Return the inserted document (with _id)
    return homepage_texts_collection.find_one({"_id": result.inserted_id})

# READ (one language)
def get_homepage_text_by_lang(language: str) -> Optional[dict]:
    """Find the homepage text document by language."""
    return homepage_texts_collection.find_one({"language": language})

# READ (all)
def get_all_homepage_texts() -> List[dict]:
    """Return all language documents."""
    return list(homepage_texts_collection.find({}))

# UPDATE
def update_homepage_text(language_code, doc_to_upsert):
    """
    Updates the existing document with the given language code.
    If the document does not exist, it creates a new one (upsert).
    
    Args:
    - language_code: The language code to identify the document.
    - doc_to_upsert: The document data to insert or update.
    
    Returns:
    - The updated or inserted document.
    """
    result = homepage_texts_collection.update_one(
        {"language": language_code},  # Find document by language
        {"$set": doc_to_upsert},  # Update the document with the new data
        upsert=True  # If no document is found, insert a new one
    )
    if result.upserted_id:  # If a new document is inserted
        return get_homepage_text_by_lang(language_code)
    else:
        return doc_to_upsert  # Return the updated data if it was updated

# DELETE
def delete_homepage_text(language: str) -> bool:
    """
    Deletes the homepage text for a given language.
    Returns True if something was deleted, otherwise False.
    """
    result = homepage_texts_collection.delete_one({"language": language})
    return result.deleted_count > 0

def get_all_homepage_texts_from_db():
    """
    Returns a list of all documents in the homepage_texts_collection.
    Each item in the returned list will be a Python dictionary, e.g.:
    [
      {
        "_id": <ObjectId>,
        "language": "en",
        "headline": "...",
        "intro_paragraph": "...",
        "features": [...],
        "cta": "..."
      },
      {
        "_id": <ObjectId>,
        "language": "es",
        "headline": "...",
        ...
      },
      ...
    ]
    """
    docs_cursor = homepage_texts_collection.find({})
    return list(docs_cursor)

def get_newest_homepage_text() -> Optional[dict]:
    """
    Returns the single newest document across all languages,
    determined by the highest (latest) updated_at.
    """
    doc = homepage_texts_collection.find_one(
        filter={}, 
        sort=[("updated_at", -1)]
    )
    return doc

def upsert_homepage_text(language: str, doc_data: dict) -> dict:
    """
    Upserts a document based on `language`.
    - If doc doesn't exist, creates it, setting created_at/updated_at.
    - If doc exists, updates it, adjusting updated_at only.
    Returns the updated (or inserted) document.
    """
    now = datetime.utcnow()
    
    # We'll set updated_at every time,
    # but created_at only if it doesn't already exist.
    update_payload = {
        "$set": doc_data,               # the fields you want to update
        "$setOnInsert": {"created_at": now},
        "$currentDate": {"updated_at": True}  # sets updated_at to current date/time
    }
    
    updated_or_inserted_doc = homepage_texts_collection.find_one_and_update(
        {"language": language},
        update_payload,
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    
    return updated_or_inserted_doc

def update_homepage_text_by_id(doc_id: str, update_data: dict) -> Optional[dict]:
    """
    Updates a document by its _id (string form).
    """
    from bson import ObjectId  # or import at the top of the file
    
    # Convert string ID to ObjectId
    try:
        object_id = ObjectId(doc_id)
    except:
        # Return None or raise an exception if doc_id is invalid
        return None

    updated_doc = homepage_texts_collection.find_one_and_update(
        {"_id": object_id},    # filter by _id
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    return updated_doc

def update_document_by_language_and_id(language: str, doc_id: str, update_data: dict
) -> dict:
    """
    Updates a document in the specified collection using the document's _id and language.
    
    Steps:
    1. Converts the provided string doc_id to a valid ObjectId.
       Raises ValueError if the format is invalid.
    2. Builds a filter that matches both _id and language.
    3. Performs a MongoDB update using the $set operator.
    4. Returns the updated document (if found), or None if no document matched.
    
    Args:
        collection (Collection): The MongoDB collection instance.
        language (str): The language field value to match.
        doc_id (str): The document ID as a string.
        update_data (dict): The fields to update.
    
    Returns:
        dict: The updated document, or None if no document was found.
    
    Raises:
        ValueError: If the doc_id is not a valid ObjectId format.
    """
    try:
        object_id = ObjectId(doc_id)
    except Exception:
        raise ValueError("Invalid ObjectId format")
    
    filter_query = {
        "_id": object_id,
        "language": language
    }
    
    updated_doc = homepage_texts_collection.find_one_and_update(
        filter_query,
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    return updated_doc

########## About us ###############

def get_city_coordinates(city_name):
    """
    Fetches coordinates of a city from MongoDB.
    :param city_name: Name of the city.
    :return: Coordinates as (latitude, longitude) or None.
    """
    record = city_collection.find_one({"type": "countries_cities"})
    if not record:
        return None

    for country in record.get("countries", []):
        for city in country.get("cities", []):
            if city["name"].lower() == city_name.lower():
                return city["latitude"], city["longitude"]

    return None

def handle_single_leg_route(origin_coords, destination_coords, origin_name, destination_name, unit_system):
    """
    Handles routing for a single leg without stops.
    """
    route_info = get_route_data(origin_coords, destination_coords)
    if not route_info or "routes" not in route_info:
        return jsonify({"error": "No routes found"}), 400

    routes_out = []
    for route in route_info["routes"]:
        dist_conv, dist_unit = convert_distance(route["distance"], unit_system)
        hrs = int(route["duration"] // 3600)
        mins = int((route["duration"] % 3600) // 60)

        routes_out.append({
            "distance": dist_conv,
            "distance_unit": dist_unit,
            "duration_hours": hrs,
            "duration_minutes": mins,
            "geometry": route["geometry"],
            "distance_summary": f"The total distance between {origin_name} and {destination_name} is {dist_conv} {dist_unit}",
            "travel_time_summary": f"The estimated travel time between {origin_name} and {destination_name} is {hrs}h {mins}m"
        })

    return jsonify({
        "origin": origin_name,
        "destination": destination_name,
        "unit_system": unit_system,
        "code": route_info.get("code", "NoCode"),
        "waypoints": route_info.get("waypoints", []),
        "routes": routes_out,
    }), 200

def handle_multi_leg_route(origin_coords, destination_coords, stops_coords, origin_name, destination_name, stops_list, unit_system):
    """
    Handles routing for multiple legs with stops.
    """
    all_coords = [origin_coords] + stops_coords + [destination_coords]
    all_names = [origin_name] + stops_list + [destination_name]

    legs_output = []
    total_distance_m = 0.0
    total_duration_s = 0.0

    for i in range(len(all_coords) - 1):
        start_coords = all_coords[i]
        end_coords = all_coords[i + 1]
        start_name = all_names[i]
        end_name = all_names[i + 1]

        leg_info = get_route_data(start_coords, end_coords)
        if not leg_info or "routes" not in leg_info:
            return jsonify({"error": f"No routes found for leg: {start_name} -> {end_name}"}), 400

        routes_array = []
        for route in leg_info["routes"]:
            dist_conv, dist_unit = convert_distance(route["distance"], unit_system)
            hrs = int(route["duration"] // 3600)
            mins = int((route["duration"] % 3600) // 60)

            routes_array.append({
                "distance": dist_conv,
                "distance_unit": dist_unit,
                "duration_hours": hrs,
                "duration_minutes": mins,
                "geometry": route["geometry"]
            })

        best_route = leg_info["routes"][0]
        total_distance_m += best_route["distance"]
        total_duration_s += best_route["duration"]

        legs_output.append({
            "from": start_name,
            "to": end_name,
            "routes": routes_array,
            "waypoints": leg_info.get("waypoints", [])
        })

    total_dist_conv, total_dist_unit = convert_distance(total_distance_m, unit_system)
    total_hrs = int(total_duration_s // 3600)
    total_mins = int((total_duration_s % 3600) // 60)

    return jsonify({
        "origin": origin_name,
        "stops": stops_list,
        "destination": destination_name,
        "unit_system": unit_system,
        "legs": legs_output,
        "total_distance": total_dist_conv,
        "total_distance_unit": total_dist_unit,
        "total_duration_hours": total_hrs,
        "total_duration_minutes": total_mins,
        "distance_summary": f"The total distance between {origin_name} and {destination_name} is {total_dist_conv} {total_dist_unit}",
        "travel_time_summary": f"The estimated travel time between {origin_name} and {destination_name} is {total_hrs}h {total_mins}m"
    }), 200

def get_city_coordinates_geonames(location_str):
    """
    Fetch coordinates from the database for a given location string (e.g., "Houston, TX").
    Returns tuple of (latitude, longitude) or None if not found.
    """
    # Parse location string
    parts = [part.strip() for part in location_str.split(",")]
    city_name = parts[0].lower()
    state = parts[1].lower() if len(parts) > 1 else None
    country = parts[2].lower() if len(parts) > 2 else None

    # Query the database
    location_data = city_collection.find_one({"type": "countries_cities"})
    if not location_data or "countries" not in location_data:
        return None

    for country_data in location_data["countries"]:
        # If country is provided, check it matches
        if country and country_data["name"].lower() != country:
            continue

        for city in country_data["cities"]:
            if city["name"].lower() == city_name:
                # If state is provided, verify it matches
                if state and "state" in city and city["state"].lower() != state:
                    continue
                return (city["latitude"], city["longitude"])
    
    return None
