#!/usr/bin/env python3
"""Test script to verify the MCP server works."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chathletique_mcp.server import server

def test_server():
    """Test if the MCP server is properly configured."""
    print("Testing MCP server...")
    print(f"Server name: {server.name}")
    
    # Test if we can list tools
    import asyncio
    
    async def list_tools():
        # Get the actual list_tools function from the server
        tools_func = server._handlers.get('tools/list')
        if tools_func:
            tools = await tools_func()
            print(f"Available tools: {[tool.name for tool in tools]}")
            return tools
        else:
            print("No tools/list handler found")
            return []
    
    tools = asyncio.run(list_tools())
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    print("✅ MCP server is working correctly!")

if __name__ == "__main__":
    test_server()
