"""
Dremio resource for the MCP server.

This module provides a resource for interacting with Dremio using the MCP server.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.mcp_dremio_server.client.client import DremioClient

logger = logging.getLogger("mcp_dremio_server")


class DremioResource:
    """Dremio resource for the MCP server."""

    def __init__(self):
        """Initialize Dremio resource."""
        self.client = None
        self.config = self._load_config()
        self._initialize_client()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables."""
        config = {
            "dremio": {
                "type": "software",
                "software": {
                    "hostname": os.getenv("DREMIO_HOSTNAME", "localhost"),
                    "port": int(os.getenv("DREMIO_PORT", "32010")),
                    "username": os.getenv("DREMIO_USERNAME", "dremio"),
                    "password": os.getenv("DREMIO_PASSWORD", "dremio123"),
                    "use_ssl": os.getenv("DREMIO_USE_SSL", "false").lower() == "true"
                },
                "cloud": {
                    "endpoint": os.getenv("DREMIO_ENDPOINT", "data.dremio.cloud"),
                    "pat_token": os.getenv("DREMIO_PAT_TOKEN", "")
                }
            },
            "query": {
                "max_rows": int(os.getenv("DREMIO_MAX_ROWS", "10000")),
                "max_columns": int(os.getenv("DREMIO_MAX_COLUMNS", "1000")),
                "timeout": int(os.getenv("DREMIO_TIMEOUT", "300"))
            }
        }

        # If DREMIO_TYPE is set in environment, use it
        if "DREMIO_TYPE" in os.environ:
            config["dremio"]["type"] = os.environ["DREMIO_TYPE"]

        # Try to load from config.yaml if it exists
        config_paths = [
            Path("config.yaml"),
            Path("~/config.yaml").expanduser(),
            Path("/etc/mcp_dremio/config.yaml")
        ]

        for config_path in config_paths:
            if config_path.exists():
                logger.info(f"Loading configuration from {config_path}")
                try:
                    with open(config_path, 'r') as f:
                        file_config = yaml.safe_load(f)

                    # Update config with file contents
                    if file_config:
                        # If the file has the proper structure, use it directly
                        if "dremio" in file_config:
                            config.update(file_config)
                        else:
                            # Otherwise, assume it's direct dremio settings
                            if isinstance(file_config, dict):
                                config["dremio"].update(file_config)

                    logger.info("Successfully loaded configuration from file")
                    break
                except Exception as e:
                    logger.error(f"Error loading configuration from {config_path}: {e}")

        return config

    def _initialize_client(self):
        """Initialize the Dremio client."""
        try:
            self.client = DremioClient(self.config)
            logger.info("Dremio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Dremio client: {e}")
            raise

    async def list_catalogs(self) -> List[Dict[str, Any]]:
        """
        List catalogs in Dremio.
        
        Args:
        Returns:
            List of catalogs
        """
        try:
            logger.info("Listing catalogs")
            self.client.connect()
            catalogs_json = self.client.list_catalogs()
            return json.loads(catalogs_json)
        except Exception as e:
            logger.error(f"Error listing catalogs: {e}")
            raise
        finally:
            self.client.disconnect()

    async def list_schemas(self, catalog_name: str) -> List[Dict[str, Any]]:
        """
        List schemas in a catalog (catalog_name).
        
        Args:
            catalog_name: Name of the catalog
            
        Returns:
            List of schemas
        """
        try:
            logger.info(f"Listing schemas in catalog: {catalog_name}")
            self.client.connect()
            schemas_json = self.client.list_schemas(catalog_name)
            return json.loads(schemas_json)
        except Exception as e:
            logger.error(f"Error listing schemas in catalog {catalog_name}: {e}")
            raise
        finally:
            self.client.disconnect()

    async def list_tables(self, catalog_name: str, prefix: str = None, max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List tables in a schema.
        
        Args:
            catalog_name: Name of the catalog
            prefix: Schema name
            max_keys: Maximum number of tables to return (passed to query limit)
            
        Returns:
            List of tables
        """
        try:
            logger.info(f"Listing tables in catalog: {catalog_name}, schema: {prefix}")
            self.client.connect()
            tables_json = self.client.list_tables(catalog_name, prefix)

            # Parse JSON and limit results if needed
            tables = json.loads(tables_json)
            if max_keys and len(tables) > max_keys:
                tables = tables[:max_keys]

            return tables
        except Exception as e:
            logger.error(f"Error listing tables in catalog {catalog_name}, schema {prefix}: {e}")
            raise
        finally:
            self.client.disconnect()

    async def execute_sql(self, sql: str) -> Dict[str, Any]:
        """
        Execute a SQL query in Dremio.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Dict[str, Any]: Dictionary with three keys:
                - data: List of row dictionaries
                - rowCount: Number of rows returned
                - sql: The original SQL query
                
        Raises:
            ValueError: If the SQL query contains forbidden operations
            Exception: If the Dremio connection fails or the query execution fails
        """
        try:
            logger.info(f"Executing SQL query: {sql}")
            self.client.connect()

            # Execute query
            results_json = self.client.execute_query(sql)
            results = json.loads(results_json)

            # Return results with metadata
            return {
                "data": results,
                "rowCount": len(results),
                "sql": sql
            }
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            raise
        finally:
            self.client.disconnect()
