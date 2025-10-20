#!/usr/bin/env python3
"""Simple working MCP server for testing."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create MCP server instance
server = Server("chathletique-mcp")

@server.list_tools()
async def list_tools():
    """List available tools."""
    return [
        Tool(
            name="get_user_stats",
            description="Get user's Strava statistics including total distance, run count, and average pace.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_last_runs",
            description="Get details of the user's last few runs including distance, time, and pace.",
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
async def call_tool(name: str, arguments: dict):
    """Call a tool by name with given arguments."""
    try:
        if name == "get_user_stats":
            # Import and call the actual function
            from chathletique_mcp import strava_tools
            result = strava_tools.get_user_stats()
        elif name == "get_last_runs":
            from chathletique_mcp import strava_tools
            count = arguments.get("count", 5)
            result = strava_tools.get_last_runs(count)
        elif name == "get_weather_prediction":
            from chathletique_mcp import weather_tools
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
