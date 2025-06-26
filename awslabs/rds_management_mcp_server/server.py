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
    get_instance_detail_resource,
    get_instance_list_resource,
)
from .models import (
    ClusterModel,
    ClusterListModel,
    InstanceModel,
    InstanceListModel,
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

@mcp.resource(uri='aws-rds://db-cluster', name='DB Clusters', mime_type='application/json')
async def list_clusters_resource() -> str:
    """List all available Amazon RDS clusters in your account.
    
    <use_case>
    Use this resource to discover all available RDS database clusters in your AWS account,
    including Aurora clusters (MySQL/PostgreSQL) and Multi-AZ DB clusters.
    </use_case>
    
    <important_notes>
    1. The response provides the essential information (identifiers, engine, etc.) about each cluster
    2. Cluster identifiers returned can be used with other tools and resources in this MCP server
    3. Keep note of the db_cluster_identifier and db_cluster_resource_id for use with other tools
    4. Clusters are filtered to the AWS region specified in your environment configuration
    5. Use the `aws-rds://clusters/{cluster_id}` to get more information about a specific cluster
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `clusters`: Array of DB cluster objects
    - `count`: Number of clusters found
    - `resource_uri`: Base URI for accessing clusters
    
    Each cluster object contains:
    - `db_cluster_identifier`: Unique identifier for the cluster
    - `db_cluster_resource_id`: The unique resource identifier for this cluster
    - `db_cluster_arn`: ARN of the cluster
    - `status`: Current status of the cluster
    - `engine`: Database engine type
    - `engine_version`: The version of the database engine
    - `availability_zones`: The AZs where the cluster instances can be created
    - `multi_az`: Whether the cluster has instances in multiple Availability Zones
    - `tag_list`: List of tags attached to the cluster
    
    <examples>
    Example usage scenarios:
    1. Discovery and inventory:
       - List all available RDS clusters to create an inventory
       - Identify cluster engine types and versions in your environment
    2. Preparation for other operations:
       - Find specific cluster identifiers to use with management tools
       - Identify clusters that may need maintenance or upgrades
    </examples>
    """
    return await get_cluster_list_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-cluster/{cluster_id}',
    name='DB Cluster Details',
    mime_type='application/json',
)
async def get_cluster_resource(cluster_id: str) -> str:
    """Get detailed information about a specific Amazon RDS cluster.
    
    <use_case>
    Use this resource to retrieve comprehensive details about a specific RDS database cluster
    identified by its cluster ID. This provides deeper insights than the cluster list resource.
    </use_case>
    
    <important_notes>
    1. The cluster ID must exist in your AWS account and region
    2. The response contains full configuration details about the specified cluster
    3. This resource includes information not available in the list view such as parameter groups,
       backup configuration, and maintenance windows
    4. Use the cluster list resource first to identify valid cluster IDs
    5. Error responses will be returned if the cluster doesn't exist or there are permission issues
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing detailed cluster information:
    - All fields from the list view plus:
    - `endpoint`: The primary endpoint for connecting to the cluster
    - `reader_endpoint`: The reader endpoint for read operations (if applicable)
    - `port`: The port the database engine is listening on
    - `parameter_group`: Database parameter group information
    - `backup_retention_period`: How long backups are retained (in days)
    - `preferred_backup_window`: When automated backups occur
    - `preferred_maintenance_window`: When maintenance operations can occur
    - `resource_uri`: The full resource URI for this specific cluster
    
    <examples>
    Example usage scenarios:
    1. Detailed configuration review:
       - Verify backup configuration meets requirements
       - Check maintenance windows align with operational schedules
    2. Connection information lookup:
       - Retrieve endpoints needed for application configuration
       - Obtain port information for security group configuration
    3. Audit and compliance:
       - Verify parameter groups match expected configurations
       - Confirm encryption settings are properly applied
    </examples>
    """
    return await get_cluster_detail_resource(cluster_id, get_rds_client())


