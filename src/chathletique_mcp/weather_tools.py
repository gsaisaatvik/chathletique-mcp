"""Weather API integration tools for running conditions forecast."""

import os

import requests
from dotenv import load_dotenv
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

# No longer using FastMCP decorators

# -------------------------------- Globals --------------------------------
load_dotenv()
token = os.getenv("WEATHER_API_KEY")
if not token:
    print("Warning: WEATHER_API_KEY not found in .env file. Weather tools will not work.")


# -------------------------------- Tools --------------------------------
def get_weather_prediction(place_name: str) -> str:
    """Loads positions from run_positions.txt and returns weather forecast as a dict."""
    if not token:
        return "Error: Weather API key not configured. Please set WEATHER_API_KEY in your environment."
        
    base_url = "http://api.openweathermap.org/data/2.5/forecast"

    longitude, latitude = _get_coordinates(place_name)
    params = {
        "lat": longitude,
        "lon": latitude,
        "appid": token,
        "exclude": "current,minutely,alerts",
    }

    response = requests.get(base_url, params=params, timeout=10)
    response = filter_weather_data(response.json())  # filter out to keep relevant data
    return str(response)


# -------------------------------- Useful functions --------------------------------
# get the coordinates of a place name
def _get_coordinates(place_name: str) -> tuple:
    """Get the coordinates of a place name"""
    geolocator = Nominatim(user_agent="my_geocoder_app")
    try:
        location = geolocator.geocode(place_name)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print("Error:", e)
        return "Failed to get coordinates"
    if location:
        return (location.longitude, location.latitude)
    else:
        return "Failed to get coordinates"


# Keep only the relevant fields from the weather data
def filter_weather_data(data):
    """Simplify OpenWeatherMap 5-day/3-hour forecast data, keeping:
    - temp
    - feels_like
    - humidity
    - weather (main + description)
    - wind (speed, deg, gust)
    - pop
    - rain (3h if available, else 0)
    - dt
    - sunrise and sunset (datetime in local time)
    """
    city_info = data.get("city", {})
    timezone_offset = city_info.get("timezone", 0)  # in seconds
    sunrise_utc = city_info.get("sunrise")
    sunset_utc = city_info.get("sunset")
    name = city_info.get("name")

    simplified = [
        {
            "sunrise": sunrise_utc,
            "sunset": sunset_utc,
            "timezone": timezone_offset,
            "name": name,
        }
    ]

    for entry in data.get("list", []):
        main = entry.get("main", {})
        weather = entry.get("weather", [{}])[0]  # usually one element
        wind = entry.get("wind", {})
        rain = entry.get("rain", {}).get("3h", 0)  # default to 0 if missing

        simplified.append(
            {
                "temp": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "humidity": main.get("humidity"),
                "weather": {
                    "main": weather.get("main"),
                    "description": weather.get("description"),
                },
                "wind": {
                    "speed": wind.get("speed"),
                    "deg": wind.get("deg"),
                    "gust": wind.get("gust"),
                },
                "pop": entry.get("pop"),
                "rain": rain,
                "dt": entry.get("dt"),
            }
        )

    return simplified
