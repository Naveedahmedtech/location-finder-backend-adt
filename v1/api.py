from flask import Blueprint, request, jsonify
from v1.services import geocode_address, get_route_data, convert_distance, get_air_distance, estimate_flight_time

api_blueprint = Blueprint("api_v1", __name__)

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
      "stops": ["stop1", "stop2", ...]  // optional or empty
      "destination": "some other place",
      "unit_system": "metric" or "imperial" // optional, default "metric"
    }

    1) If `stops` is empty (or not present):
       - Single-leg logic. Calls get_route_data(origin, destination).
       - Returns ALL alternative routes in "routes".
       - Also includes total_distance/time from the first route.

    2) If `stops` is non-empty:
       - Multi-leg logic. For each leg, calls get_route_data(...), storing the first route
         in each leg for total_distance/time, while returning all routes in a "routes" array.
    """
    data = request.get_json() or {}
    origin_str = data.get("origin")
    stops_list = data.get("stops", [])
    destination_str = data.get("destination")
    unit_system = data.get("unit_system", "metric")

    # Validate
    if not origin_str or not destination_str:
        return jsonify({"error": "origin and destination are required"}), 400

    # 1. Geocode origin & destination
    origin_coords = geocode_address(origin_str)
    if not origin_coords:
        return jsonify({"error": f"Unable to geocode origin: {origin_str}"}), 400

    destination_coords = geocode_address(destination_str)
    if not destination_coords:
        return jsonify({"error": f"Unable to geocode destination: {destination_str}"}), 400

    # --------------------------------------------------------------------------------------
    # CASE A: NO STOPS -> SINGLE LEG WITH ALTERNATIVES
    # --------------------------------------------------------------------------------------
    if not stops_list:
        route_info = get_route_data(origin_coords, destination_coords)
        if not route_info or "routes" not in route_info:
            return jsonify({"error": "No routes found"}), 400

        # Parse all routes from route_info
        routes_out = []
        for r in route_info["routes"]:
            dist_m = r["distance"]
            dur_s  = r["duration"]

            dist_conv, dist_unit = convert_distance(dist_m, unit_system)
            hrs = int(dur_s // 3600)
            mins = int((dur_s % 3600) // 60)

            routes_out.append({
                "distance": dist_conv,
                "distance_unit": dist_unit,
                "duration_hours": hrs,
                "duration_minutes": mins,
                "geometry": r["geometry"]
            })

        # Also produce total distance/time from the FIRST (best) route
        best_route = route_info["routes"][0]
        best_dist_m = best_route["distance"]
        best_dur_s  = best_route["duration"]

        best_dist_conv, best_dist_unit = convert_distance(best_dist_m, unit_system)
        best_hrs = int(best_dur_s // 3600)
        best_mins = int((best_dur_s % 3600) // 60)

        return jsonify({
            "origin": origin_str,
            "destination": destination_str,
            "unit_system": unit_system,
            "code": route_info.get("code", "NoCode"),
            "waypoints": route_info.get("waypoints", []),
            "routes": routes_out,

            # single-leg total (from first route)
            "total_distance": best_dist_conv,
            "total_distance_unit": best_dist_unit,
            "total_duration_hours": best_hrs,
            "total_duration_minutes": best_mins
        }), 200

    # Else => MULTI-LEG logic with stops
    # 1. Geocode each stop
    stops_coords = []
    for s_str in stops_list:
        sc = geocode_address(s_str)
        if not sc:
            return jsonify({"error": f"Unable to geocode stop: {s_str}"}), 400
        stops_coords.append(sc)

    # 2. Build the coordinate list
    all_coords = [origin_coords] + stops_coords + [destination_coords]
    all_names = [origin_str] + stops_list + [destination_str]

    legs_output = []
    total_distance_m = 0.0
    total_duration_s = 0.0

    # 3. For each leg, get routes from OSRM (alternatives=true)
    #    Summation is from the first (best) route
    for i in range(len(all_coords) - 1):
        start_coords = all_coords[i]
        end_coords   = all_coords[i+1]
        start_name   = all_names[i]
        end_name     = all_names[i+1]

        leg_info = get_route_data(start_coords, end_coords)
        if not leg_info or "routes" not in leg_info:
            return jsonify({"error": f"No routes found for leg: {start_name} -> {end_name}"}), 400

        # Build "routes": an array of alternatives
        routes_array = []
        for route_obj in leg_info["routes"]:
            dist_m = route_obj["distance"]
            dur_s  = route_obj["duration"]

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

        # The first route is the best route for total distance/duration
        best = leg_info["routes"][0]
        total_distance_m += best["distance"]
        total_duration_s += best["duration"]

        # Add the leg object
        legs_output.append({
            "from": start_name,
            "to": end_name,
            "routes": routes_array,
            "waypoints": leg_info.get("waypoints", [])
        })

    # 4. Summaries
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
        "total_duration_minutes": total_mins
    }), 200


# ______________________________
########### FLIGHT ################


@api_blueprint.route("/flight", methods=["POST"])
def compute_air_distance():
    """
    POST /api/v1/air-distance
    Expects JSON body:
    {
      "origin": "New York City",
      "destination": "Los Angeles",
      "unit_system": "imperial"  // optional (default = "metric")
    }

    Returns JSON:
    {
      "origin": "New York City",
      "origin_coords": [lat, lon],
      "destination": "Los Angeles",
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
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    origin = data.get("origin")
    destination = data.get("destination")
    unit_system = data.get("unit_system", "metric")

    if not origin or not destination:
        return jsonify({"error": "origin and destination are required"}), 400

    # 1. Get air distance + coords
    air_data = get_air_distance(origin, destination)
    if air_data is None:
        return jsonify({"error": "Unable to geocode origin or destination"}), 400

    distance_meters = air_data["distance_m"]
    origin_coords = air_data["origin_coords"]         # (lat, lon)
    destination_coords = air_data["destination_coords"] # (lat, lon)

    # 2. Convert distance
    distance_converted, distance_label = convert_distance(distance_meters, unit_system)

    # 3. Estimate flight time
    hours, minutes = estimate_flight_time(distance_meters, speed_kmh=900)

    # 4. Build a simple geometry for the line
    # Note that GeoJSON is usually [lon, lat], so we swap the tuple.
    geometry = {
        "type": "LineString",
        "coordinates": [
            [origin_coords[1], origin_coords[0]],      # [lon, lat]
            [destination_coords[1], destination_coords[0]]
        ]
    }

    # 5. Return everything as JSON
    return jsonify({
        "origin": origin,
        "origin_coords": [origin_coords[0], origin_coords[1]],  # lat, lon
        "destination": destination,
        "destination_coords": [destination_coords[0], destination_coords[1]],  # lat, lon
        "unit_system": unit_system,
        "distance": distance_converted,
        "distance_unit": distance_label,
        "duration_hours": hours,
        "duration_minutes": minutes,
        "geometry": geometry,
        "notes": "Estimated flight time at 900 km/h"
    }), 200