@mcp.resource(uri='aws-rds://db-instance', name='DB Instances', mime_type='application/json')
async def list_instances_resource() -> str:
    """List all available Amazon RDS instances in your account.
    
    <use_case>
    Use this resource to discover all available RDS database instances in your AWS account.
    </use_case>
    
    <important_notes>
    1. The response provides essential information about each instance
    2. Instance identifiers returned can be used with other tools and resources in this MCP server
    3. Instances are filtered to the AWS region specified in your environment configuration
    4. Use the `aws-rds://db-instance/{instance_id}` to get more information about a specific instance
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `instances`: Array of DB instance objects
    - `count`: Number of instances found
    - `resource_uri`: Base URI for accessing instances
    
    <examples>
    Example usage scenarios:
    1. Discovery and inventory:
       - List all available RDS instances to create an inventory
       - Identify instance engine types and versions in your environment
    2. Preparation for other operations:
       - Find specific instance identifiers to use with management tools
    </examples>
    """
    return await get_instance_list_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-instance/{instance_id}',
    name='DB Instance Details',
    mime_type='application/json',
)
async def get_instance_resource(instance_id: str) -> str:
    """Get detailed information about a specific Amazon RDS instance.
    
    <use_case>
    Use this resource to retrieve comprehensive details about a specific RDS database instance
    identified by its instance ID.
    </use_case>
    
    <important_notes>
    1. The instance ID must exist in your AWS account and region
    2. The response contains full configuration details about the specified instance
    3. Error responses will be returned if the instance doesn't exist or there are permission issues
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing detailed instance information including:
    - `instance_id`: The unique identifier for the instance
    - `status`: Current status of the instance
    - `engine`: Database engine type
    - `engine_version`: The version of the database engine
    - `endpoint`: Connection endpoint information
    - `storage`: Storage configuration details
    - `multi_az`: Whether the instance is a Multi-AZ deployment
    - Other instance details, settings, and configuration
    
    <examples>
    Example usage scenarios:
    1. Detailed instance configuration review
    2. Connection information lookup
    3. Storage configuration analysis
    </examples>
    """
    return await get_instance_detail_resource(instance_id, get_rds_client())


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
    """Create a new RDS database cluster.
    
    <use_case>
    Use this tool to provision a new Amazon RDS database cluster in your AWS account.
    This creates the cluster control plane but doesn't automatically provision database instances.
    You'll need to create DB instances separately after the cluster is available.
    </use_case>
    
    <important_notes>
    1. Cluster identifiers must follow naming rules: 1-63 alphanumeric characters, must begin with a letter
    2. The tool will automatically determine default port numbers based on the engine if not specified
    3. Using manage_master_user_password=True (default) will store the password in AWS Secrets Manager
    4. Not all parameter combinations are valid for all database engines
    5. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the creation
    - `formatted_cluster`: A simplified representation of the cluster in standard format
    - `DBCluster`: The full AWS API response containing all cluster details including:
      - `DBClusterIdentifier`: The cluster identifier
      - `Status`: The current status (usually "creating" initially)
      - `Engine`: The database engine
      - `EngineVersion`: The engine version
      - `Endpoint`: The connection endpoint
      - `MasterUsername`: The admin username
      - `AvailabilityZones`: List of AZs where the cluster operates
      - Other cluster configuration details and settings
    
    <examples>
    Example usage scenarios:
    1. Create a basic Aurora PostgreSQL cluster:
       - db_cluster_identifier="my-postgres-cluster"
       - engine="aurora-postgresql"
       - master_username="admin"
    
    2. Create a MySQL-compatible Aurora cluster with custom settings:
       - db_cluster_identifier="production-aurora"
       - engine="aurora-mysql"
       - master_username="dbadmin"
       - database_name="appdb"
       - backup_retention_period=7
       - vpc_security_group_ids=["sg-12345678"]
    </examples>
    """
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
    """Modify an existing RDS database cluster configuration.
    
    <use_case>
    Use this tool to update the configuration of an existing Amazon RDS database cluster.
    This allows changing various settings like backup retention, parameter groups, security groups, 
    and upgrading database engine versions without recreating the cluster.
    </use_case>
    
    <important_notes>
    1. Setting apply_immediately=True applies changes immediately but may cause downtime
    2. Setting apply_immediately=False (default) applies changes during the next maintenance window
    3. Major version upgrades require allow_major_version_upgrade=True
    4. Changing the port may require updates to security groups and application configurations
    5. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the modification
    - `formatted_cluster`: A simplified representation of the modified cluster in standard format
    - `DBCluster`: The full AWS API response containing all cluster details including:
      - `DBClusterIdentifier`: The cluster identifier
      - `Status`: The current status (may show "modifying")
      - `PendingModifiedValues`: Values that will be applied if not immediate
      - Other updated cluster configuration details
    
    <examples>
    Example usage scenarios:
    1. Increase backup retention period:
       - db_cluster_identifier="production-db-cluster" 
       - backup_retention_period=14
       - apply_immediately=True
    
    2. Change security groups and apply during maintenance window:
       - db_cluster_identifier="production-db-cluster"
       - vpc_security_group_ids=["sg-87654321", "sg-12348765"]
       - apply_immediately=False
    
    3. Upgrade database engine version:
       - db_cluster_identifier="production-db-cluster"
       - engine_version="5.7.mysql_aurora.2.10.2"
       - allow_major_version_upgrade=True
       - apply_immediately=False
    </examples>
    """
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
    skip_final_snapshot: bool = Field(default=False, description='Whether to skip creating a final snapshot'),
    final_db_snapshot_identifier: Optional[str] = Field(default=None, description='The snapshot identifier if creating final snapshot'),
    confirmation_token: Optional[str] = Field(default=None, description='The confirmation token for the operation - required for destructive operations'),
) -> Dict[str, Any]:
    """Delete an RDS database cluster.
    
    <use_case>
    Use this tool to permanently remove an Amazon RDS database cluster and optionally
    create a final snapshot. This operation cannot be undone, so a confirmation token is
    required to prevent accidental deletion.
    </use_case>
    
    <important_notes>
    1. This is a destructive operation that permanently deletes data
    2. A confirmation token is required for safety - first call without token to receive one
    3. By default, a final snapshot is created (skip_final_snapshot=False)
    4. When creating a final snapshot (default behavior), you must provide final_db_snapshot_identifier
    5. The operation may take several minutes to complete
    6. All associated instances, automated backups and continuous backups (PITR) will be deleted
    7. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    If called without a confirmation token:
    - `requires_confirmation`: Always true
    - `warning`: Warning message about the deletion
    - `impact`: Description of the impact of deletion
    - `confirmation_token`: Token to use in a subsequent call
    - `message`: Instructions for confirming the deletion
    
    If called with a valid confirmation token:
    - `message`: Success message confirming deletion
    - `formatted_cluster`: A simplified representation of the deleted cluster
    - `DBCluster`: The full AWS API response containing cluster details including:
      - `DBClusterIdentifier`: The cluster identifier
      - `Status`: The current status (usually "deleting")
      - Other cluster details
    
    <examples>
    Example usage scenarios:
    1. Start deletion process (get confirmation token):
       - db_cluster_identifier="test-db-cluster"
       - skip_final_snapshot=true
    
    2. Confirm deletion (with confirmation token):
       - db_cluster_identifier="test-db-cluster"
       - skip_final_snapshot=true
       - confirmation_token="abc123xyz" (token received from step 1)
    
    3. Delete with final snapshot:
       - db_cluster_identifier="prod-db-cluster"
       - skip_final_snapshot=false
       - final_db_snapshot_identifier="prod-final-snapshot-20230625"
    </examples>
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
    
    <use_case>
    Use this tool to change the operational status of an Amazon RDS database cluster.
    You can start a stopped cluster, stop a running cluster, or reboot a cluster to apply
    configuration changes or resolve certain issues.
    </use_case>
    
    <important_notes>
    1. Each action requires explicit confirmation with a specific confirmation string
    2. Stopping a cluster will make it unavailable but will continue to incur storage charges
    3. Starting a cluster will resume full billing charges
    4. Rebooting causes a brief interruption but preserves cluster settings and data
    5. Aurora Serverless v1 clusters cannot be stopped manually
    6. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    If called without confirmation:
    - `requires_confirmation`: Always true
    - `warning`: Warning message about the action
    - `impact`: Description of the impact of the action
    - `message`: Instructions for confirming the action
    
    If called with valid confirmation:
    - `message`: Success message confirming the action
    - `formatted_cluster`: A simplified representation of the cluster in its new state
    - `DBCluster`: The full AWS API response containing cluster details including:
      - `DBClusterIdentifier`: The cluster identifier
      - `Status`: The current status (e.g., "starting", "stopping", "rebooting")
      - Other cluster details
    
    <examples>
    Example usage scenarios:
    1. Stop a development cluster (first call to get warning):
       - db_cluster_identifier="dev-db-cluster" 
       - action="stop"
    
    2. Confirm stopping the cluster:
       - db_cluster_identifier="dev-db-cluster"
       - action="stop"
       - confirmation="CONFIRM_STOP"
    
    3. Reboot a cluster that's experiencing issues:
       - db_cluster_identifier="prod-db-cluster"
       - action="reboot"
       - confirmation="CONFIRM_REBOOT"
    
    4. Start a previously stopped cluster:
       - db_cluster_identifier="dev-db-cluster"
       - action="start"
       - confirmation="CONFIRM_START"
    </examples>
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
    """Force a failover for an RDS database cluster.
    
    <use_case>
    Use this tool to force a failover of an Amazon RDS Multi-AZ DB cluster, promoting a read replica
    to become the primary instance. This can be used for disaster recovery testing, to move the primary
    to a different availability zone, or to recover from issues with the current primary instance.
    </use_case>
    
    <important_notes>
    1. This operation requires explicit confirmation with the text "CONFIRM_FAILOVER"
    2. Failover causes a momentary interruption in database availability
    3. Any in-flight transactions that haven't been committed may be lost during failover
    4. The cluster must be in the "available" state for the failover to succeed
    5. If target_db_instance_identifier is not specified, RDS chooses a replica automatically
    6. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    If called without confirmation:
    - `requires_confirmation`: Always true
    - `warning`: Warning message about the failover
    - `impact`: Description of the impact of the failover
    - `message`: Instructions for confirming the failover
    
    If called with valid confirmation:
    - `message`: Success message confirming the initiated failover
    - `formatted_cluster`: A simplified representation of the cluster during failover
    - `DBCluster`: The full AWS API response containing cluster details including:
      - `DBClusterIdentifier`: The cluster identifier
      - `Status`: The current status (usually "failing-over")
      - Other cluster details
    
    <examples>
    Example usage scenarios:
    1. Start failover process (get warning):
       - db_cluster_identifier="production-cluster"
    
    2. Confirm failover without specifying a target:
       - db_cluster_identifier="production-cluster"
       - confirmation="CONFIRM_FAILOVER"
    
    3. Failover to a specific replica instance:
       - db_cluster_identifier="production-cluster"
       - target_db_instance_identifier="production-instance-east-1c"
       - confirmation="CONFIRM_FAILOVER"
    
    4. Regular disaster recovery drill:
       - db_cluster_identifier="production-cluster"
       - confirmation="CONFIRM_FAILOVER"
    </examples>
    """
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
    """Retrieve information about one or multiple RDS clusters.
    
    <use_case>
    Use this tool to query detailed information about Amazon RDS clusters in your AWS account.
    This provides the raw data from the AWS API and is useful for advanced filtering and pagination.
    </use_case>
    
    <important_notes>
    1. If db_cluster_identifier is specified, information is returned only for that cluster
    2. The filters parameter allows complex querying based on cluster attributes
    3. Pagination is supported through marker and max_records parameters
    4. The response includes the complete AWS API data structure
    5. Results are filtered to the AWS region specified in your environment configuration
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `DBClusters`: List of DB cluster descriptions from the AWS API
    - `formatted_clusters`: List of simplified cluster representations
    - `Marker`: Pagination token for retrieving the next set of results (if applicable)
    
    Each DB cluster description in the API response contains extensive details including:
    - All connection endpoints
    - Complete configuration parameters
    - Status information
    - Associated resources
    - Security settings
    - Backup configuration
    - Performance settings
    
    <examples>
    Example usage scenarios:
    1. Get details about a specific cluster:
       - db_cluster_identifier="production-aurora-cluster"
    
    2. Filter clusters by engine type:
       - filters=[{"Name": "engine", "Values": ["aurora-postgresql"]}]
    
    3. Get the first 20 clusters, then paginate:
       - max_records=20
       (Then in subsequent calls)
       - max_records=20
       - marker="token-from-previous-response"
    
    4. Complex filtering with multiple attributes:
       - filters=[
           {"Name": "engine", "Values": ["aurora-mysql"]},
           {"Name": "status", "Values": ["available"]}
         ]
    </examples>
    """
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

    if args.port:
        mcp.settings.port = args.port
        
    # default streamable HTTP transport
    mcp.run()


if __name__ == '__main__':
    main()
