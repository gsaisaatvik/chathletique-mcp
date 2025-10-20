"""Strava API integration tools for activity analysis and route planning."""

import json
import math
import os
import random
import ssl
from urllib.parse import quote_plus, urlencode

import certifi
import numpy as np
import openrouteservice
import polyline
import requests
import stravalib
from stravalib.exc import Fault
from dotenv import load_dotenv
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from pydantic import BaseModel, Field
from functools import wraps

from .mcp_utils import get_current_token

# -------------------------------- Globals --------------------------------
load_dotenv()

ors_api_key = os.getenv("ORS_KEY")
google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

# Initialize OpenRouteService client only if key is available
if ors_api_key:
    client_ors = openrouteservice.Client(key=ors_api_key)
else:
    client_ors = None

ROUTES_URL = (
    "https://routes.googleapis.com/directions/v2:computeRoutes"  # Google Map URL
)


def handle_strava_error(func):
    """Decorator to handle Strava API errors gracefully."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Fault as e:
            if "access_token" in str(e) and "invalid" in str(e):
                return f"ERROR: Strava Authentication Error: Your access token is invalid or expired.\n\n" \
                       f"To fix this:\n" \
                       f"1. Go to https://www.strava.com/settings/api\n" \
                       f"2. Get a new access token from your app\n" \
                       f"3. Update STRAVA_ACCESS_TOKEN in your servers_config.json\n" \
                       f"4. Restart the MCP server\n\n" \
                       f"The integration is working correctly - you just need a fresh token!"
            else:
                return f"ERROR: Strava API Error: {str(e)}\n\n" \
                       f"This might be a temporary issue. Try again in a few minutes."
        except Exception as e:
            return f"ERROR: Unexpected Error: {str(e)}\n\n" \
                   f"Please check your internet connection and try again."
    return wrapper


def get_strava_client():
    """Get authenticated Strava client."""
    token = get_current_token()
    if not token:
        raise Exception("No Strava access token available. Please authenticate first.")
    return stravalib.Client(access_token=token)


class Coordinates(BaseModel):
    """Geographic coordinates model.

    Attributes:
        lon: Longitude in decimal degrees.
        lat: Latitude in decimal degrees.
    """

    lon: float
    lat: float


# -------------------------------- Tools --------------------------------


@handle_strava_error
def get_user_stats() -> str:
    """Get current user's Strava statistics.

    Returns:
        str: Formatted string containing user stats including total distance,
            activity count, and performance metrics.
    """
    client_strava = get_strava_client()
    athlete_id = client_strava.get_athlete().id  # API call
    athlete_stats = client_strava.get_athlete_stats(athlete_id)
    
    # Extract actual values from the stats
    recent_totals = athlete_stats.recent_run_totals
    ytd_totals = athlete_stats.ytd_run_totals
    all_totals = athlete_stats.all_run_totals
    
    # Format the data in a clear, readable way
    result = f"""STRAVA STATISTICS:

RECENT RUNS (Last 4 weeks):
- Total Distance: {recent_totals.distance / 1000:.2f} km
- Total Runs: {recent_totals.count}
- Total Time: {recent_totals.moving_time / 3600:.2f} hours
- Elevation Gain: {recent_totals.elevation_gain:.0f} meters

YEAR TO DATE:
- Total Distance: {ytd_totals.distance / 1000:.2f} km
- Total Runs: {ytd_totals.count}
- Total Time: {ytd_totals.moving_time / 3600:.2f} hours
- Elevation Gain: {ytd_totals.elevation_gain:.0f} meters

ALL TIME:
- Total Distance: {all_totals.distance / 1000:.2f} km
- Total Runs: {all_totals.count}
- Total Time: {all_totals.moving_time / 3600:.2f} hours
- Elevation Gain: {all_totals.elevation_gain:.0f} meters

Note: These are your actual Strava statistics. If you see 0 values, it means you don't have any running activities recorded in your Strava account yet."""

    return result


