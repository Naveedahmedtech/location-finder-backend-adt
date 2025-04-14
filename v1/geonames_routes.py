from flask import Blueprint, jsonify, request
from v1.geonames_services import fetch_geonames_data
from db import city_collection

# Flask Blueprint
geo_blueprint = Blueprint("geo", __name__)

@geo_blueprint.route("/adding-countries", methods=["POST"])
def fetch_and_store_geonames():
    """
    POST /geo/fetch-and-store
    Fetches data from geonamescache and stores it in MongoDB.
    """
    # Fetch data using geonamescache
    geonames_data = fetch_geonames_data()
    # Upsert operation
    result = city_collection.replace_one({"type": "countries_cities"}, geonames_data, upsert=True)
    action = "replaced" if result.modified_count > 0 else "inserted"
    return jsonify({"status":"OK", "message": f"Data {action} successfully from GeonamesCache."}), 200


@geo_blueprint.route("/listing-countries", methods=["GET"])
def get_geonames_data():
    """
    GET /geo/countries-cities
    Retrieves the stored data for countries and cities from MongoDB.
    """
    record = city_collection.find_one({"type": "countries_cities"})
    if not record:
        return jsonify({"error": "No data found."}), 404

    # Exclude MongoDB's _id field in the response
    record.pop("_id", None)
    # Extract the list of countries, ensuring _id is excluded
    countries = record.get("countries", [])
    print(countries)
    country_names = [country.get("name") for country in countries if "name" in country]
    return jsonify({"Status": "OK","countries": countries}), 200

@geo_blueprint.route("/cities-by-country", methods=["GET"])
def get_cities_by_country():
    """
    GET /geo/cities-by-country?country=CountryName
    Retrieves cities in a given country, including their latitude and longitude.
    """
    # Get the country name from query parameters
    country_name = request.args.get("country")
    if not country_name:
        return jsonify({"error": "Country name is required."}), 400

    # Fetch the record from MongoDB
    record = city_collection.find_one({"type": "countries_cities"})
    if not record:
        return jsonify({"error": "No data found in the database."}), 404

    # Search for the country
    country_data = next((c for c in record["countries"] if c["name"].lower() == country_name.lower()), None)
    if not country_data:
        return jsonify({"error": f"No data found for the country: {country_name}."}), 404

    return jsonify({
        "country": country_data["name"],
        "cities": country_data["cities"]
    }), 200