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

"""AWS Labs RDS Management MCP Server implementation for Amazon RDS databases."""

import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

# modules
from . import cluster
from .constants import MCP_SERVER_VERSION
from .resources import (
    get_cluster_detail_resource,
    get_cluster_list_resource,
)

logger.remove()
logger.add(sys.stderr, level='INFO')

# global variables
_rds_client = None
_readonly = True
_region = None


def get_rds_client():
    """Get or create RDS client."""
    global _rds_client, _region
    if _rds_client is None:
        config = Config(
            region_name=_region,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
        )
        _rds_client = boto3.client('rds', config=config)
    return _rds_client


mcp = FastMCP(
    'awslabs.rds-management-mcp-server',
    version=MCP_SERVER_VERSION,
    instructions="""This server provides management capabilities for Amazon RDS database clusters including Aurora, MySQL, PostgreSQL, MariaDB, Oracle, and SQL Server.

Key capabilities:
- Cluster Management: Create, modify, delete, start, stop, reboot, and failover DB clusters
- Cluster Information: View detailed information about clusters and their configuration

The server operates in read-only mode by default for safety. Write operations require explicit configuration.

Always verify resource identifiers and understand the impact of operations before executing them.""",
    dependencies=['boto3', 'botocore', 'pydantic', 'loguru'],
)


# ===== RESOURCES =====
# read-only access to RDS data

@mcp.resource(uri='aws-rds://clusters', name='DB Clusters', mime_type='application/json')
async def list_clusters_resource() -> str:
    """List all DB clusters in the region.
    
    Returns a JSON document containing all clusters with their current status,
    configuration, and member instances.
    """
    return await get_cluster_list_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://clusters/{cluster_id}',
    name='DB Cluster Details',
    mime_type='application/json',
)
async def get_cluster_resource(cluster_id: str) -> str:
    """Get detailed information about a specific DB cluster.
    
    Args:
        cluster_id: The identifier of the DB cluster
        
    Returns:
        JSON document with comprehensive cluster information including
        status, configuration, endpoints, and member instances.
    """
    return await get_cluster_detail_resource(cluster_id, get_rds_client())


# ===== CLUSTER MANAGEMENT TOOLS =====

@mcp.tool(name='create_db_cluster')
async def create_db_cluster_tool(
    ctx: Context,
    db_cluster_identifier: str = Field(description='The identifier for the DB cluster'),
    engine: str = Field(description='The name of the database engine (e.g., aurora, aurora-mysql, aurora-postgresql, mysql, postgres, mariadb, oracle, sqlserver)'),
    master_username: str = Field(description='The name of the master user for the DB cluster'),
    manage_master_user_password: Optional[bool] = Field(default=True, description='Specifies whether to manage the master user password with Amazon Web Services Secrets Manager'),
    database_name: Optional[str] = Field(default=None, description='The name for your database'),
    vpc_security_group_ids: Optional[List[str]] = Field(default=None, description='A list of EC2 VPC security groups'),
    db_subnet_group_name: Optional[str] = Field(default=None, description='A DB subnet group to associate with this DB cluster'),
    availability_zones: Optional[List[str]] = Field(default=None, description='A list of Availability Zones'),
    backup_retention_period: Optional[int] = Field(default=None, description='The number of days for which automated backups are retained'),
    port: Optional[int] = Field(default=None, description='The port number on which the instances accept connections'),
    engine_version: Optional[str] = Field(default=None, description='The version number of the database engine'),
) -> Dict[str, Any]:
    """Create a new RDS database cluster."""
    return await cluster.create_db_cluster(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_identifier=db_cluster_identifier,
        engine=engine,
        master_username=master_username,
        manage_master_user_password=manage_master_user_password,
        database_name=database_name,
        vpc_security_group_ids=vpc_security_group_ids,
        db_subnet_group_name=db_subnet_group_name,
        availability_zones=availability_zones,
        backup_retention_period=backup_retention_period,
        port=port,
        engine_version=engine_version,
    )


@mcp.tool(name='modify_db_cluster')
async def modify_db_cluster_tool(
    ctx: Context,
    db_cluster_identifier: str = Field(description='The identifier for the DB cluster'),
    apply_immediately: Optional[bool] = Field(default=None, description='Whether modifications are applied immediately'),
    backup_retention_period: Optional[int] = Field(default=None, description='The number of days for automated backups'),
    db_cluster_parameter_group_name: Optional[str] = Field(default=None, description='The name of the DB cluster parameter group'),
    vpc_security_group_ids: Optional[List[str]] = Field(default=None, description='VPC security groups'),
    port: Optional[int] = Field(default=None, description='The port number'),
    manage_master_user_password: Optional[bool] = Field(default=None, description='Specifies whether to manage the master user password with Amazon Web Services Secrets Manager'),
    engine_version: Optional[str] = Field(default=None, description='The version number of the database engine'),
    allow_major_version_upgrade: Optional[bool] = Field(default=None, description='Whether major version upgrades are allowed'),
) -> Dict[str, Any]:
    """Modify an existing RDS database cluster configuration."""
    return await cluster.modify_db_cluster(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_identifier=db_cluster_identifier,
        apply_immediately=apply_immediately,
        backup_retention_period=backup_retention_period,
        db_cluster_parameter_group_name=db_cluster_parameter_group_name,
        vpc_security_group_ids=vpc_security_group_ids,
        port=port,
        manage_master_user_password=manage_master_user_password,
        engine_version=engine_version,
        allow_major_version_upgrade=allow_major_version_upgrade,
    )


