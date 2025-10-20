# Helper file: copy the text below into a .env file at the project root

ENV_DOTENV_CONTENT = """
# Chathletique-MCP configuration

# Strava API Configuration (updated to match your working app)
STRAVA_CLIENT_ID=181771
# Paste exact values from your Strava dashboard below:
STRAVA_CLIENT_SECRET=
STRAVA_ACCESS_TOKEN=
REFRESH_TOKEN=
SILENCE_TOKEN_WARNINGS=true

# Weather API Configuration (optional unless using weather tools)
WEATHER_API_KEY=

# OpenRouteService API Configuration (optional unless using itinerary)
ORS_KEY=

# Google Maps API Configuration (optional, for route planning)
GOOGLE_MAPS_API_KEY=
"""

if __name__ == "__main__":
    print(ENV_DOTENV_CONTENT)
