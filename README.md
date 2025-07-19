# AWS Labs RDS Management MCP Server

The official MCP Server for managing AWS RDS database resources. This server provides comprehensive tools for creating, modifying, deleting, and managing Amazon RDS database instances and clusters.

## Available Resource Templates

### DB Cluster Resources
- `aws-rds://db-cluster` - List all available Amazon RDS clusters in your account
- `aws-rds://db-cluster/{db_cluster_identifier}` - Get detailed information about a specific RDS cluster

### DB Instance Resources
- `aws-rds://db-instance` - List all available Amazon RDS instances in your account
- `aws-rds://db-instance/{db_instance_identifier}` - Get detailed information about a specific RDS instance

## Available Tools

### DB Cluster Management Tools

- CreateDBCluster - Create a new Amazon RDS database cluster
- ModifyDBCluster - Modify an existing RDS database cluster configuration
- DeleteDBCluster - Delete an RDS database cluster
- ChangeDBClusterStatus - Start, stop, or reboot a DB cluster
- FailoverDBCluster - Force a failover for an RDS database cluster
- CreateDBClusterSnapshot - Create a snapshot of a DB cluster
- DeleteDBClusterSnapshot - Delete a DB cluster snapshot
- RestoreDBClusterFromSnapshot - Restore a DB cluster from a snapshot
- RestoreDBClusterToPointInTime - Restore a DB cluster to a point in time
- DescribeDBClusters - Retrieve information about RDS database clusters

### DB Instance Management Tools

- CreateDBInstance - Create a new Amazon RDS database instance
- ModifyDBInstance - Modify an existing RDS database instance
- DeleteDBInstance - Delete an RDS database instance
- ManageDBInstanceStatus - Start, stop, or reboot a DB instance
- DescribeDBInstances - Retrieve information about RDS database instances

### Parameter Group Management Tools

- CreateDBClusterParameterGroup - Create a new custom DB cluster parameter group
- CreateDBInstanceParameterGroup - Create a new custom DB instance parameter group
- ModifyDBClusterParameterGroup - Modify parameters in a DB cluster parameter group
- ModifyDBInstanceParameterGroup - Modify parameters in a DB instance parameter group
- ResetDBClusterParameterGroup - Reset parameters in a DB cluster parameter group
- ResetDBInstanceParameterGroup - Reset parameters in a DB instance parameter group

## Instructions

The AWS RDS Management MCP Server provides comprehensive tools for managing your Amazon RDS database resources. Each tool provides specific functionality for working with RDS clusters and instances, allowing you to create, modify, delete, and control database resources.

To use these tools, ensure you have proper AWS credentials configured with appropriate permissions for RDS operations. The server will automatically use credentials from environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN) or other standard AWS credential sources.

All tools support an optional `region_name` parameter to specify which AWS region to operate in. If not provided, it will use the AWS_REGION environment variable.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to RDS services
   - Consider setting up Read-only permission if you don't want the LLM to modify any resources

## Installation

Add the MCP to your favorite agentic tools. (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.rds-management-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/rds-management",
        "run",
        "main.py"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

If you would like to prevent the MCP from taking any mutating actions (i.e. Create/Update/Delete Resource), you can specify the readonly flag as demonstrated below:

```json
{
  "mcpServers": {
    "awslabs.rds-management-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/rds-management",
        "run",
        "main.py",
        "--readonly"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration

### AWS Configuration

Configure AWS credentials and region:

```bash
# AWS settings
AWS_PROFILE=default              # AWS credential profile to use
AWS_REGION=us-east-1             # AWS region to connect to
```

The server automatically handles:
- AWS authentication and credential management
- Connection establishment and management

### Server Settings

The following CLI arguments can be passed when running the server:

```bash
# Server CLI arguments
--max-items 100                # Maximum number of items returned from API responses
--port 8888                    # Port to run the server on
--readonly                     # Whether to run in readonly mode (prevents mutating operations)
--no-readonly                  # Whether to turn off readonly mode (allow mutating operations)
--region us-east-1             # AWS region for RDS operations
--profile default              # AWS profile to use for credentials
```

## Development

### Running Tests
```bash
uv venv
source .venv/bin/activate
uv sync
uv run --frozen pytest
```

### Running the Server
```bash
uv --directory /path/to/rds-management run main.py
```

### Running in Readonly Mode
```bash
uv --directory /path/to/rds-management run main.py --readonly
```