@handle_strava_error
def get_last_runs(count: int = 5) -> str:
    """Get the last runs from the user's Strava account and return them in a formatted list for activity analysis
    This function will use the Strava API to get the last runs from the user's Strava account and return them in a formatted list for activity analysis
    The function will return a list of runs with the following information:
    name, distance, type, start_date_local, moving_time, average_speed, max_speed, max_heartrate, average_heartrate, total_elevation_gain, average_speed

    """
    # Get the last runs
    client_strava = get_strava_client()
    activities = client_strava.get_activities(limit=count)

    if not activities:
        return "No activities found in your Strava account. Please add some running activities to see your data here."

    result = f"LAST {count} RUNNING ACTIVITIES:\n\n"
    run_count = 0

    # Extract the data from the activities
    for activity in activities:
        if activity.type != "Run":
            continue
            
        run_count += 1
        
        # Calculate pace in min/km
        pace_min_per_km = "N/A"
        if activity.average_speed and activity.average_speed > 0:
            pace_seconds_per_km = 1000 / activity.average_speed
            pace_minutes = pace_seconds_per_km / 60
            pace_min_per_km = f"{int(pace_minutes)}:{int((pace_minutes % 1) * 60):02d}"

        result += f"RUN #{run_count}:\n"
        result += f"- Name: {activity.name}\n"
        result += f"- Date: {activity.start_date_local}\n"
        result += f"- Distance: {activity.distance / 1000:.2f} km\n"
        result += f"- Time: {activity.moving_time / 60:.0f} minutes\n"
        result += f"- Average Pace: {pace_min_per_km} min/km\n"
        result += f"- Elevation Gain: {activity.total_elevation_gain:.0f} meters\n"
        if activity.average_heartrate:
            result += f"- Average Heart Rate: {activity.average_heartrate} bpm\n"
        if activity.max_heartrate:
            result += f"- Max Heart Rate: {activity.max_heartrate} bpm\n"
        result += "\n"

    if run_count == 0:
        return f"No running activities found in your last {count} activities. Please add some running activities to see your data here."

    return result


