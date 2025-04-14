from geonamescache import GeonamesCache

def get_countries():
    """Returns a list of country names."""
    gc = GeonamesCache()
    countries = gc.get_countries()
    return [{"code": code, "name": details["name"]} for code, details in countries.items()]

def get_cities_by_country(country_name):
    """
    Returns a list of city names and coordinates for a given country.
    
    :param country_name: The name of the country.
    :return: A list of cities with names and coordinates.
    """
    gc = GeonamesCache()
    countries = gc.get_countries()
    cities = gc.get_cities()

    # Match the country name to its code
    country_code = None
    for code, details in countries.items():
        if details["name"].lower() == country_name.lower():
            country_code = code
            break

    if not country_code:
        return {"error": f"Country '{country_name}' not found."}, 404

    # Filter cities for the matched country code
    city_list = []
    for city_details in cities.values():
        if city_details["countrycode"] == country_code:
            city_list.append({
                "name": city_details["name"],
                "latitude": city_details["latitude"],
                "longitude": city_details["longitude"],
            })

    return {"cities": city_list}, 200


def fetch_geonames_data():
    """
    Fetch countries and cities from geonamescache and structure the data.
    Returns:
        dict: Structured data for MongoDB.
    """
    gc = GeonamesCache()

    countries = gc.get_countries()
    cities = gc.get_cities()

    structured_data = {"type": "countries_cities", "countries": []}

    for country_code, country_info in countries.items():
        country_name = country_info["name"]
        country_cities = [
            {"name": city_info["name"], "latitude": city_info["latitude"], "longitude": city_info["longitude"]}
            for city_code, city_info in cities.items()
            if city_info["countrycode"] == country_code
        ]
        structured_data["countries"].append({"name": country_name, "cities": country_cities})

    return structured_data

