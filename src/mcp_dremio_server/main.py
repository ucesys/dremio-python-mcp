"""
Main module for the Dremio MCP server.

This module provides an implementation of the Model Context Protocol (MCP) server
for Dremio databases. It allows listing catalogs, schemas, and tables,
as well as executing SQL queries.
"""

import logging
import argparse
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP
from .resources.dremio_resource import DremioResource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_dremio_server")

# Global resource instance
dremio_resource = None


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Dremio MCP Server')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    """Manage the lifecycle of the Dremio resource."""
    global dremio_resource

    logger.info("Starting Dremio MCP server")

    try:
        # Initialize the resource
        dremio_resource = DremioResource()
        logger.info("Dremio resource initialized")

        # Wait for shutdown
        yield

    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down Dremio MCP server")


# Create FastMCP app instance
app = FastMCP("dremio", lifespan=lifespan)


@app.tool()
async def list_catalogs() -> str:
    """
    List all catalogs in Dremio.
    
    Returns:
        JSON string containing catalog information
    """
    try:
        catalogs = await dremio_resource.list_catalogs()
        return catalogs
    except Exception as e:
        logger.error(f"Error in list_catalogs tool: {e}")
        raise


@app.tool()
async def list_schemas(catalog: str) -> str:
    """
    List all schemas in a catalog.
    
    Args:
        catalog: Name of the catalog
        
    Returns:
        JSON string containing schema information
    """
    try:
        schemas = await dremio_resource.list_schemas(catalog)
        return schemas
    except Exception as e:
        logger.error(f"Error in list_schemas tool: {e}")
        raise


@app.tool()
async def list_tables(catalog: str, schema: str) -> str:
    """
    List all tables in a schema.
    
    Args:
        catalog: Name of the catalog
        schema: Name of the schema
        
    Returns:
        JSON string containing table information
    """
    try:
        tables = await dremio_resource.list_tables(catalog, schema)
        return tables
    except Exception as e:
        logger.error(f"Error in list_tables tool: {e}")
        raise


@app.tool()
async def execute_sql(sql: str) -> str:
    """
    Execute a SQL query.
    
    Args:
        sql: SQL query to execute
        
    Returns:
        JSON string containing query results
    """
    try:
        result = await dremio_resource.execute_sql(sql)
        return result
    except Exception as e:
        logger.error(f"Error in execute_sql tool: {e}")
        raise


# Register resources
@app.resource("dremio://catalogs")
async def get_catalogs() -> str:
    """
    Get a list of all catalogs.
    
    Returns:
        JSON string containing catalog information
    """
    try:
        catalogs = await dremio_resource.list_catalogs()
        return catalogs
    except Exception as e:
        logger.error(f"Error in get_catalogs resource: {e}")
        raise


@app.resource("dremio://schemas/{catalog}")
async def get_schemas(catalog: str) -> str:
    """
    Get a list of all schemas in a catalog.
    
    Args:
        catalog: Name of the catalog
        
    Returns:
        JSON string containing schema information
    """
    try:
        schemas = await dremio_resource.list_schemas(catalog)
        return schemas
    except Exception as e:
        logger.error(f"Error in get_schemas resource: {e}")
        raise


@app.resource("dremio://tables/{catalog}/{schema}")
async def get_tables(catalog: str, schema: str) -> str:
    """
    Get a list of all tables in a schema.
    
    Args:
        catalog: Name of the catalog
        schema: Name of the schema
        
    Returns:
        JSON string containing table information
    """
    try:
        tables = await dremio_resource.list_tables(catalog, schema)
        return tables
    except Exception as e:
        logger.error(f"Error in get_tables resource: {e}")
        raise


def handle_exit(signum, frame):
    """Handle exit signals."""
    logger.info(f"Received signal {signum}, shutting down")
    sys.exit(0)


def main():
    """Run the server."""
    # Parse command line arguments
    args = parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Run the server
    logger.info("Starting Dremio MCP server")
    app.run()


if __name__ == "__main__":
    main()
