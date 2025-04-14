#!/usr/bin/env python3
"""
Test script to verify Dremio connection.
This script helps users test their Dremio connection without using the MCP server.
"""

import sys
import json
import yaml
import argparse
import logging
from src.mcp_dremio_server.client.client import DremioClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dremio_connection_test")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test Dremio connection')
    parser.add_argument('--config', help='Path to the configuration file')
    parser.add_argument('--connection', help='Dremio connection details as JSON string')
    args = parser.parse_args()
    return args


def load_config(args):
    """Load configuration from file or command line."""
    config = {
        "dremio": {
            "type": "software",
            "software": {},
            "cloud": {},
        },
        "query": {
            "max_rows": 10000,
            "max_columns": 1000,
            "timeout": 300
        },
        "logging": {
            "level": "INFO",
            "file": None
        }
    }
    
    logger.info("Loading configuration...")
    
    # If connection string is provided, parse it
    if args.connection:
        logger.info("Using connection string from command line")
        try:
            connection_config = json.loads(args.connection)
            
            # Check if the connection has the proper nested structure
            if "type" in connection_config:
                # Direct connection details - organize into proper structure
                conn_type = connection_config.get("type", "software")
                config["dremio"]["type"] = conn_type
                
                # Extract software/cloud specific settings
                if conn_type == "software":
                    for key in ["hostname", "port", "username", "password", "use_ssl"]:
                        if key in connection_config:
                            config["dremio"]["software"][key] = connection_config[key]
                elif conn_type == "cloud":
                    for key in ["endpoint", "pat_token"]:
                        if key in connection_config:
                            config["dremio"]["cloud"][key] = connection_config[key]
            
            elif "dremio" in connection_config:
                # Already has proper structure
                config.update(connection_config)
            
            elif "hostname" in connection_config or "endpoint" in connection_config:
                # Flat connection details - organize into proper structure
                if "endpoint" in connection_config:
                    # Cloud connection
                    config["dremio"]["type"] = "cloud"
                    for key in ["endpoint", "pat_token"]:
                        if key in connection_config:
                            config["dremio"]["cloud"][key] = connection_config[key]
                else:
                    # Software connection
                    config["dremio"]["type"] = "software"
                    for key in ["hostname", "port", "username", "password"]:
                        if key in connection_config:
                            config["dremio"]["software"][key] = connection_config[key]
                    # Handle SSL/TLS setting
                    if "use_ssl" in connection_config:
                        config["dremio"]["software"]["use_ssl"] = connection_config["use_ssl"]
                    elif "tls" in connection_config:
                        config["dremio"]["software"]["use_ssl"] = connection_config["tls"]
            
            logger.info("Successfully parsed connection JSON")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error: Connection string is not a valid JSON: {e}")
            raise Exception(f"Connection string is not a valid JSON: {e}")
    
    # If config file is provided, load it
    elif args.config:
        logger.info(f"Loading configuration from file: {args.config}")
        try:
            with open(args.config, 'r') as f:
                file_config = yaml.safe_load(f)
            
            # Update config with file contents
            if file_config:
                # If file has proper structure, use it directly
                if "dremio" in file_config:
                    config.update(file_config)
                else:
                    # Otherwise, assume it's direct dremio settings
                    config["dremio"].update(file_config)
            
            logger.info("Successfully loaded configuration from file")
        except Exception as e:
            logger.error(f"Error: Failed to load config file: {e}")
            raise Exception(f"Failed to load config file: {str(e)}")
    
    # Validate configuration
    if config["dremio"]["type"] == "software":
        if not config["dremio"]["software"]:
            # If no configuration is provided, use default values for demo
            logger.warning("No configuration found. Using default values for demo purposes.")
            config["dremio"]["software"] = {
                "hostname": "localhost",
                "port": 32010,
                "username": "dremio",
                "password": "dremio123",
                "use_ssl": False
            }
    elif config["dremio"]["type"] == "cloud":
        if not config["dremio"]["cloud"].get("endpoint") or not config["dremio"]["cloud"].get("pat_token"):
            logger.warning("Incomplete cloud configuration. Using demo values.")
            if not config["dremio"]["cloud"].get("endpoint"):
                config["dremio"]["cloud"]["endpoint"] = "data.dremio.cloud"
            if not config["dremio"]["cloud"].get("pat_token"):
                config["dremio"]["cloud"]["pat_token"] = "demo_pat_token"
    
    logger.info(f"Configuration loaded with structure: dremio.{config['dremio']['type']}")
    return config


def main():
    """Main function to test Dremio connection."""
    try:
        args = parse_args()
        config = load_config(args)

        logger.info("Testing connection to Dremio...")
        
        # Display connection details based on connection type
        if config["dremio"]["type"] == "software":
            software_config = config["dremio"]["software"]
            logger.info(f"Connection type: Dremio Software")
            logger.info(f"Connection details: {software_config.get('hostname')}:{software_config.get('port')}")
            logger.info(f"Authentication: Username = {software_config.get('username')}")
            logger.info(f"SSL Enabled: {software_config.get('use_ssl', False)}")
        else:
            cloud_config = config["dremio"]["cloud"]
            logger.info(f"Connection type: Dremio Cloud")
            logger.info(f"Endpoint: {cloud_config.get('endpoint')}")
            logger.info(f"Authentication: Personal Access Token")

        # Create client
        client = DremioClient(config)
        logger.info("Client created successfully, connecting...")

        # Test connection by listing catalogs
        catalogs_json = client.list_catalogs()
        catalogs = json.loads(catalogs_json)

        logger.info(f"Connection successful! Found {len(catalogs)} catalogs:")
        for catalog in catalogs:
            catalog_name = catalog.get("CATALOG_NAME", "")
            if catalog_name:
                logger.info(f"  - {catalog_name}")

                # Try listing schemas for each catalog
                try:
                    schemas_json = client.list_schemas(catalog_name)
                    schemas = json.loads(schemas_json)
                    logger.info(f"    Found {len(schemas)} schemas")

                    # Print first few schemas
                    for i, schema in enumerate(schemas[:3]):
                        schema_name = schema.get("SCHEMA_NAME", "")
                        if schema_name:
                            logger.info(f"      - {schema_name}")

                    if len(schemas) > 3:
                        logger.info(f"      ... and {len(schemas) - 3} more")

                except Exception as e:
                    logger.error(f"Error listing schemas for catalog {catalog_name}: {e}")

        logger.info("Connection test completed successfully!")

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
