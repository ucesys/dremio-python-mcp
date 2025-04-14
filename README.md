# Dremio Model-Context Protocol (MCP)

This project implements a Model-Context Protocol (MCP) server for Dremio. It provides a standardized way to interact with Dremio databases through the MCP.

## Features

### Resources

Exposes Dremio data through **Resources**:

* `dremio://catalogs` - Lists all catalogs
* `dremio://schemas/{catalog}` - Lists all schemas in a catalog
* `dremio://tables/{catalog}/{schema}` - Lists all tables in a schema
* `dremio://schema/{table_name}` - Gets schema information for a table

### Tools

* **list_catalogs**
  * Lists all available catalogs in Dremio
  * Usage: `list_catalogs()`

* **list_schemas**
  * Lists all schemas in a specific catalog
  * Usage: `list_schemas("catalog_name")`

* **list_tables**
  * Lists all tables in a specific schema
  * Usage: `list_tables("catalog_name", "schema_name")`

* **create_select_statement**
  * Generates a SELECT statement for a specific table
  * Includes all columns with proper quoting
  * Usage: `create_select_statement("catalog.schema.table")`

* **execute_sql**
  * Executes a SQL query against Dremio
  * Returns results in a structured format with metadata
  * Usage: `execute_sql("SELECT * FROM catalog.schema.table LIMIT 10")`

## Requirements

* Python 3.10+
* Dremio instance (Cloud or Software)
* PyArrow with Flight support

## Installation

### Using pip

```bash
pip install -e .
```

### Using uv (recommended)

```bash
# Install uv if you don't have it
curl -sSf https://astral.sh/uv/install.sh | bash

# Install the package
uv pip install -e .
```

## Configuration

Create a `config.yaml` file in the root directory with the following configuration:

```yaml
# Dremio connection settings
dremio:
  # Connection type: 'software' for Dremio Software or 'cloud' for Dremio Cloud
  type: software

  # Dremio Software connection details
  software:
    hostname: localhost
    port: 32010
    username: your_username
    password: your_password
    use_ssl: false

# Query settings
query:
  # Maximum number of rows to return in a query result
  max_rows: 10000
  # Maximum number of columns to return in schema request
  max_columns: 1000
  # Timeout in seconds for query execution
  timeout: 300
```

### Environment Variables

You can also configure the server using environment variables:

```
DREMIO_HOSTNAME=localhost
DREMIO_PORT=32010
DREMIO_USERNAME=your_username
DREMIO_PASSWORD=your_password
DREMIO_USE_SSL=false
```

For Dremio Cloud:

```
DREMIO_TYPE=cloud
DREMIO_ENDPOINT=data.dremio.cloud
DREMIO_PAT_TOKEN=your_personal_access_token
```

## Usage

### Running the Server

```bash
# If installed from package
mcp-dremio-server

# Or run directly
python run_mcp_server.py
```

### Integration with Claude or Other MCP Clients

Add the following configuration to your MCP client settings:

#### MacOS
```json
// ~/Library/Application\ Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "dremio_service": {
      "command": "/Users/USERNAME/.local/bin/uv",
      "args": [
                "--directory",
                "/Users/USERNAME/PycharmProjects/dremio-python-mcp",
                "run",
                "run_mcp_server.py"
            ]
    }
  }
}
```

#### Windows
```json
// %APPDATA%/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "dremio-mcp": {
      "command": "mcp-dremio-server",
      "args": []
    }
  }
}
```

## Example Usage

### Listing Catalogs and Schemas

```
// List all catalogs
list_catalogs()

// List schemas in a catalog
list_schemas("my_catalog")

// List tables in a schema
list_tables("my_catalog", "my_schema")
```

### Creating and Executing SQL Queries

```
// Generate a SELECT statement for a table
select_statement = create_select_statement("my_catalog.my_schema.my_table")
print(select_statement["sql"])

// Execute a query
results = execute_sql("SELECT * FROM my_catalog.my_schema.my_table LIMIT 10")
```

## Security Features

* **SQL Validation**: Prevents execution of non-read-only queries
* **Input Validation**: Prevents SQL injection via table/schema names
* **TLS Support**: Secure communication with Dremio
* **Authentication**: Support for username/password and token authentication

## Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging experience, use the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector mcp-dremio-server
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
