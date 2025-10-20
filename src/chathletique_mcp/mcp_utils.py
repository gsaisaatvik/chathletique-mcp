"""MCP utilities for Strava coaching server."""

import os
from dotenv import load_dotenv

load_dotenv()

# For MCP stdio mode, we'll import the mcp instance from server.py
# This avoids duplicate instances and ensures compatibility


def get_current_token():
    """Get the current user's Strava access token from environment."""
    return os.getenv("STRAVA_ACCESS_TOKEN")


# OAuth functionality removed for MCP stdio integration
# We use simple token authentication via environment variables
