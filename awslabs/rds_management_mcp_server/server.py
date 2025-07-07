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
from . import backup, cluster, instance, parameter
from .constants import MCP_SERVER_VERSION
from .resources import (
    get_cluster_detail_resource,
    get_cluster_list_resource,
    get_instance_detail_resource,
    get_instance_list_resource,
)
from .backup import (
    get_all_cluster_backups_resource,
    get_all_instance_backups_resource,
    get_cluster_backups_resource,
    get_instance_backups_resource,
)
from .parameter import (
    get_db_instance_parameters_resource,
    get_db_instance_parameter_groups_resource,
    get_db_cluster_parameters_resource,
    get_db_cluster_parameter_groups_resource,
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


@mcp.resource(
    uri='aws-rds://db-cluster/{db_cluster_identifier}/backups',
    name='DB Cluster Backups',
    mime_type='application/json',
)
async def cluster_backups_resource(db_cluster_identifier: str) -> str:
    """List all backups including manual snapshot and auto backups for a specific db cluster.
    
    <use_case>
    Use this resource to discover all available backups for a specific RDS database cluster,
    including both manual snapshots and automated backups. This provides a comprehensive
    view of all restore points available for a cluster.
    </use_case>
    
    <important_notes>
    1. The cluster ID must exist in your AWS account and region
    2. The response includes both manual snapshots and automated backups in a single view
    3. Automated backups are created according to your retention policy settings
    4. Manual snapshots remain until explicitly deleted
    5. Both types can be used for point-in-time recovery operations
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `snapshots`: Array of manual DB cluster snapshots
    - `automated_backups`: Array of automated backups
    - `count`: Total number of backups available
    - `resource_uri`: The resource URI for these backups
    
    <examples>
    Example usage scenarios:
    1. Disaster recovery planning:
       - Identify available restore points before performing operations
       - Verify backup schedules are working as expected
    2. Backup management:
       - Identify old snapshots that could be removed
       - Confirm automated backups are being created according to policy
    </examples>
    """
    return await get_cluster_backups_resource(db_cluster_identifier, get_rds_client())


@mcp.resource(
    uri='aws-rds://db-instance/{db_instance_identifier}/backups',
    name='DB Instance Backups',
    mime_type='application/json',
)
async def instance_backups_resource(db_instance_identifier: str) -> str:
    """List of backups including manual snapshot and auto backups for a specific db instance.
    
    <use_case>
    Use this resource to discover all available backups for a specific RDS database instance,
    including both manual snapshots and automated backups. This provides a comprehensive
    view of all restore points available for an instance.
    </use_case>
    
    <important_notes>
    1. The instance ID must exist in your AWS account and region
    2. The response includes both manual snapshots and automated backups in a single view
    3. Automated backups are created according to your retention policy settings
    4. Manual snapshots remain until explicitly deleted
    5. Both types can be used for point-in-time recovery operations
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `snapshots`: Array of manual DB instance snapshots
    - `automated_backups`: Array of automated backups
    - `count`: Total number of backups available
    - `resource_uri`: The resource URI for these backups
    
    <examples>
    Example usage scenarios:
    1. Disaster recovery planning:
       - Identify available restore points before performing operations
       - Verify backup schedules are working as expected
    2. Backup management:
       - Identify old snapshots that could be removed
       - Confirm automated backups are being created according to policy
    </examples>
    """
    return await get_instance_backups_resource(db_instance_identifier, get_rds_client())


@mcp.resource(
    uri='aws-rds://db-cluster/backups',
    name='All DB Cluster Backups',
    mime_type='application/json',
)
async def all_cluster_backups_resource() -> str:
    """List all backups including manual snapshot and auto backups across all DB clusters.
    
    <use_case>
    Use this resource to discover all available backups across all RDS database clusters
    in your AWS account, including both manual snapshots and automated backups. This provides
    a comprehensive view of all restore points available in your environment without having to
    specify an individual cluster.
    </use_case>
    
    <important_notes>
    1. The response includes backups for all clusters in the current region
    2. Both manual snapshots and automated backups are included in the results
    3. This resource is useful for getting a complete overview of all backup resources
    4. For large environments with many clusters, this may return a large amount of data
    5. Results can be filtered client-side by cluster ID if needed
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `snapshots`: Array of manual DB cluster snapshots across all clusters
    - `automated_backups`: Array of automated backups across all clusters
    - `count`: Total number of backups available
    - `resource_uri`: The resource URI for these backups
    
    <examples>
    Example usage scenarios:
    1. Backup inventory management:
       - Get a complete inventory of all backup resources in the account
       - Identify snapshots that could be deleted to reduce storage costs
    2. Cross-cluster restore planning:
       - Find available snapshots across all clusters for restore operations
       - Plan migration or disaster recovery operations
    </examples>
    """
    return await get_all_cluster_backups_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-instance/backups',
    name='All DB Instance Backups',
    mime_type='application/json',
)
async def all_instance_backups_resource() -> str:
    """List all backups including manual snapshot and auto backups across all DB instances.
    
    <use_case>
    Use this resource to discover all available backups across all RDS database instances
    in your AWS account, including both manual snapshots and automated backups. This provides
    a comprehensive view of all restore points available in your environment without having to
    specify an individual instance.
    </use_case>
    
    <important_notes>
    1. The response includes backups for all instances in the current region
    2. Both manual snapshots and automated backups are included in the results
    3. This resource is useful for getting a complete overview of all backup resources
    4. For large environments with many instances, this may return a large amount of data
    5. Results can be filtered client-side by instance ID if needed
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `snapshots`: Array of manual DB instance snapshots across all instances
    - `automated_backups`: Array of automated backups across all instances
    - `count`: Total number of backups available
    - `resource_uri`: The resource URI for these backups
    
    <examples>
    Example usage scenarios:
    1. Backup inventory management:
       - Get a complete inventory of all backup resources in the account
       - Identify snapshots that could be deleted to reduce storage costs
    2. Cross-instance restore planning:
       - Find available snapshots across all instances for restore operations
       - Plan migration or disaster recovery operations
    </examples>
    """
    return await get_all_instance_backups_resource(get_rds_client())


# ===== PARAMETER RESOURCES =====