@handle_strava_error
def create_itinerary(
    start_location: str,
    end_location: str,
    distance_km: float,
) -> str:
    """Produces an itinerary for the user

    Args :
    - start : tuple[float, float]
    - distance_km : int

    Returns :
    - gmaps_directions_link : str
    """

    def get_coordinates(place_name: str) -> tuple[float, float]:
        geolocator = Nominatim(
            user_agent="chathletique-mcp/0.1",
            timeout=10,
            ssl_context=ssl.create_default_context(cafile=certifi.where()),
        )
        try:
            loc = geolocator.geocode(place_name, language="fr")
            if loc:
                return float(loc.latitude), float(loc.longitude)
        except (GeocoderTimedOut, GeocoderServiceError):
            pass

        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "chathletique-mcp/0.1 (contact: you@example.com)"}
        params = {"q": place_name, "format": "json", "limit": 1}
        r = requests.get(
            url, headers=headers, params=params, timeout=10, verify=certifi.where()
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            raise ValueError(f"Lieu introuvable: {place_name}")
        return float(data[0]["lat"]), float(data[0]["lon"])

    def bounds_for_run(center_lat, center_lon, distance_m: int):
        """
        Return 4 bounds (SW, SE, NW, NE) :
        [min_lat, min_lon, max_lat, max_lon].
        The Global Bound is center on (center_lat, center_lon) and
        can contain a circle of radius = distance_m/2.
        """
        half = distance_m / 2.0  # half size of the squarre
        dlat = half / 111_320.0
        dlon = half / (111_320.0 * math.cos(math.radians(center_lat)))

        min_lat, max_lat = center_lat - dlat, center_lat + dlat
        min_lon, max_lon = center_lon - dlon, center_lon + dlon
        mid_lat = (min_lat + max_lat) / 2.0
        mid_lon = (min_lon + max_lon) / 2.0

        bounds = [
            [min_lat, min_lon, mid_lat, mid_lon],  # SW
            [min_lat, mid_lon, mid_lat, max_lon],  # SE
            [mid_lat, min_lon, max_lat, mid_lon],  # NW
            [mid_lat, mid_lon, max_lat, max_lon],  # NE
        ]
        return bounds

    def compute_route(
        origin, destination, waypoints=None, mode="WALK", api_key=google_api_key
    ) -> dict:
        """
        origin, destination, waypoints: (lat, lon)
        mode: "WALK" | "DRIVE" | "BICYCLE" | "TWO_WHEELER"
        Retourne dict avec distance (m), durée ISO, et polyline encodée.
        """
        if not api_key:
            raise ValueError("Google Maps API key is required for route computation. Please set GOOGLE_MAPS_API_KEY in your environment.")
            
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline",
        }

        def ll(pt):  # (lat, lon) -> payload Routes API
            return {
                "location": {
                    "latLng": {"latitude": float(pt[0]), "longitude": float(pt[1])}
                }
            }

        body = {
            "origin": ll(origin),
            "destination": ll(destination),
            "travelMode": mode.upper(),
        }
        if waypoints:
            body["intermediates"] = [ll(w) for w in waypoints]

        r = requests.post(ROUTES_URL, headers=headers, json=body, timeout=20)
        if r.status_code != 200:
            raise RuntimeError(f"Routes API {r.status_code}: {r.text}")

        route = r.json()["routes"][0]

        return {
            "distance_m": route["distanceMeters"],
            "duration_iso": route["duration"],
            "encoded_polyline": route["polyline"]["encodedPolyline"],
        }

    def get_segments(bounds):
        client_strava = get_strava_client()

        segments = client_strava.explore_segments(
            bounds=bounds, activity_type="running"
        )  # Return all the segment disponible in this bound

        list_segment = []

        for seg in segments:
            desc = {
                "id": int(seg.id),
                "name": seg.name,
                "distance_m": float(seg.distance),
                "points": polyline.decode(seg.points),
                "start_latlng": seg.start_latlng,
                "end_latlng": seg.end_latlng,
            }
            list_segment.append(desc)

        return list_segment

    def get_path_segment(segment: dict) -> list[tuple[float, float]]:
        """Get a running path from start to end, passing through segment_path."""

        length_segment = len(segment["points"])
        middle_coord_index1 = length_segment // 4
        middle_coord_index2 = 3 * length_segment // 4
        quarter_coord = segment["points"][middle_coord_index1]
        three_quarter_coord = segment["points"][middle_coord_index2]
        start_coord = (segment["start_latlng"].root[0], segment["start_latlng"].root[1])
        end_coord = (segment["end_latlng"].root[0], segment["end_latlng"].root[1])

        return [start_coord, quarter_coord, three_quarter_coord, end_coord]

    def _get_gmaps_directions_link(
        origin_coords: tuple[float, float],
        waypoints_coords_list: list[tuple[float, float]] | None = None,
    ) -> str:
        """Build a Google Maps directions URL."""
        lat0, lon0 = origin_coords
        origin = f"{lat0},{lon0}"

        if waypoints_coords_list:
            wps = [
                f"{lat},{lon}"
                for lat, lon in waypoints_coords_list
                if f"{lat},{lon}" != origin
            ]
            params = {
                "api": 1,
                "origin": origin,
                "destination": origin,
                "waypoints": "|".join(wps),
            }
            return "https://www.google.com/maps/dir/?" + urlencode(
                params, quote_via=quote_plus
            )

        # No waypoints: just point to the origin as destination
        params = {"api": 1, "destination": origin}
        return "https://www.google.com/maps/dir/?" + urlencode(
            params, quote_via=quote_plus
        )

    def create_path(list_segment, distance, start_coords):
        new_list_segment = []

        for list_seg in list_segment:
            for seg in list_seg:
                coord_seg = get_path_segment(seg)
                if (
                    distance / 3
                    < compute_route(
                        start_coords,
                        coord_seg[0],
                        coord_seg[1:-1],
                        mode="WALK",
                        api_key=google_api_key,
                    )["distance_m"]
                    < (distance) / 2
                ):
                    new_list_segment.append(seg)

        segs = new_list_segment[:]
        random.shuffle(
            segs
        )  # on choisit un ordre aléatoire pour eviter de donner le meme segment au client à chaque fois

        for seg in segs:
            pas = 0.1
            path_segment = get_path_segment(seg)
            new_waypoint = (
                path_segment[-1][0] + pas,
                path_segment[-1][1] + pas,
            )  # On choisit un point au nord est du segment
            path_segment.append(new_waypoint)
            pas = pas / 2

            for _ in range(
                10
            ):  # On effectue une dichotomie pour trouver la bonne longueur
                actual_distance = compute_route(
                    start_coords,
                    start_coords,
                    path_segment,
                    mode="WALK",
                    api_key=google_api_key,
                )["distance_m"]  # Regarde la distance totale

                if distance - 100 < actual_distance < distance + 100:
                    return start_coords, path_segment

                if actual_distance > distance:
                    new_waypoint = (new_waypoint[0] - pas, new_waypoint[1] - pas)

                elif actual_distance < distance:
                    new_waypoint = (new_waypoint[0] + pas, new_waypoint[1] + pas)

                path_segment[-1] = new_waypoint
                pas = pas / 2

        return "No segment found"

    start_coords = get_coordinates(start_location)
    distance_m = int(distance_km * 1000)
    bounds = bounds_for_run(start_coords[0], start_coords[1], distance_m)
    list_segment = []
    for bound in bounds:
        list_segment.append(get_segments(bound))
    path = create_path(list_segment, distance_m, start_coords)
    maps = _get_gmaps_directions_link(path[0], path[1])

    return maps


