#!/bin/bash

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "UV is not installed. Installing UV..."
    curl -sSf https://astral.sh/uv/install.sh | bash
    
    # Add UV to path for this session
    export PATH="$HOME/.astral/uv/bin:$PATH"
    
    echo "UV installed successfully!"
else
    echo "UV is already installed."
fi

# Install dependencies
echo "Installing dependencies with UV..."
uv pip install -e .

echo "Installation complete. You can now run the Dremio MCP server with:"
echo "mcp-dremio-server"
echo "or"
echo "python run_mcp_server.py"