@mcp.resource(
    uri='aws-rds://db-instance/parameters',
    name='DB Instance Parameters',
    mime_type='application/json',
)
async def db_instance_parameters_resource() -> str:
    """Resource for listing all DB parameters.
    
    <use_case>
    Use this resource to discover information about database parameters across all instance parameter
    groups in your account. Parameter values define how the database engine operates and behaves.
    </use_case>
    
    <important_notes>
    1. This resource provides a consolidated view of parameters across all parameter groups
    2. Some parameters may be specific to certain database engines
    3. Parameters are organized by their parameter groups
    4. To see specific parameter groups and their parameters, use the parameter_groups resource
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `parameter_groups`: Array of parameter group objects, each containing:
      - `name`: The parameter group name
      - `parameters`: Array of parameter objects
    - `count`: Total number of parameter groups
    
    <examples>
    Example usage scenarios:
    1. Parameter audit and compliance:
       - Review parameter settings across your environment
       - Identify non-standard configurations
    2. Configuration planning:
       - Determine what parameters are available for tuning
       - Compare parameter settings across different parameter groups
    </examples>
    """
    return await get_db_instance_parameter_groups_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-instance/parameter-groups',
    name='DB Instance Parameter Groups',
    mime_type='application/json',
)
async def db_instance_parameter_groups_resource() -> str:
    """Resource for listing all DB parameter groups.
    
    <use_case>
    Use this resource to discover all available DB instance parameter groups in your AWS account.
    Parameter groups are collections of engine configuration values that can be applied to
    database instances.
    </use_case>
    
    <important_notes>
    1. Parameter groups are organized by database engine family
    2. Default parameter groups are provided for each engine family
    3. Custom parameter groups allow for performance and behavior tuning
    4. The same parameter group can be applied to multiple instances
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `parameter_groups`: Array of parameter group objects
    - `count`: Total number of parameter groups
    - `resource_uri`: The resource URI for these parameter groups
    
    <examples>
    Example usage scenarios:
    1. Configuration management:
       - Identify available parameter groups before creating instances
       - Review parameter group settings for compliance or optimization
    2. Preparation for applying common settings:
       - Find parameter groups that can be applied to multiple instances
       - Compare parameter settings across different groups
    </examples>
    """
    return await get_db_instance_parameter_groups_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-cluster/parameters',
    name='DB Cluster Parameters',
    mime_type='application/json',
)
async def db_cluster_parameters_resource() -> str:
    """Resource for listing all DB cluster parameters.
    
    <use_case>
    Use this resource to discover information about database parameters across all cluster parameter
    groups in your account. Parameter values define how the database engine operates and behaves at
    the cluster level.
    </use_case>
    
    <important_notes>
    1. This resource provides a consolidated view of parameters across all cluster parameter groups
    2. Cluster parameters affect all instances in the cluster
    3. Some parameters may be specific to certain database engines
    4. Parameters are organized by their parameter groups
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `parameter_groups`: Array of parameter group objects, each containing:
      - `name`: The parameter group name
      - `parameters`: Array of parameter objects
    - `count`: Total number of parameter groups
    
    <examples>
    Example usage scenarios:
    1. Parameter audit and compliance:
       - Review parameter settings across your environment
       - Identify non-standard configurations
    2. Configuration planning:
       - Determine what parameters are available for tuning
       - Compare parameter settings across different parameter groups
    </examples>
    """
    return await get_db_cluster_parameter_groups_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-cluster/parameter-groups',
    name='DB Cluster Parameter Groups',
    mime_type='application/json',
)
async def db_cluster_parameter_groups_resource() -> str:
    """Resource for listing all DB cluster parameter groups.
    
    <use_case>
    Use this resource to discover all available DB cluster parameter groups in your AWS account.
    Cluster parameter groups are collections of engine configuration values that can be applied to
    database clusters.
    </use_case>
    
    <important_notes>
    1. Cluster parameter groups are organized by database engine family
    2. Default parameter groups are provided for each engine family
    3. Custom parameter groups allow for performance and behavior tuning
    4. The same parameter group can be applied to multiple clusters
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `parameter_groups`: Array of parameter group objects
    - `count`: Total number of parameter groups
    - `resource_uri`: The resource URI for these parameter groups
    
    <examples>
    Example usage scenarios:
    1. Configuration management:
       - Identify available parameter groups before creating clusters
       - Review parameter group settings for compliance or optimization
    2. Preparation for applying common settings:
       - Find parameter groups that can be applied to multiple clusters
       - Compare parameter settings across different groups
    </examples>
    """
    return await get_db_cluster_parameter_groups_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-cluster/parameter-groups/{db_cluster_parameter_group_name}/parameters',
    name='DB Cluster Parameter Group Parameters',
    mime_type='application/json',
)
async def db_cluster_parameter_group_parameters_resource(db_cluster_parameter_group_name: str) -> str:
    """Resource for listing parameters in a specific DB cluster parameter group.
    
    <use_case>
    Use this resource to inspect detailed information about all parameters in a specific
    DB cluster parameter group. This provides insight into how the database cluster is
    configured and the specific settings that apply to all instances in the cluster.
    </use_case>
    
    <important_notes>
    1. Parameter values determine database behavior and performance
    2. Some parameters can be modified, while others are fixed
    3. Parameter modifications may require a database reboot to take effect
    4. Parameters have different data types and valid value ranges
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `parameters`: Array of parameter objects with:
      - `name`: The parameter name
      - `value`: The parameter value
      - `description`: Parameter description
      - `allowed_values`: Valid range or values
      - `is_modifiable`: Whether the parameter can be changed
    - `count`: Total number of parameters
    - `parameter_group_name`: The name of the parameter group
    
    <examples>
    Example usage scenarios:
    1. Parameter review and tuning:
       - Examine current parameter settings before making changes
       - Identify parameters that can be modified for performance improvements
    2. Configuration documentation:
       - Document the complete configuration of a database cluster
       - Compare settings across different environments
    </examples>
    """
    return await get_db_cluster_parameters_resource(db_cluster_parameter_group_name, get_rds_client())


