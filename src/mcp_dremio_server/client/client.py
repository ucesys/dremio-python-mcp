"""
Dremio client implementation for MCP server.

This module provides a client class for connecting to and querying Dremio
using the Arrow Flight protocol. It handles connection management, query execution,
and result transformation, while ensuring security through input validation 
and SQL injection prevention.

Features:
- Connection to both Dremio Software and Dremio Cloud
- SQL query execution with result size limits
- Schema and metadata exploration (catalogs, schemas, tables)
- SQL injection prevention through input validation

Typical usage:
    client = DremioClient(config)
    client.connect()
    result = client.execute_query("SELECT * FROM my_catalog.my_schema.my_table LIMIT 10")
    client.disconnect()
"""

import json
import re
import logging
from typing import Dict, Any, Optional
from dremio.flight.connection import DremioFlightEndpointConnection
from dremio.flight.query import DremioFlightEndpointQuery
from pyarrow._flight import FlightStreamReader

# Configure loxgging
logger = logging.getLogger("mcp_dremio_server")


class DremioClient:
    """
    Client for interacting with Dremio via Arrow Flight protocol.
    
    This class provides methods to connect to Dremio, execute queries, and explore
    metadata such as catalogs, schemas, and tables. It uses the Arrow Flight protocol
    to communicate with Dremio and handles security, connection management, and
    result transformation.
    
    Attributes:
        config (Dict[str, Any]): Configuration dictionary for the client
        dremio_config (Dict[str, Any]): Dremio-specific configuration
        query_config (Dict[str, Any]): Query-specific configuration
        conn_type (str): Connection type ('software' or 'cloud')
        _client: Arrow Flight client instance
        _endpoint: Arrow Flight endpoint instance
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Dremio client with the provided configuration.

        Args:
            config: Dictionary containing Dremio connection details
        """
        self.config = config
        self.dremio_config = config.get("dremio", {})
        self.query_config = config.get("query", {})
        self.conn_type = self.dremio_config.get("type", "software")

        self._client = None
        self._endpoint = None

    def _get_flight_args(self) -> Dict[str, Any]:
        """
        Create the arguments for the Arrow Flight client.

        Returns:
            Dictionary containing Arrow Flight connection arguments
        """
        if self.conn_type == "cloud":
            return {
                "hostname": self.dremio_config.get("cloud", {}).get("endpoint", "data.dremio.cloud"),
                "port": 443,
                "bearer_token": self.dremio_config.get("cloud", {}).get("pat_token"),
                "tls": True,
            }
        else:  # software
            software_config = self.dremio_config.get("software", {})
            return {
                "hostname": software_config.get("hostname", "localhost"),
                "port": software_config.get("port", 32010),
                "username": software_config.get("username"),
                "password": software_config.get("password"),
                "tls": software_config.get("use_ssl", False),
            }

    def connect(self) -> None:
        """
        Connect to Dremio using the Arrow Flight protocol.
        """
        if self._client is not None:
            return

        try:
            args = self._get_flight_args()
            self._endpoint = DremioFlightEndpointConnection(args)
            self._client = self._endpoint.connect()
            logger.info("Successfully connected to Dremio")
        except Exception as e:
            logger.error(f"Failed to connect to Dremio: {str(e)}")
            raise Exception(f"Failed to connect to Dremio: {str(e)}")

    def disconnect(self) -> None:
        """
        Disconnect from Dremio.
        """
        if self._client is not None:
            try:
                self._client.close()
                logger.info("Disconnected from Dremio")
            except Exception as e:
                logger.error(f"Error disconnecting from Dremio: {str(e)}")
            finally:
                self._client = None
                self._endpoint = None

    def validate_sql_query(self, sql: str) -> bool:
        """
        Validates SQL query to ensure it's read-only.

        Args:
            sql: SQL query to validate

        Returns:
            bool: True if query is read-only, False otherwise
        """
        # List of forbidden SQL keywords
        forbidden_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER',
            'CREATE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
        ]

        # Convert to uppercase for case-insensitive matching
        sql_upper = sql.upper()
        return not any(re.search(rf'\b{keyword}\b', sql_upper) for keyword in forbidden_keywords)

    def validate_identifier(self, identifier: str) -> bool:
        """
        Validates an identifier (catalog, schema, table name) to prevent SQL injection.

        Args:
            identifier: Identifier to validate

        Returns:
            bool: True if identifier is valid, False otherwise
        """
        # Allow alphanumeric characters, underscores, dots, and spaces (quoted identifiers)
        pattern = r'^[a-zA-Z0-9_\.\s]+$'
        return bool(re.match(pattern, identifier))
        
    def _escape_sql_string(self, value: str) -> str:
        """
        Escapes a string value for safe inclusion in SQL queries.
        
        This provides an additional layer of protection beyond validate_identifier().
        
        Args:
            value: String value to escape
            
        Returns:
            Escaped string safe for inclusion in SQL queries
        """
        # Replace single quotes with double single quotes (SQL standard escape for quotes)
        return value.replace("'", "''")

    def get_dremio_reader(self, sql: str) -> FlightStreamReader:
        dremio_flight_query = DremioFlightEndpointQuery(
            sql, self._client, self._endpoint
        )
        return dremio_flight_query.get_reader()

    def execute_query(self, sql: str) -> str:
        """
        Execute a SQL query and return the results as JSON.

        Args:
            sql: SQL query to execute

        Returns:
            JSON string containing query results
        """
        if not self.validate_sql_query(sql):
            raise ValueError("Query contains forbidden keywords or is not read-only")

        try:
            self.connect()

            max_rows = self.query_config.get("max_rows", 10000)

            # Execute the query and get a reader

            reader = self.get_dremio_reader(sql)

            # Read the results into a pandas DataFrame
            df = reader.read_pandas()

            # Limit the number of rows if needed
            if len(df) > max_rows:
                df = df.head(max_rows)

            # Convert to JSON
            result = df.to_json(orient="records", date_format="iso")
            return result

        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            raise Exception(f"Failed to execute query: {str(e)}")

    def list_catalogs(self) -> str:
        """
        List all catalogs in Dremio.

        Returns:
            JSON string containing catalog information
        """
        sql = "SELECT * FROM INFORMATION_SCHEMA.CATALOGS"
        return self.execute_query(sql)

    def list_schemas(self, catalog: Optional[str] = None) -> str:
        """
        List all schemas in a catalog.

        Args:
            catalog: Catalog name

        Returns:
            JSON string containing schema information
            
        Raises:
            ValueError: If the catalog name contains invalid characters
            Exception: If the query execution fails
        """
        if catalog and not self.validate_identifier(catalog):
            raise ValueError("Invalid catalog name")

        sql = "SELECT * FROM INFORMATION_SCHEMA.SCHEMATA"
        if catalog:
            sql += f" WHERE CATALOG_NAME = '{self._escape_sql_string(catalog)}'"

        return self.execute_query(sql)

    def list_tables(self, catalog: Optional[str] = None, schema: Optional[str] = None) -> str:
        """
        List all tables in a schema.

        Args:
            catalog: Catalog name
            schema: Schema name

        Returns:
            JSON string containing table information
            
        Raises:
            ValueError: If the catalog or schema name contains invalid characters
            Exception: If the query execution fails
        """
        if catalog and not self.validate_identifier(catalog):
            raise ValueError("Invalid catalog name")

        if schema and not self.validate_identifier(schema):
            raise ValueError("Invalid schema name")

        sql = 'SELECT * FROM INFORMATION_SCHEMA."TABLES"'

        where_clauses = []
        if catalog:
            where_clauses.append(f"TABLE_CATALOG = '{self._escape_sql_string(catalog)}'")
        if schema:
            where_clauses.append(f"TABLE_SCHEMA = '{self._escape_sql_string(schema)}'")

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        return self.execute_query(sql)

    def get_table_schema(self, table_name: str) -> str:
        """
        Get the schema of a table.

        Args:
            table_name: Full table name (catalog.schema.table)

        Returns:
            JSON string containing table schema information
            
        Raises:
            ValueError: If the table name contains invalid characters
            Exception: If the query execution fails
        """
        if not self.validate_identifier(table_name):
            raise ValueError("Invalid table name")

        # Use secure parameter building for SQL
        parts = table_name.split('.')
        table = parts[-1]
        
        # Base SQL with table name condition
        conditions = [f"TABLE_NAME = '{self._escape_sql_string(table)}'"]
        
        # Add schema and catalog conditions if provided
        if len(parts) > 1:
            conditions.append(f"TABLE_SCHEMA = '{self._escape_sql_string(parts[-2])}'")
        if len(parts) > 2:
            conditions.append(f"TABLE_CATALOG = '{self._escape_sql_string(parts[0])}'")
            
        # Assemble the final SQL query
        sql = f"""
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE {' AND '.join(conditions)}
        ORDER BY ORDINAL_POSITION
        """

        return self.execute_query(sql)