@mcp.tool(name='delete_db_cluster')
async def delete_db_cluster_tool(
    ctx: Context,
    db_cluster_identifier: str = Field(description='The identifier for the DB cluster'),
    skip_final_snapshot: bool = Field(description='Whether to skip creating a final snapshot'),
    final_db_snapshot_identifier: Optional[str] = Field(default=None, description='The snapshot identifier if creating final snapshot'),
    confirmation_token: Optional[str] = Field(default=None, description='The confirmation token for the operation - required for destructive operations'),
) -> Dict[str, Any]:
    """Delete an RDS database cluster.
    
    This is a destructive operation that requires a two-step confirmation process:
    1. First call without a confirmation_token to get a token
    2. Then call again with the token to confirm and execute the operation
    """
    return await cluster.delete_db_cluster(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_identifier=db_cluster_identifier,
        skip_final_snapshot=skip_final_snapshot,
        final_db_snapshot_identifier=final_db_snapshot_identifier,
        confirmation_token=confirmation_token,
    )


@mcp.tool(name='status_db_cluster')
async def status_db_cluster_tool(
    ctx: Context,
    db_cluster_identifier: str = Field(description='The identifier for the DB cluster'),
    action: str = Field(description='Action to perform: "start", "stop", or "reboot"'),
    confirmation: Optional[str] = Field(default=None, description='Confirmation text for destructive operations - required for all actions'),
) -> Dict[str, Any]:
    """Manage the status of an RDS database cluster.
    
    This tool allows you to start, stop, or reboot an RDS database cluster.
    
    Important warnings:
    - start: Starting a stopped cluster will resume billing charges and may incur costs
    - stop: Stopping a cluster will make it unavailable until started again
    - reboot: Rebooting will cause a brief interruption to database service
    """
    return await cluster.status_db_cluster(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_identifier=db_cluster_identifier,
        action=action,
        confirmation=confirmation,
    )


@mcp.tool(name='failover_db_cluster')
async def failover_db_cluster_tool(
    ctx: Context,
    db_cluster_identifier: str = Field(description='The identifier for the DB cluster'),
    target_db_instance_identifier: Optional[str] = Field(default=None, description='The instance to promote to primary'),
    confirmation: Optional[str] = Field(default=None, description='Confirmation text for destructive operation - must match the cluster identifier exactly'),
) -> Dict[str, Any]:
    """Force a failover for an RDS database cluster."""
    return await cluster.failover_db_cluster(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_identifier=db_cluster_identifier,
        target_db_instance_identifier=target_db_instance_identifier,
        confirmation=confirmation,
    )


@mcp.tool(name='describe_db_clusters')
async def describe_db_clusters_tool(
    ctx: Context,
    db_cluster_identifier: Optional[str] = Field(default=None, description='The DB cluster identifier'),
    filters: Optional[List[Dict[str, Any]]] = Field(default=None, description='Filters to apply'),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    max_records: Optional[int] = Field(default=None, description='Maximum number of records'),
) -> Dict[str, Any]:
    """Retrieve information about one or multiple RDS clusters."""
    return await cluster.describe_db_clusters(
        ctx=ctx,
        rds_client=get_rds_client(),
        db_cluster_identifier=db_cluster_identifier,
        filters=filters,
        marker=marker,
        max_records=max_records,
    )


# ===== MAIN FUNCTION =====

def main():
    """Run the MCP server with CLI argument support."""
    global _readonly, _region
    
    parser = argparse.ArgumentParser(
        description='An AWS Labs MCP server for comprehensive management of Amazon RDS databases'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument(
        '--region',
        type=str,
        required=True,
        help='AWS region for RDS operations'
    )
    parser.add_argument(
        '--readonly',
        type=str,
        default='true',
        choices=['true', 'false'],
        help='Whether to run in read-only mode (default: true)'
    )
    parser.add_argument(
        '--profile',
        type=str,
        help='AWS profile to use for credentials'
    )

    args = parser.parse_args()

    # global configuration
    _readonly = args.readonly.lower() == 'true'
    _region = args.region
    
    # AWS profile if provided
    if args.profile:
        os.environ['AWS_PROFILE'] = args.profile
    
    # log configuration
    logger.info(f"Starting RDS Management MCP Server v{MCP_SERVER_VERSION}")
    logger.info(f"Region: {_region}")
    logger.info(f"Read-only mode: {_readonly}")
    if args.profile:
        logger.info(f"AWS Profile: {args.profile}")

    # run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