@mcp.resource(
    uri='aws-rds://db-instance/parameter-groups/{db_parameter_group_name}/parameters',
    name='DB Instance Parameter Group Parameters',
    mime_type='application/json',
)
async def db_instance_parameter_group_parameters_resource(db_parameter_group_name: str) -> str:
    """Resource for listing parameters in a specific DB instance parameter group.
    
    <use_case>
    Use this resource to inspect detailed information about all parameters in a specific
    DB instance parameter group. This provides insight into how database instances using
    this parameter group are configured.
    </use_case>
    
    <important_notes>
    1. Parameter values determine database behavior and performance
    2. Some parameters can be modified, while others are fixed
    3. Parameter modifications may require a database reboot to take effect
    4. Parameters have different data types and valid value ranges
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `parameters`: Array of parameter objects with:
      - `name`: The parameter name
      - `value`: The parameter value
      - `description`: Parameter description
      - `allowed_values`: Valid range or values
      - `is_modifiable`: Whether the parameter can be changed
    - `count`: Total number of parameters
    - `parameter_group_name`: The name of the parameter group
    
    <examples>
    Example usage scenarios:
    1. Parameter review and tuning:
       - Examine current parameter settings before making changes
       - Identify parameters that can be modified for performance improvements
    2. Configuration documentation:
       - Document the complete configuration of database instances
       - Compare settings across different environments
    </examples>
    """
    return await get_db_instance_parameters_resource(db_parameter_group_name, get_rds_client())


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


# ===== INSTANCE MANAGEMENT TOOLS =====

@mcp.tool(name='create_db_instance')
async def create_db_instance_tool(
    ctx: Context,
    db_instance_identifier: str = Field(description='The identifier for the DB instance'),
    db_cluster_identifier: str = Field(description='The identifier of the DB cluster that the instance will belong to'),
    db_instance_class: str = Field(description='The compute and memory capacity of the DB instance (e.g., db.r5.large)'),
    engine: str = Field(description='The name of the database engine to be used for this instance'),
    availability_zone: Optional[str] = Field(default=None, description='The Availability Zone where the DB instance will be created'),
    publicly_accessible: Optional[bool] = Field(default=None, description='Specifies whether the DB instance is publicly accessible'),
    tags: Optional[List[Dict[str, str]]] = Field(default=None, description='A list of tags to assign to the DB instance'),
) -> Dict[str, Any]:
    """Create a new RDS DB instance within an existing DB cluster.
    
    <use_case>
    Use this tool to provision a new Amazon RDS database instance within an existing DB cluster.
    For Aurora databases, cluster instances provide the compute and memory capacity for the cluster.
    </use_case>
    
    <important_notes>
    1. Instance identifiers must follow naming rules: 1-63 alphanumeric characters, must begin with a letter
    2. The DB cluster must exist before creating an instance within it
    3. The instance class determines the compute and memory capacity (e.g., db.r5.large)
    4. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the creation
    - `formatted_instance`: A simplified representation of the instance in standard format
    - `DBInstance`: The full AWS API response containing all instance details including:
      - `DBInstanceIdentifier`: The instance identifier
      - `DBInstanceClass`: The compute capacity class
      - `Engine`: The database engine
      - `DBClusterIdentifier`: The parent cluster identifier
      - `AvailabilityZone`: The AZ where the instance is located
      - `Endpoint`: The connection endpoint
      - Other instance configuration details
    
    <examples>
    Example usage scenarios:
    1. Create a standard Aurora cluster instance:
       - db_instance_identifier="aurora-instance-1"
       - db_cluster_identifier="aurora-cluster"
       - db_instance_class="db.r5.large"
    
    2. Create a DB instance in a specific availability zone:
       - db_instance_identifier="aurora-instance-2"
       - db_cluster_identifier="aurora-cluster"
       - db_instance_class="db.r5.large"
       - availability_zone="us-east-1a"
       - publicly_accessible=false
    </examples>
    """
    return await instance.create_db_instance(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_instance_identifier=db_instance_identifier,
        db_cluster_identifier=db_cluster_identifier,
        db_instance_class=db_instance_class,
        availability_zone=availability_zone,
        engine=engine,
        publicly_accessible=publicly_accessible,
        tags=tags,
    )


@mcp.tool(name='modify_db_instance')
async def modify_db_instance_tool(
    ctx: Context,
    db_instance_identifier: str = Field(description='The identifier for the DB instance'),
    apply_immediately: Optional[bool] = Field(default=None, description='Specifies whether the modifications are applied immediately, or during the next maintenance window'),
    db_instance_class: Optional[str] = Field(default=None, description='The new compute and memory capacity of the DB instance'),
    db_parameter_group_name: Optional[str] = Field(default=None, description='The name of the DB parameter group to apply to the DB instance'),
    publicly_accessible: Optional[bool] = Field(default=None, description='Specifies whether the DB instance is publicly accessible'),
    auto_minor_version_upgrade: Optional[bool] = Field(default=None, description='Indicates whether minor engine upgrades are applied automatically to the DB instance'),
    preferred_maintenance_window: Optional[str] = Field(default=None, description='The weekly time range during which system maintenance can occur'),
) -> Dict[str, Any]:
    """Modify an existing RDS database instance.
    
    <use_case>
    Use this tool to update the configuration of an existing Amazon RDS database instance.
    This allows changing various settings like instance class, parameter groups, and
    maintenance windows without recreating the instance.
    </use_case>
    
    <important_notes>
    1. Setting apply_immediately=True applies changes immediately but may cause downtime
    2. Setting apply_immediately=False (default) applies changes during the next maintenance window
    3. Changing the instance class affects the compute and memory capacity of the instance
    4. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the modification
    - `formatted_instance`: A simplified representation of the modified instance in standard format
    - `DBInstance`: The full AWS API response containing all instance details including:
      - `DBInstanceIdentifier`: The instance identifier
      - `DBInstanceClass`: The updated compute capacity class
      - `PendingModifiedValues`: Values that will be applied if not immediate
      - Other updated instance configuration details
    
    <examples>
    Example usage scenarios:
    1. Scale up instance capacity immediately:
       - db_instance_identifier="production-db-instance"
       - db_instance_class="db.r5.2xlarge"
       - apply_immediately=true
    
    2. Update parameter group during maintenance window:
       - db_instance_identifier="production-db-instance"
       - db_parameter_group_name="custom-mysql-params"
       - apply_immediately=false
    
    3. Change instance accessibility:
       - db_instance_identifier="production-db-instance"
       - publicly_accessible=false
    </examples>
    """
    return await instance.modify_db_instance(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_instance_identifier=db_instance_identifier,
        apply_immediately=apply_immediately,
        db_instance_class=db_instance_class,
        db_parameter_group_name=db_parameter_group_name,
        publicly_accessible=publicly_accessible,
        auto_minor_version_upgrade=auto_minor_version_upgrade,
        preferred_maintenance_window=preferred_maintenance_window,
    )