@handle_strava_error
def figures_speed_hr_by_activity(
    number_of_activity: int,
    resolution: str = "high",
    series_type: str = "time",
    slice_step: int = 10,
):
    """Returns a list of tuples: [(activity_name, fig_hr, fig_speed), ...]
    - fig_hr : HR curve (red) as a function of time (s)
    - fig_speed : speed curve (blue) as a function of time (s)
    Create a separate figure for each metric (no subplots).
    """
    client_strava = get_strava_client()
    activities = client_strava.get_activities(limit=number_of_activity)

    for act in activities:
        try:
            streams = client_strava.get_activity_streams(
                act.id,
                types=["time", "distance", "velocity_smooth", "heartrate"],
                resolution=resolution,
                series_type=series_type,
            )
        except Exception as e:
            print(f"Error processing activity {act.name}: {e}")
            continue

        t = np.array(streams["time"].data) if streams and "time" in streams else None
        dist = (
            np.array(streams["distance"].data)
            if streams and "distance" in streams
            else None
        )
        vel = (
            np.array(streams["velocity_smooth"].data)
            if streams and "velocity_smooth" in streams
            else None
        )
        hr = (
            np.array(streams["heartrate"].data)
            if streams and "heartrate" in streams
            else None
        )

        if (
            vel is None
            and (t is not None)
            and (dist is not None)
            and len(t) == len(dist)
            and len(t) > 1
        ):
            try:
                vel = np.gradient(dist, t)
            except Exception:
                vel = None

        speed_kmh = vel * 3.6 if vel is not None else None

        if t is not None:
            t = t[::slice_step]
        if hr is not None:
            hr = hr[::slice_step]
        if speed_kmh is not None:
            speed_kmh = speed_kmh[::slice_step]

        # Convert to lists for JSON (data stored in figures)
