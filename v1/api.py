from flask import Blueprint, request, jsonify
from v1.services import get_city_coordinates_geonames, convert_distance, estimate_flight_time, handle_multi_leg_route, handle_single_leg_route, haversine_distance

api_blueprint = Blueprint("api/v1", __name__)

@api_blueprint.route("/health", methods=["GET"])
def health():
    """
    Simple health check endpoint.
    """
    return jsonify({"status": "ok"}), 200

@api_blueprint.route("/driving", methods=["POST"])
def driving():
    """
    POST /api/v1/driving
    Handles driving routes with cities matched from the database.
    Supports formats like "City", "City, State", or "City, State, Country"
    """
    data = request.get_json() or {}
    origin_name = data.get("origin")
    stops_list = data.get("stops", [])
    destination_name = data.get("destination")
    unit_system = data.get("unit_system", "metric")

    if not origin_name or not destination_name:
        return jsonify({"error": "origin and destination are required"}), 400

    # Fetch and validate cities
    origin_coords = get_city_coordinates_geonames(origin_name)
    if not origin_coords:
        return jsonify({"error": f"Origin city not found: {origin_name}"}), 400

    destination_coords = get_city_coordinates_geonames(destination_name)
    if not destination_coords:
        return jsonify({"error": f"Destination city not found: {destination_name}"}), 400

    stops_coords = []
    for stop_name in stops_list:
        stop_coords = get_city_coordinates_geonames(stop_name)
        if not stop_coords:
            return jsonify({"error": f"Stop city not found: {stop_name}"}), 400
        stops_coords.append(stop_coords)

    # Single-leg or multi-leg logic
    if not stops_list:
        return handle_single_leg_route(origin_coords, destination_coords, origin_name, destination_name, unit_system)
    else:
        return handle_multi_leg_route(
            origin_coords, destination_coords, stops_coords,
            origin_name, destination_name, stops_list, unit_system
        )

# ______________________________
########### FLIGHT ################

@api_blueprint.route("/flight", methods=["POST"])
def compute_air_distance():
    """
    POST /api/v1/flight
    Expects JSON body:
    {
      "origin": "New York City, NY",
      "destination": "Los Angeles, CA",
      "unit_system": "imperial"  // optional (default = "metric")
    }

    Returns JSON:
    {
      "origin": "New York City, NY",
      "origin_coords": [lat, lon],
      "destination": "Los Angeles, CA",
      "destination_coords": [lat, lon],
      "unit_system": "imperial",
      "distance": 2469.07,
      "distance_unit": "miles",
      "duration_hours": 4,
      "duration_minutes": 54,
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [ -74.00, 40.71 ],   // origin (lon, lat)
          [ -118.24, 34.05 ]   // destination (lon, lat)
        ]
      },
      "notes": "Estimated flight time at 900 km/h"
    }
    """
    data = request.get_json() or {}
    origin = data.get("origin")
    destination = data.get("destination")
    unit_system = data.get("unit_system", "metric")

    if not origin or not destination:
        return jsonify({"error": "origin and destination are required"}), 400

    # Get coordinates from the database
    origin_coords = get_city_coordinates_geonames(origin)
    if not origin_coords:
        return jsonify({"error": f"Origin city not found: {origin}"}), 400

    destination_coords = get_city_coordinates_geonames(destination)
    if not destination_coords:
        return jsonify({"error": f"Destination city not found: {destination}"}), 400

    # Calculate air distance using Haversine formula
    distance_meters = haversine_distance(
        origin_coords[0], origin_coords[1],  # lat, lon
        destination_coords[0], destination_coords[1]  # lat, lon
    )

    # Convert distance
    distance_converted, distance_label = convert_distance(distance_meters, unit_system)

    # Estimate flight time
    hours, minutes = estimate_flight_time(distance_meters, speed_kmh=900)

    # Build GeoJSON geometry (lon, lat order)
    geometry = {
        "type": "LineString",
        "coordinates": [
            [origin_coords[1], origin_coords[0]],  # [lon, lat]
            [destination_coords[1], destination_coords[0]]  # [lon, lat]
        ]
    }

    # Return response
    return jsonify({
        "origin": origin,
        "origin_coords": [origin_coords[0], origin_coords[1]],  # [lat, lon]
        "destination": destination,
        "destination_coords": [destination_coords[0], destination_coords[1]],  # [lat, lon]
        "unit_system": unit_system,
        "distance": distance_converted,
        "distance_unit": distance_label,
        "duration_hours": hours,
        "duration_minutes": minutes,
        "geometry": geometry,
        "distance_summary": f"The total distance between {origin} and {destination} is {distance_converted} {distance_label}",
        "travel_time_summary": f"The estimated travel time between {origin} and {destination} is {hours}h {minutes}m"
    }), 200