@mcp.tool(name='delete_db_instance')
async def delete_db_instance_tool(
    ctx: Context,
    db_instance_identifier: str = Field(description='The identifier for the DB instance'),
    skip_final_snapshot: bool = Field(default=False, description='Whether to skip creating a final snapshot'),
    final_db_snapshot_identifier: Optional[str] = Field(default=None, description='The snapshot identifier if creating final snapshot'),
    confirmation_token: Optional[str] = Field(default=None, description='The confirmation token for the operation - required for destructive operations'),
) -> Dict[str, Any]:
    """Delete an RDS database instance.
    
    <use_case>
    Use this tool to permanently remove an Amazon RDS database instance and optionally
    create a final snapshot. This operation cannot be undone, so a confirmation token is
    required to prevent accidental deletion.
    </use_case>
    
    <important_notes>
    1. This is a destructive operation that permanently deletes data
    2. A confirmation token is required for safety - first call without token to receive one
    3. By default, a final snapshot is created (skip_final_snapshot=False)
    4. When creating a final snapshot (default behavior), you must provide final_db_snapshot_identifier
    5. The operation may take several minutes to complete
    6. Automated backups and continuous backups (PITR) will be deleted with the instance
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
    - `formatted_instance`: A simplified representation of the deleted instance
    - `DBInstance`: The full AWS API response containing instance details including:
      - `DBInstanceIdentifier`: The instance identifier
      - `Status`: The current status (usually "deleting")
      - Other instance details
    
    <examples>
    Example usage scenarios:
    1. Start deletion process (get confirmation token):
       - db_instance_identifier="test-db-instance"
       - skip_final_snapshot=true
    
    2. Confirm deletion (with confirmation token):
       - db_instance_identifier="test-db-instance"
       - skip_final_snapshot=true
       - confirmation_token="abc123xyz" (token received from step 1)
    
    3. Delete with final snapshot:
       - db_instance_identifier="prod-db-instance"
       - skip_final_snapshot=false
       - final_db_snapshot_identifier="prod-instance-snapshot-20230625"
    </examples>
    """
    return await instance.delete_db_instance(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_instance_identifier=db_instance_identifier,
        skip_final_snapshot=skip_final_snapshot,
        final_db_snapshot_identifier=final_db_snapshot_identifier,
        confirmation_token=confirmation_token,
    )


@mcp.tool(name='status_db_instance')
async def status_db_instance_tool(
    ctx: Context,
    db_instance_identifier: str = Field(description='The identifier for the DB instance'),
    action: str = Field(description='Action to perform: "start", "stop", or "reboot"'),
    confirmation: Optional[str] = Field(default=None, description='Confirmation text for destructive operations - required for all actions'),
) -> Dict[str, Any]:
    """Manage the status of an RDS database instance.
    
    <use_case>
    Use this tool to change the operational status of an Amazon RDS database instance.
    You can start a stopped instance, stop a running instance, or reboot an instance to apply
    configuration changes or resolve certain issues.
    </use_case>
    
    <important_notes>
    1. Each action requires explicit confirmation with a specific confirmation string
    2. Stopping an instance will make it unavailable but will continue to incur storage charges
    3. Starting an instance will resume full billing charges
    4. Rebooting causes a brief interruption but preserves instance settings and data
    5. For Multi-AZ instances, a reboot with failover can be performed with specific parameters
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
    - `formatted_instance`: A simplified representation of the instance in its new state
    - `DBInstance`: The full AWS API response containing instance details including:
      - `DBInstanceIdentifier`: The instance identifier
      - `Status`: The current status (e.g., "starting", "stopping", "rebooting")
      - Other instance details
    
    <examples>
    Example usage scenarios:
    1. Stop a development instance (first call to get warning):
       - db_instance_identifier="dev-db-instance" 
       - action="stop"
    
    2. Confirm stopping the instance:
       - db_instance_identifier="dev-db-instance"
       - action="stop"
       - confirmation="CONFIRM_STOP"
    
    3. Reboot an instance that's experiencing issues:
       - db_instance_identifier="prod-db-instance"
       - action="reboot"
       - confirmation="CONFIRM_REBOOT"
    
    4. Start a previously stopped instance:
       - db_instance_identifier="dev-db-instance"
       - action="start"
       - confirmation="CONFIRM_START"
    </examples>
    """
    return await instance.status_db_instance(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_instance_identifier=db_instance_identifier,
        action=action,
        confirmation=confirmation,
    )


@mcp.tool(name='describe_db_instances')
async def describe_db_instances_tool(
    ctx: Context,
    db_instance_identifier: Optional[str] = Field(default=None, description='The DB instance identifier'),
    filters: Optional[List[Dict[str, Any]]] = Field(default=None, description='Filters to apply'),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    max_records: Optional[int] = Field(default=None, description='Maximum number of records'),
) -> Dict[str, Any]:
    """Retrieve information about one or multiple RDS instances.
    
    <use_case>
    Use this tool to query detailed information about Amazon RDS instances in your AWS account.
    This provides the raw data from the AWS API and is useful for advanced filtering and pagination.
    </use_case>
    
    <important_notes>
    1. If db_instance_identifier is specified, information is returned only for that instance
    2. The filters parameter allows complex querying based on instance attributes
    3. Pagination is supported through marker and max_records parameters
    4. The response includes the complete AWS API data structure
    5. Results are filtered to the AWS region specified in your environment configuration
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `DBInstances`: List of DB instance descriptions from the AWS API
    - `formatted_instances`: List of simplified instance representations
    - `Marker`: Pagination token for retrieving the next set of results (if applicable)
    
    Each DB instance description in the API response contains extensive details including:
    - Endpoint connection information
    - Complete configuration parameters
    - Status information
    - Associated resources and cluster information
    - Storage configuration
    - Security settings
    - Backup configuration
    
    <examples>
    Example usage scenarios:
    1. Get details about a specific instance:
       - db_instance_identifier="production-db-instance"
    
    2. Filter instances by engine type:
       - filters=[{"Name": "engine", "Values": ["aurora-postgresql"]}]
    
    3. Get the first 20 instances, then paginate:
       - max_records=20
       (Then in subsequent calls)
       - max_records=20
       - marker="token-from-previous-response"
    
    4. Complex filtering with multiple attributes:
       - filters=[
           {"Name": "instance-type", "Values": ["db.r5.large"]},
           {"Name": "engine", "Values": ["aurora-mysql"]}
         ]
    </examples>
    """
    return await instance.describe_db_instances(
        ctx=ctx,
        rds_client=get_rds_client(),
        db_instance_identifier=db_instance_identifier,
        filters=filters,
        marker=marker,
        max_records=max_records,
    )


