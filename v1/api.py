from flask import Blueprint, request, jsonify
from v1.services import geocode_address, get_air_distance, get_city_coordinates_geonames, convert_distance, estimate_flight_time, get_route_data, handle_multi_leg_route, handle_single_leg_route, haversine_distance

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
    {
      "origin": "some place",
      "stops": ["stop1", "stop2", ...],  // optional or empty
      "destination": "some other place",
      "unit_system": "metric" or "imperial", // optional, default "metric"
      "homeland": true or false  // true for DB lookup, false for geocoding
    }

    Returns:
    - Single-leg (no stops):
      {
        "origin": "New York City",
        "destination": "Boston",
        "unit_system": "imperial",
        "code": "Ok",
        "waypoints": [...],
        "routes": [
          {
            "distance": 214.32,
            "distance_unit": "miles",
            "duration_hours": 3,
            "duration_minutes": 49,
            "geometry": { "type": "LineString", "coordinates": [...] }
          },
          ...
        ]
      }
    - Multi-leg (with stops):
      {
        "origin": "Houston, TX",
        "stops": ["New Orleans, LA", "Birmingham, AL"],
        "destination": "Atlanta, GA",
        "unit_system": "imperial",
        "legs": [
          {
            "from": "Houston, TX",
            "to": "New Orleans, LA",
            "routes": [...],
            "waypoints": [...]
          },
          ...
        ],
        "total_distance": 850.06,
        "total_distance_unit": "miles",
        "total_duration_hours": 12,
        "total_duration_minutes": 45
      }
    """
    data = request.get_json() or {}
    origin_str = data.get("origin")
    stops_list = data.get("stops", [])
    destination_str = data.get("destination")
    unit_system = data.get("unit_system", "metric")
    homeland = data.get("is_db", False)  # Default to geocoding

    if not origin_str or not destination_str:
        return jsonify({"error": "origin and destination are required"}), 400

    # Get coordinates based on homeland flag
    if homeland:
        # Database lookup (MongoDB city_collection)
        origin_coords = get_city_coordinates_geonames(origin_str)
        if not origin_coords:
            return jsonify({"error": f"Origin city not found: {origin_str}"}), 400

        destination_coords = get_city_coordinates_geonames(destination_str)
        if not destination_coords:
            return jsonify({"error": f"Destination city not found: {destination_str}"}), 400

        stops_coords = []
        for s_str in stops_list:
            sc = get_city_coordinates_geonames(s_str)
            if not sc:
                return jsonify({"error": f"Stop city not found: {s_str}"}), 400
            stops_coords.append(sc)
    else:
        # Geocoding
        origin_coords = geocode_address(origin_str)
        if not origin_coords:
            return jsonify({"error": f"Unable to geocode origin: {origin_str}"}), 400

        destination_coords = geocode_address(destination_str)
        if not destination_coords:
            return jsonify({"error": f"Unable to geocode destination: {destination_str}"}), 400

        stops_coords = []
        for s_str in stops_list:
            sc = geocode_address(s_str)
            if not sc:
                return jsonify({"error": f"Unable to geocode stop: {s_str}"}), 400
            stops_coords.append(sc)

    # Single-leg logic (no stops)
    if not stops_list:
        route_info = get_route_data(origin_coords, destination_coords)
        if not route_info or "routes" not in route_info:
            return jsonify({"error": "No routes found"}), 400

        routes_out = []
        for r in route_info["routes"]:
            dist_m = r["distance"]
            dur_s = r["duration"]

            dist_conv, dist_unit = convert_distance(dist_m, unit_system)
            hrs = int(dur_s // 3600)
            mins = int((dur_s % 3600) // 60)

            routes_out.append({
                "distance": dist_conv,
                "distance_unit": dist_unit,
                "duration_hours": hrs,
                "duration_minutes": mins,
                "geometry": r["geometry"],
                "distance_summary": f"The total distance between {origin_str} and {destination_str} is {dist_conv} {dist_unit}",
                "travel_time_summary": f"The estimated travel time between {origin_str} and {destination_str} is {hrs}h {mins}m"
            })

        return jsonify({
            "origin": origin_str,
            "destination": destination_str,
            "unit_system": unit_system,
            "code": route_info.get("code", "NoCode"),
            "waypoints": route_info.get("waypoints", []),
            "routes": routes_out,
            
            
        }), 200

    # Multi-leg logic (with stops)
    all_coords = [origin_coords] + stops_coords + [destination_coords]
    all_names = [origin_str] + stops_list + [destination_str]

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
        for route_obj in leg_info["routes"]:
            dist_m = route_obj["distance"]
            dur_s = route_obj["duration"]

            dist_conv, dist_unit = convert_distance(dist_m, unit_system)
            hrs = int(dur_s // 3600)
            mins = int((dur_s % 3600) // 60)

            routes_array.append({
                "distance": dist_conv,
                "distance_unit": dist_unit,
                "duration_hours": hrs,
                "duration_minutes": mins,
                "geometry": route_obj["geometry"]
            })

        best = leg_info["routes"][0]
        total_distance_m += best["distance"]
        total_duration_s += best["duration"]

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
        "origin": origin_str,
        "stops": stops_list,
        "destination": destination_str,
        "unit_system": unit_system,
        "legs": legs_output,
        "total_distance": total_dist_conv,
        "total_distance_unit": total_dist_unit,
        "total_duration_hours": total_hrs,
        "total_duration_minutes": total_mins,"distance_summary": f"The total distance between {origin_str} and {destination_str} is {total_dist_conv} {total_dist_unit}",
        "travel_time_summary": f"The estimated travel time between {origin_str} and {destination_str} is {total_hrs}h {total_mins}m"
    }), 200
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
      "unit_system": "imperial",  // optional (default = "metric")
      "homeland": true           // true for DB lookup, false for geocoding
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
    homeland = data.get("is_db", False)  # Default to False (geocoding)

    if not origin or not destination:
        return jsonify({"error": "origin and destination are required"}), 400

    # Get coordinates based on homeland flag
    if homeland:
        # Database lookup (like API 2)
        origin_coords = get_city_coordinates_geonames(origin)
        if not origin_coords:
            return jsonify({"error": f"Origin city not found: {origin}"}), 400

        destination_coords = get_city_coordinates_geonames(destination)
        if not destination_coords:
            return jsonify({"error": f"Destination city not found: {destination}"}), 400

        # Calculate distance using Haversine formula
        distance_meters = haversine_distance(
            origin_coords[0], origin_coords[1],
            destination_coords[0], destination_coords[1]
        )
    else:
        # Geocoding (like API 1)
        air_data = get_air_distance(origin, destination)
        if air_data is None:
            return jsonify({"error": "Unable to geocode origin or destination"}), 400

        distance_meters = air_data["distance_m"]
        origin_coords = air_data["origin_coords"]  # (lat, lon)
        destination_coords = air_data["destination_coords"]  # (lat, lon)

    # Convert distance
    distance_converted, distance_label = convert_distance(distance_meters, unit_system)

    # Estimate flight time
    hours, minutes = estimate_flight_time(distance_meters, speed_kmh=900)

    # Build GeoJSON geometry (lon, lat order)
    geometry = {
        "type": "LineString",
        "coordinates": [
            [origin_coords[1], origin_coords[0]],  # [lon, lat]
            [destination_coords[1], destination_coords[0]]
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