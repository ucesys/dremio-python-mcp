#!/usr/bin/env python3
"""
Run the Dremio MCP server.

This script provides a simple way to run the Dremio MCP server.
"""

import sys
from src.mcp_dremio_server.main import main

if __name__ == "__main__":
    sys.exit(main())
