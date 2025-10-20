"""MCP Server Entry Point"""

import asyncio
from .server import main as server_main


def main():
    """Main entry point for the MCP server."""
    asyncio.run(server_main())


if __name__ == "__main__":
    main()