@mcp.tool(name='create_db_cluster_snapshot')
async def create_db_cluster_snapshot_tool(
    ctx: Context,
    db_cluster_snapshot_identifier: str = Field(description='The identifier for the DB cluster snapshot'),
    db_cluster_identifier: str = Field(description='The identifier of the DB cluster'),
    tags: Optional[List[Dict[str, str]]] = Field(default=None, description='A list of tags to apply to the snapshot'),
) -> Dict[str, Any]:
    """Creates a manual snapshot of an RDS DB cluster.
    
    <use_case>
    Use this tool to create a point-in-time snapshot of an Amazon RDS DB cluster.
    Manual snapshots are useful for long-term backups, before making major changes,
    or for creating copies of databases for development or testing purposes.
    </use_case>
    
    <important_notes>
    1. Snapshot identifiers must follow naming rules: 1-255 alphanumeric characters
    2. Creating a snapshot does not interrupt database operations
    3. Manual snapshots are retained indefinitely until explicitly deleted
    4. Snapshots can be used to restore a cluster to the exact point when the snapshot was taken
    5. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the snapshot creation
    - `formatted_snapshot`: A simplified representation of the snapshot
    - `DBClusterSnapshot`: The full AWS API response containing snapshot details including:
      - `DBClusterSnapshotIdentifier`: The snapshot identifier
      - `DBClusterIdentifier`: The source cluster identifier
      - `SnapshotCreateTime`: When the snapshot was created
      - `Status`: The current status (usually "creating" initially)
      - Other snapshot details like engine version, port, etc.
    
    <examples>
    Example usage scenarios:
    1. Create a backup before major changes:
       - db_cluster_snapshot_identifier="pre-upgrade-snapshot"
       - db_cluster_identifier="production-db-cluster"
    
    2. Create a tagged snapshot for specific purposes:
       - db_cluster_snapshot_identifier="monthly-backup-jan2023" 
       - db_cluster_identifier="finance-db-cluster"
       - tags=[{"Purpose": "Monthly Backup", "Department": "Finance"}]
    </examples>
    """
    return await backup.create_db_cluster_snapshot(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_snapshot_identifier=db_cluster_snapshot_identifier,
        db_cluster_identifier=db_cluster_identifier,
        tags=tags,
    )


@mcp.tool(name='restore_db_cluster_from_snapshot')
async def restore_db_cluster_from_snapshot_tool(
    ctx: Context,
    db_cluster_identifier: str = Field(description='The identifier for the new DB cluster'),
    snapshot_identifier: str = Field(description='The identifier of the DB cluster snapshot to restore from'),
    engine: str = Field(description='The database engine to use'),
    vpc_security_group_ids: Optional[List[str]] = Field(default=None, description='A list of VPC security group IDs'),
    db_subnet_group_name: Optional[str] = Field(default=None, description='A DB subnet group to associate with the restored DB cluster'),
    engine_version: Optional[str] = Field(default=None, description='The version number of the database engine to use'),
    port: Optional[int] = Field(default=None, description='The port number on which the DB cluster accepts connections'),
    availability_zones: Optional[List[str]] = Field(default=None, description='A list of Availability Zones'),
    tags: Optional[List[Dict[str, str]]] = Field(default=None, description='A list of tags to apply to the restored cluster'),
) -> Dict[str, Any]:
    """Creates a new RDS DB cluster from a DB cluster snapshot.
    
    <use_case>
    Use this tool to restore an Amazon RDS DB cluster from a previously created snapshot.
    This is useful for recovery operations, creating development copies of production
    databases, or migrating databases between environments.
    </use_case>
    
    <important_notes>
    1. The new cluster identifier must be unique and follow naming rules
    2. The engine must match or be compatible with the engine of the source snapshot
    3. The restored cluster will not include any instances - you'll need to create them separately
    4. When run with readonly=True (default), this operation will be simulated but not actually performed
    5. Engine version can be upgraded during restore but not downgraded
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the restoration
    - `formatted_cluster`: A simplified representation of the new cluster
    - `DBCluster`: The full AWS API response containing cluster details including:
      - `DBClusterIdentifier`: The new cluster identifier
      - `Status`: The current status (usually "creating" initially)
      - `Engine`, `EngineVersion`: Database engine information
      - Other cluster configuration details
    
    <examples>
    Example usage scenarios:
    1. Restore for disaster recovery:
       - db_cluster_identifier="restored-production-db"
       - snapshot_identifier="pre-incident-snapshot"
       - engine="aurora-mysql"
    
    2. Create a development copy with custom settings:
       - db_cluster_identifier="dev-db-cluster"
       - snapshot_identifier="production-snapshot-20230615"
       - engine="aurora-postgresql"
       - vpc_security_group_ids=["sg-12345678"]
       - engine_version="13.6"
    </examples>
    """
    return await backup.restore_db_cluster_from_snapshot(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_identifier=db_cluster_identifier,
        snapshot_identifier=snapshot_identifier,
        engine=engine,
        vpc_security_group_ids=vpc_security_group_ids,
        db_subnet_group_name=db_subnet_group_name,
        engine_version=engine_version,
        port=port,
        availability_zones=availability_zones,
        tags=tags,
    )


