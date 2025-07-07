# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common MCP server configuration."""

from mcp.server.fastmcp import FastMCP

SERVER_VERSION = '0.1.0'

SERVER_INSTRUCTIONS = """
This server provides management capabilities for Amazon RDS database clusters including Aurora, MySQL, PostgreSQL, MariaDB, Oracle, and SQL Server.

Key capabilities:
- Cluster Management: Create, modify, delete, start, stop, reboot, and failover DB clusters
- Instance Management: Create, modify, delete, start, stop, and reboot DB instances
- Parameter Management: Create, modify, and reset parameter groups
- Backup Management: Create, delete, and restore snapshots
- Information Access: View detailed information about clusters, instances, and configurations

The server operates in read-only mode by default for safety. Write operations require explicit configuration.

Always verify resource identifiers and understand the impact of operations before executing them.
"""

SERVER_DEPENDENCIES = ['boto3', 'botocore', 'pydantic', 'loguru', 'mypy-boto3-rds']

# FastMCP instance
mcp = FastMCP(
    'awslabs.rds-management-mcp-server',
    version=SERVER_VERSION,
    instructions=SERVER_INSTRUCTIONS,
    dependencies=SERVER_DEPENDENCIES,
)
