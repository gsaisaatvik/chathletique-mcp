"""MCP stdio server entry point for Strava Coach.

This module provides an MCP-compatible stdio interface for the Strava coaching tools.
It's designed to be used by the MCP API server (mcp_api_server.py) via stdio transport.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create MCP server instance
server = Server("strava-coach")

# Import tools to register them
from . import strava_tools, weather_tools

# Register tools manually
@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_user_stats",
            description="Get user's Strava statistics including total distance, run count, and average pace. Use this when user asks for 'stats', 'statistics', 'totals', or 'summary' of their Strava data.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_last_runs",
            description="Get details of the user's last few runs including distance, time, and pace. Use this when user asks for 'recent runs', 'last runs', 'activities', or 'running history'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of recent runs to retrieve (default: 5)",
                        "default": 5
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="create_itinerary",
            description="Create a running itinerary with route planning and weather information",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_location": {
                        "type": "string",
                        "description": "Starting location for the run"
                    },
                    "end_location": {
                        "type": "string", 
                        "description": "Ending location for the run"
                    },
                    "distance_km": {
                        "type": "number",
                        "description": "Desired distance in kilometers"
                    }
                },
                "required": ["start_location", "end_location", "distance_km"]
            }
        ),
        Tool(
            name="get_weather_prediction",
            description="Get weather forecast for a specific location",
            inputSchema={
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Name of the place to get weather for"
                    }
                },
                "required": ["place_name"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Call a tool by name with given arguments."""
    try:
        if name == "get_user_stats":
            result = strava_tools.get_user_stats()
        elif name == "get_last_runs":
            count = arguments.get("count", 5)
            result = strava_tools.get_last_runs(count)
        elif name == "create_itinerary":
            result = strava_tools.create_itinerary(
                arguments["start_location"],
                arguments["end_location"], 
                arguments["distance_km"]
            )
        elif name == "get_weather_prediction":
            result = weather_tools.get_weather_prediction(arguments["place_name"])
        else:
            result = f"Unknown tool: {name}"
            
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