@mcp.tool(name='restore_db_cluster_to_point_in_time')
async def restore_db_cluster_to_point_in_time_tool(
    ctx: Context,
    db_cluster_identifier: str = Field(description='The identifier for the new DB cluster'),
    source_db_cluster_identifier: str = Field(description='The identifier of the source DB cluster'),
    restore_to_time: Optional[str] = Field(default=None, description='The date and time to restore the cluster to (format: YYYY-MM-DDTHH:MM:SSZ)'),
    use_latest_restorable_time: Optional[bool] = Field(default=None, description='Whether to restore to the latest restorable backup time'),
    port: Optional[int] = Field(default=None, description='The port number for the new DB cluster'),
    db_subnet_group_name: Optional[str] = Field(default=None, description='The DB subnet group name to use for the new DB cluster'),
    vpc_security_group_ids: Optional[List[str]] = Field(default=None, description='A list of VPC security group IDs'),
    tags: Optional[List[Dict[str, str]]] = Field(default=None, description='A list of tags to apply to the restored cluster'),
) -> Dict[str, Any]:
    """Restores a DB cluster to a specific point in time.
    
    <use_case>
    Use this tool to restore an Amazon RDS DB cluster to a specific point in time within the
    retention period. This is useful for recovering from logical errors, failed operations,
    or to retrieve data as it existed at a particular time.
    </use_case>
    
    <important_notes>
    1. The new cluster identifier must be unique and follow naming rules
    2. You must provide either restore_to_time or use_latest_restorable_time
    3. The restore time must be within the backup retention window
    4. The restored cluster will not include any instances - you'll need to create them separately
    5. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the restoration
    - `formatted_cluster`: A simplified representation of the new cluster
    - `DBCluster`: The full AWS API response containing cluster details including:
      - `DBClusterIdentifier`: The new cluster identifier
      - `Status`: The current status (usually "creating" initially)
      - `Engine`, `EngineVersion`: Database engine information
      - Other cluster configuration details
    
    <examples>
    Example usage scenarios:
    1. Restore to a specific timestamp:
       - db_cluster_identifier="recovery-db-cluster"
       - source_db_cluster_identifier="production-db-cluster"
       - restore_to_time="2023-06-15T08:45:00Z"
    
    2. Restore to the latest possible time:
       - db_cluster_identifier="recovery-db-cluster"
       - source_db_cluster_identifier="production-db-cluster"
       - use_latest_restorable_time=true
    </examples>
    """
    return await backup.restore_db_cluster_to_point_in_time(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_identifier=db_cluster_identifier,
        source_db_cluster_identifier=source_db_cluster_identifier,
        restore_to_time=restore_to_time,
        use_latest_restorable_time=use_latest_restorable_time,
        port=port,
        db_subnet_group_name=db_subnet_group_name,
        vpc_security_group_ids=vpc_security_group_ids,
        tags=tags,
    )


