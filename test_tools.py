#!/usr/bin/env python3
"""Test script to verify Strava tools are working."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chathletique_mcp.server import server

def test_tools():
    """Test if tools are registered."""
    print("Testing Strava MCP tools...")
    
    # Check if server is created
    print(f"MCP server: {server}")
    print(f"Server name: {server.name}")
    
    # Test individual tool functions
    try:
        from chathletique_mcp import strava_tools, weather_tools
        print("\nTesting individual tool functions...")
        
        # Test get_user_stats
        print("Testing get_user_stats...")
        result = strava_tools.get_user_stats()
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error testing tools: {e}")

if __name__ == "__main__":
    test_tools()