@mcp.tool(name='delete_db_cluster_snapshot')
async def delete_db_cluster_snapshot_tool(
    ctx: Context,
    db_cluster_snapshot_identifier: str = Field(description='The identifier for the DB cluster snapshot'),
    confirmation_token: Optional[str] = Field(default=None, description='The confirmation token for the operation - required for destructive operations'),
) -> Dict[str, Any]:
    """Deletes a DB cluster snapshot.
    
    <use_case>
    Use this tool to permanently delete an Amazon RDS DB cluster snapshot. This can be used
    for managing storage costs by removing unnecessary or outdated snapshots.
    </use_case>
    
    <important_notes>
    1. This is a destructive operation that permanently deletes the snapshot
    2. A confirmation token is required for safety - first call without token to receive one
    3. Once deleted, a snapshot cannot be recovered
    4. When run with readonly=True (default), this operation will be simulated but not actually performed
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
    - `formatted_snapshot`: A simplified representation of the deleted snapshot
    - `DBClusterSnapshot`: The full AWS API response containing snapshot details
    
    <examples>
    Example usage scenarios:
    1. Start deletion process (get confirmation token):
       - db_cluster_snapshot_identifier="old-backup-snapshot"
    
    2. Confirm deletion (with confirmation token):
       - db_cluster_snapshot_identifier="old-backup-snapshot"
       - confirmation_token="abc123xyz" (token received from step 1)
    </examples>
    """
    return await backup.delete_db_cluster_snapshot(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_snapshot_identifier=db_cluster_snapshot_identifier,
        confirmation_token=confirmation_token,
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


# ===== PARAMETER MANAGEMENT TOOLS =====

@mcp.tool(name='create_db_cluster_parameter_group')
async def create_db_cluster_parameter_group_tool(
    ctx: Context,
    db_cluster_parameter_group_name: str = Field(description='The name of the DB cluster parameter group'),
    db_parameter_group_family: str = Field(description='The DB parameter group family name'),
    description: str = Field(description='The description for the DB cluster parameter group'),
    tags: Optional[List[Dict[str, str]]] = Field(default=None, description='A list of tags to apply to the parameter group'),
) -> Dict[str, Any]:
    """Create a new custom DB cluster parameter group.
    
    <use_case>
    Use this tool to create a custom parameter group for DB clusters, allowing you to customize
    database engine parameters according to your specific requirements. Custom parameter groups
    let you optimize database performance, security, and behavior.
    </use_case>
    
    <important_notes>
    1. Parameter group names must be 1-255 letters, numbers, or hyphens
    2. Parameter group names must start with a letter and cannot end with a hyphen
    3. You must specify a valid DB parameter group family (e.g., 'mysql8.0', 'aurora-postgresql13')
    4. The parameter group family determines which parameters are available
    5. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the creation
    - `formatted_parameter_group`: A simplified representation of the parameter group
    - `DBClusterParameterGroup`: The full AWS API response
    
    <examples>
    Example usage scenarios:
    1. Create a parameter group for a MySQL cluster:
       - db_cluster_parameter_group_name="prod-mysql-params"
       - db_parameter_group_family="mysql8.0"
       - description="Production MySQL 8.0 parameters with optimized settings"
    
    2. Create a parameter group for an Aurora PostgreSQL cluster:
       - db_cluster_parameter_group_name="data-warehouse-params"
       - db_parameter_group_family="aurora-postgresql13"
       - description="Data warehouse optimized parameters"
       - tags=[{"Environment": "Production", "Team": "Data"}]
    </examples>
    """
    return await parameter.create_db_cluster_parameter_group(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_parameter_group_name=db_cluster_parameter_group_name,
        db_parameter_group_family=db_parameter_group_family,
        description=description,
        tags=tags,
    )


@mcp.tool(name='modify_db_cluster_parameter_group')
async def modify_db_cluster_parameter_group_tool(
    ctx: Context,
    db_cluster_parameter_group_name: str = Field(description='The name of the DB cluster parameter group'),
    parameters: List[Dict[str, Any]] = Field(description='The parameters to modify'),
) -> Dict[str, Any]:
    """Modify parameters in a DB cluster parameter group.
    
    <use_case>
    Use this tool to update parameter values in an existing DB cluster parameter group.
    This allows you to tune database engine configuration to optimize performance,
    security, and behavior according to your specific workload requirements.
    </use_case>
    
    <important_notes>
    1. Each parameter object must contain 'name' and 'value' keys
    2. The 'apply_method' can be 'immediate' or 'pending-reboot'
    3. Not all parameters can be modified
    4. Some parameter changes require a database reboot to take effect
    5. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `message`: Success message confirming the modification
    - `parameters_modified`: Number of parameters that were modified
    - `formatted_parameters`: A sample of the parameters in the group
    - `total_parameters`: Total number of parameters in the group
    - `DBClusterParameterGroupStatus`: The AWS API response
    
    <examples>
    Example usage scenarios:
    1. Increase the maximum connections:
       - db_cluster_parameter_group_name="prod-mysql-params"
       - parameters=[{"name": "max_connections", "value": "1000", "apply_method": "pending-reboot"}]
    
    2. Modify multiple parameters:
       - db_cluster_parameter_group_name="data-warehouse-params"
       - parameters=[
           {"name": "shared_buffers", "value": "4096", "apply_method": "pending-reboot"},
           {"name": "max_connections", "value": "200", "apply_method": "pending-reboot"},
           {"name": "log_min_duration_statement", "value": "500", "apply_method": "immediate"}
         ]
    </examples>
    """
    return await parameter.modify_db_cluster_parameter_group(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_parameter_group_name=db_cluster_parameter_group_name,
        parameters=parameters,
    )


@mcp.tool(name='reset_db_cluster_parameter_group')
async def reset_db_cluster_parameter_group_tool(
    ctx: Context,
    db_cluster_parameter_group_name: str = Field(description='The name of the DB cluster parameter group'),
    reset_all_parameters: bool = Field(default=False, description='Whether to reset all parameters'),
    parameters: Optional[List[Dict[str, Any]]] = Field(default=None, description='The parameters to reset (if not resetting all)'),
    confirmation_token: Optional[str] = Field(default=None, description='The confirmation token for the operation - required for destructive operations'),
) -> Dict[str, Any]:
    """Reset parameters in a DB cluster parameter group to their default values.
    
    <use_case>
    Use this tool to reset parameters in a DB cluster parameter group to their default values.
    This can be used to revert configuration changes or to return to a known-good state if
    custom parameter settings are causing issues.
    </use_case>
    
    <important_notes>
    1. This operation requires explicit confirmation with a confirmation token
    2. You can choose to reset all parameters or a specific subset
    3. If resetting specific parameters, each parameter object must contain a 'name' key
    4. The 'apply_method' can be 'immediate' or 'pending-reboot'
    5. Some parameter resets require a database reboot to take effect
    6. When run with readonly=True (default), this operation will be simulated but not actually performed
    </important_notes>
    
    ## Response structure
    If called without a confirmation token:
    - `requires_confirmation`: Always true
    - `warning`: Warning message about the reset
    - `impact`: Description of the impact of resetting parameters
    - `confirmation_token`: Token to use in a subsequent call
    - `message`: Instructions for confirming the reset
    
    If called with a valid confirmation token:
    - `message`: Success message confirming the reset
    - `parameters_reset`: Number of parameters that were reset
    - `DBClusterParameterGroupStatus`: The AWS API response
    
    <examples>
    Example usage scenarios:
    1. Start reset process for all parameters (get confirmation token):
       - db_cluster_parameter_group_name="prod-mysql-params"
       - reset_all_parameters=true
    
    2. Confirm reset for all parameters:
       - db_cluster_parameter_group_name="prod-mysql-params"
       - reset_all_parameters=true
       - confirmation_token="abc123xyz" (token received from step 1)
    
    3. Reset specific parameters:
       - db_cluster_parameter_group_name="prod-mysql-params"
       - reset_all_parameters=false
       - parameters=[
           {"name": "max_connections", "apply_method": "pending-reboot"},
           {"name": "shared_buffers", "apply_method": "pending-reboot"}
         ]
       - confirmation_token="abc123xyz" (token received from separate call)
    </examples>
    """
    return await parameter.reset_db_cluster_parameter_group(
        ctx=ctx,
        rds_client=get_rds_client(),
        readonly=_readonly,
        db_cluster_parameter_group_name=db_cluster_parameter_group_name,
        reset_all_parameters=reset_all_parameters,
        parameters=parameters,
        confirmation_token=confirmation_token,
    )


@mcp.tool(name='describe_db_cluster_parameters')
async def describe_db_cluster_parameters_tool(
    ctx: Context,
    db_cluster_parameter_group_name: str = Field(description='The name of the DB cluster parameter group'),
    source: Optional[str] = Field(default=None, description='The parameter source'),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    max_records: Optional[int] = Field(default=None, description='Maximum number of records to return'),
) -> Dict[str, Any]:
    """Returns a list of parameters for a DB cluster parameter group.
    
    <use_case>
    Use this tool to retrieve detailed information about the parameters in a specific
    DB cluster parameter group. This allows you to inspect parameter settings before
    making modifications or to understand current database configuration.
    </use_case>
    
    <important_notes>
    1. The source parameter can filter results by parameter origin ('engine-default', 'user', or 'system')
    2. Pagination is supported through marker and max_records parameters
    3. Parameters have different data types, allowed values, and modifiability
    4. Each parameter includes description and metadata about its purpose
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `formatted_parameters`: A simplified representation of parameters
    - `Parameters`: The full list of parameters from the AWS API
    - `Marker`: Pagination token for retrieving the next set of results (if applicable)
    
    <examples>
    Example usage scenarios:
    1. List all parameters in a group:
       - db_cluster_parameter_group_name="prod-mysql-params"
    
    2. List only user-modified parameters:
       - db_cluster_parameter_group_name="prod-mysql-params"
       - source="user"
    
    3. Paginate through a large parameter list:
       - db_cluster_parameter_group_name="prod-mysql-params"
       - max_records=100
       (Then in subsequent calls)
       - db_cluster_parameter_group_name="prod-mysql-params"
       - max_records=100
       - marker="token-from-previous-response"
    </examples>
    """
    return await parameter.describe_db_cluster_parameters(
        ctx=ctx,
        rds_client=get_rds_client(),
        db_cluster_parameter_group_name=db_cluster_parameter_group_name,
        source=source,
        marker=marker,
        max_records=max_records,
    )


@mcp.tool(name='describe_db_instance_parameters')
async def describe_db_instance_parameters_tool(
    ctx: Context,
    db_parameter_group_name: str = Field(description='The name of the DB parameter group'),
    source: Optional[str] = Field(default=None, description='The parameter source'),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    max_records: Optional[int] = Field(default=None, description='Maximum number of records to return'),
) -> Dict[str, Any]:
    """Returns a list of parameters for a DB instance parameter group.
    
    <use_case>
    Use this tool to retrieve detailed information about the parameters in a specific
    DB instance parameter group. This allows you to inspect parameter settings before
    making modifications or to understand current database configuration.
    </use_case>
    
    <important_notes>
    1. The source parameter can filter results by parameter origin ('engine-default', 'user', or 'system')
    2. Pagination is supported through marker and max_records parameters
    3. Parameters have different data types, allowed values, and modifiability
    4. Each parameter includes description and metadata about its purpose
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `formatted_parameters`: A simplified representation of parameters
    - `Parameters`: The full list of parameters from the AWS API
    - `Marker`: Pagination token for retrieving the next set of results (if applicable)
    
    <examples>
    Example usage scenarios:
    1. List all parameters in a group:
       - db_parameter_group_name="prod-oracle-params"
    
    2. List only user-modified parameters:
       - db_parameter_group_name="prod-oracle-params"
       - source="user"
    
    3. Paginate through a large parameter list:
       - db_parameter_group_name="prod-oracle-params"
       - max_records=100
       (Then in subsequent calls)
       - db_parameter_group_name="prod-oracle-params"
       - max_records=100
       - marker="token-from-previous-response"
    </examples>
    """
    return await parameter.describe_db_instance_parameters(
        ctx=ctx,
        rds_client=get_rds_client(),
        db_parameter_group_name=db_parameter_group_name,
        source=source,
        marker=marker,
        max_records=max_records,
    )


@mcp.tool(name='describe_db_cluster_parameter_groups')
async def describe_db_cluster_parameter_groups_tool(
    ctx: Context,
    db_cluster_parameter_group_name: Optional[str] = Field(default=None, description='The name of the DB cluster parameter group'),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    max_records: Optional[int] = Field(default=None, description='Maximum number of records to return'),
) -> Dict[str, Any]:
    """Returns a list of DB cluster parameter group descriptions.
    
    <use_case>
    Use this tool to discover and examine DB cluster parameter groups in your AWS account.
    This helps you identify existing parameter groups that can be applied to clusters or
    that may need modification.
    </use_case>
    
    <important_notes>
    1. If db_cluster_parameter_group_name is provided, only that parameter group's details are returned
    2. Pagination is supported through marker and max_records parameters
    3. Each parameter group includes information about its family and description
    4. This tool provides a high-level view of parameter groups - use describe_db_cluster_parameters 
       to see the actual parameters within a group
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `formatted_parameter_groups`: A simplified representation of parameter groups
    - `DBClusterParameterGroups`: The full list of parameter groups from the AWS API
    - `Marker`: Pagination token for retrieving the next set of results (if applicable)
    
    <examples>
    Example usage scenarios:
    1. List all cluster parameter groups:
       (no parameters)
    
    2. Get details for a specific parameter group:
       - db_cluster_parameter_group_name="prod-mysql-params"
    
    3. Paginate through many parameter groups:
       - max_records=20
       (Then in subsequent calls)
       - max_records=20
       - marker="token-from-previous-response"
    </examples>
    """
    return await parameter.describe_db_cluster_parameter_groups(
        ctx=ctx,
        rds_client=get_rds_client(),
        db_cluster_parameter_group_name=db_cluster_parameter_group_name,
        marker=marker,
        max_records=max_records,
    )


@mcp.tool(name='describe_db_instance_parameter_groups')
async def describe_db_instance_parameter_groups_tool(
    ctx: Context,
    db_parameter_group_name: Optional[str] = Field(default=None, description='The name of the DB parameter group'),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    max_records: Optional[int] = Field(default=None, description='Maximum number of records to return'),
) -> Dict[str, Any]:
    """Returns a list of DB instance parameter group descriptions.
    
    <use_case>
    Use this tool to discover and examine DB instance parameter groups in your AWS account.
    This helps you identify existing parameter groups that can be applied to instances or
    that may need modification.
    </use_case>
    
    <important_notes>
    1. If db_parameter_group_name is provided, only that parameter group's details are returned
    2. Pagination is supported through marker and max_records parameters
    3. Each parameter group includes information about its family and description
    4. This tool provides a high-level view of parameter groups - use describe_db_instance_parameters 
       to see the actual parameters within a group
    </important_notes>
    
    ## Response structure
    Returns a dictionary with the following keys:
    - `formatted_parameter_groups`: A simplified representation of parameter groups
    - `DBParameterGroups`: The full list of parameter groups from the AWS API
    - `Marker`: Pagination token for retrieving the next set of results (if applicable)
    
    <examples>
    Example usage scenarios:
    1. List all instance parameter groups:
       (no parameters)
    
    2. Get details for a specific parameter group:
       - db_parameter_group_name="prod-oracle-params"
    
    3. Paginate through many parameter groups:
       - max_records=20
       (Then in subsequent calls)
       - max_records=20
       - marker="token-from-previous-response"
    </examples>
    """
    return await parameter.describe_db_instance_parameter_groups(
        ctx=ctx,
        rds_client=get_rds_client(),
        db_parameter_group_name=db_parameter_group_name,
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
