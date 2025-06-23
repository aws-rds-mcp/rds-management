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

"""Cluster management operations for RDS Management MCP Server."""

import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing_extensions import Annotated
from .constants import (
    CONFIRM_DELETE_CLUSTER,
    CONFIRM_FAILOVER,
    CONFIRM_STOP_CLUSTER,
    ERROR_INVALID_PARAMS,
    ERROR_READONLY_MODE,
    SUCCESS_CREATED,
    SUCCESS_DELETED,
    SUCCESS_MODIFIED,
    SUCCESS_REBOOTED,
    SUCCESS_STARTED,
    SUCCESS_STOPPED,
)
from .utils import (
    add_mcp_tags,
    check_readonly_mode,
    format_aws_response,
    format_cluster_info,
    get_engine_port,
    get_operation_impact,
    handle_aws_error,
    validate_db_identifier,
    add_pending_operation,
    get_pending_operation,
    remove_pending_operation,
)


async def create_db_cluster(
    db_cluster_identifier: Annotated[
        str, Field(description='The identifier for the DB cluster')
    ],
    engine: Annotated[
        str, Field(description='The name of the database engine to be used for this DB cluster (e.g., aurora, aurora-mysql, aurora-postgresql, mysql, postgres, mariadb, oracle, sqlserver)')
    ],
    master_username: Annotated[
        str, Field(description='The name of the master user for the DB cluster')
    ],
    manage_master_user_password: Annotated[
        Optional[bool], Field(description='Specifies whether to manage the master user password with Amazon Web Services Secrets Manager')
    ] = True,
    database_name: Annotated[
        Optional[str], Field(description='The name for your database')
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]], Field(description='A list of EC2 VPC security groups to associate with this DB cluster')
    ] = None,
    db_subnet_group_name: Annotated[
        Optional[str], Field(description='A DB subnet group to associate with this DB cluster')
    ] = None,
    availability_zones: Annotated[
        Optional[List[str]], Field(description='A list of Availability Zones (AZs) where instances in the DB cluster can be created')
    ] = None,
    backup_retention_period: Annotated[
        Optional[int], Field(description='The number of days for which automated backups are retained')
    ] = None,
    port: Annotated[
        Optional[int], Field(description='The port number on which the instances in the DB cluster accept connections')
    ] = None,
    engine_version: Annotated[
        Optional[str], Field(description='The version number of the database engine to use')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Create a new RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        engine: The name of the database engine to be used for this DB cluster
        master_username: The name of the master user for the DB cluster
        manage_master_user_password: Specifies whether to manage the master user password with AWS Secrets Manager
        database_name: The name for your database
        vpc_security_group_ids: A list of EC2 VPC security groups to associate with this DB cluster
        db_subnet_group_name: A DB subnet group to associate with this DB cluster
        availability_zones: A list of Availability Zones (AZs) where instances in the DB cluster can be created
        backup_retention_period: The number of days for which automated backups are retained
        port: The port number on which the instances in the DB cluster accept connections
        engine_version: The version number of the database engine to use
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client
        readonly: Whether server is in readonly mode

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    if not check_readonly_mode('create', readonly, ctx):
        return {'error': ERROR_READONLY_MODE}

    # validate identifier
    if not validate_db_identifier(db_cluster_identifier):
        error_msg = ERROR_INVALID_PARAMS.format('db_cluster_identifier must be 1-63 characters, begin with a letter, and contain only alphanumeric characters and hyphens')
        if ctx:
            await ctx.error(error_msg)
        return {'error': error_msg}

    try:
        params = {
            'DBClusterIdentifier': db_cluster_identifier,
            'Engine': engine,
            'MasterUsername': master_username,
            'ManageMasterUserPassword': manage_master_user_password,
        }

        # add optional parameters if provided
        if database_name:
            params['DatabaseName'] = database_name
        if vpc_security_group_ids:
            params['VpcSecurityGroupIds'] = vpc_security_group_ids
        if db_subnet_group_name:
            params['DBSubnetGroupName'] = db_subnet_group_name
        if availability_zones:
            params['AvailabilityZones'] = availability_zones
        if backup_retention_period is not None:
            params['BackupRetentionPeriod'] = backup_retention_period
        if port is not None:
            params['Port'] = port
        else:
            params['Port'] = get_engine_port(engine)
        if engine_version:
            params['EngineVersion'] = engine_version

        # MCP tags
        params = add_mcp_tags(params)

        logger.info(f"Creating DB cluster {db_cluster_identifier} with engine {engine}")
        response = await asyncio.to_thread(rds_client.create_db_cluster, **params)
        logger.success(f"Successfully created DB cluster {db_cluster_identifier}")
        
        result = format_aws_response(response)
        result['message'] = SUCCESS_CREATED.format(f'DB cluster {db_cluster_identifier}')
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'create_db_cluster({db_cluster_identifier})', e, ctx)


async def modify_db_cluster(
    db_cluster_identifier: Annotated[
        str, Field(description='The identifier for the DB cluster')
    ],
    apply_immediately: Annotated[
        Optional[bool], Field(description='Specifies whether the modifications are applied immediately, or during the next maintenance window')
    ] = None,
    backup_retention_period: Annotated[
        Optional[int], Field(description='The number of days for which automated backups are retained')
    ] = None,
    db_cluster_parameter_group_name: Annotated[
        Optional[str], Field(description='The name of the DB cluster parameter group to use for the DB cluster')
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]], Field(description='A list of EC2 VPC security groups to associate with this DB cluster')
    ] = None,
    port: Annotated[
        Optional[int], Field(description='The port number on which the DB cluster accepts connections')
    ] = None,
    manage_master_user_password: Annotated[
        Optional[bool], Field(description='Specifies whether to manage the master user password with Amazon Web Services Secrets Manager')
    ] = None,
    engine_version: Annotated[
        Optional[str], Field(description='The version number of the database engine to upgrade to')
    ] = None,
    allow_major_version_upgrade: Annotated[
        Optional[bool], Field(description='Indicates whether major version upgrades are allowed')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Modify an existing RDS database cluster configuration.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        apply_immediately: Specifies whether the modifications are applied immediately
        backup_retention_period: The number of days for which automated backups are retained
        db_cluster_parameter_group_name: The name of the DB cluster parameter group to use
        vpc_security_group_ids: A list of EC2 VPC security groups to associate with this DB cluster
        port: The port number on which the DB cluster accepts connections
        manage_master_user_password: Specifies whether to manage the master user password with AWS Secrets Manager
        engine_version: The version number of the database engine to upgrade to
        allow_major_version_upgrade: Indicates whether major version upgrades are allowed
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client
        readonly: Whether server is in readonly mode

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    if not check_readonly_mode('modify', readonly, ctx):
        return {'error': ERROR_READONLY_MODE}

    try:
        params = {
            'DBClusterIdentifier': db_cluster_identifier,
        }

        # add optional parameters if provided
        if apply_immediately is not None:
            params['ApplyImmediately'] = apply_immediately
        if backup_retention_period is not None:
            params['BackupRetentionPeriod'] = backup_retention_period
        if db_cluster_parameter_group_name:
            params['DBClusterParameterGroupName'] = db_cluster_parameter_group_name
        if vpc_security_group_ids:
            params['VpcSecurityGroupIds'] = vpc_security_group_ids
        if port is not None:
            params['Port'] = port
        if manage_master_user_password is not None:
            params['ManageMasterUserPassword'] = manage_master_user_password
        if engine_version:
            params['EngineVersion'] = engine_version
        if allow_major_version_upgrade is not None:
            params['AllowMajorVersionUpgrade'] = allow_major_version_upgrade

        logger.info(f"Modifying DB cluster {db_cluster_identifier}")
        response = await asyncio.to_thread(rds_client.modify_db_cluster, **params)
        logger.success(f"Successfully modified DB cluster {db_cluster_identifier}")
        
        result = format_aws_response(response)
        result['message'] = SUCCESS_MODIFIED.format(f'DB cluster {db_cluster_identifier}')
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'modify_db_cluster({db_cluster_identifier})', e, ctx)


async def delete_db_cluster(
    db_cluster_identifier: Annotated[
        str, Field(description='The identifier for the DB cluster')
    ],
    skip_final_snapshot: Annotated[
        bool, Field(description='Determines whether a final DB snapshot is created before the DB cluster is deleted')
    ],
    final_db_snapshot_identifier: Annotated[
        Optional[str], Field(description='The DB snapshot identifier of the new DB snapshot created when SkipFinalSnapshot is false')
    ] = None,
    confirmation_token: Annotated[
        Optional[str], Field(description='The confirmation token for the operation')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Delete an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        skip_final_snapshot: Determines whether a final DB snapshot is created
        final_db_snapshot_identifier: The DB snapshot identifier if creating final snapshot
        confirmation_token: The confirmation token for the operation
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client
        readonly: Whether server is in readonly mode

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    if not check_readonly_mode('delete', readonly, ctx):
        return {'error': ERROR_READONLY_MODE}

    # confirmation message and impact
    impact = get_operation_impact('delete_db_cluster')
    confirmation_msg = CONFIRM_DELETE_CLUSTER.format(cluster_id=db_cluster_identifier)
    
    # if no confirmation token provided, create a pending operation and return a token
    if not confirmation_token:
        # create parameters for the operation
        params = {
            'db_cluster_identifier': db_cluster_identifier,
            'skip_final_snapshot': skip_final_snapshot,
        }
        
        if not skip_final_snapshot and final_db_snapshot_identifier:
            params['final_db_snapshot_identifier'] = final_db_snapshot_identifier
            
        # add the pending operation and get a token
        token = add_pending_operation('delete_db_cluster', params)
        
        # return the token directly in the response
        return {
            'requires_confirmation': True,
            'warning': confirmation_msg,
            'impact': impact,
            'confirmation_token': token,
            'message': f'WARNING: You are about to delete DB cluster {db_cluster_identifier}. This operation cannot be undone.\n\nTo confirm, please call this function again with the confirmation_token parameter set to this token.'
        }
    
    # if confirmation token provided, check if it's valid
    pending_op = get_pending_operation(confirmation_token)
    if not pending_op:
        return {
            'error': f'Invalid or expired confirmation token. Please request a new token by calling this function without a confirmation_token parameter.'
        }
    
    # extract operation details
    op_type, params, _ = pending_op
    
    # verify that this is the correct operation type
    if op_type != 'delete_db_cluster':
        return {
            'error': f'Invalid operation type. Expected "delete_db_cluster", got "{op_type}".'
        }
    
    # verify that the parameters match
    if params.get('db_cluster_identifier') != db_cluster_identifier:
        return {
            'error': f'Parameter mismatch. The confirmation token is for a different DB cluster.'
        }
    
    try:
        # remove the pending operation
        remove_pending_operation(confirmation_token)
        
        # AWS API parameters
        aws_params = {
            'DBClusterIdentifier': db_cluster_identifier,
            'SkipFinalSnapshot': skip_final_snapshot,
        }

        if not skip_final_snapshot and final_db_snapshot_identifier:
            aws_params['FinalDBSnapshotIdentifier'] = final_db_snapshot_identifier

        logger.info(f"Deleting DB cluster {db_cluster_identifier}")
        response = await asyncio.to_thread(rds_client.delete_db_cluster, **aws_params)
        logger.success(f"Successfully initiated deletion of DB cluster {db_cluster_identifier}")
        
        result = format_aws_response(response)
        result['message'] = SUCCESS_DELETED.format(f'DB cluster {db_cluster_identifier}')
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'delete_db_cluster({db_cluster_identifier})', e, ctx)


async def status_db_cluster(
    db_cluster_identifier: Annotated[
        str, Field(description='The identifier for the DB cluster')
    ],
    action: Annotated[
        str, Field(description='Action to perform: "start", "stop", or "reboot"')
    ],
    confirmation: Annotated[
        Optional[str], Field(description='Confirmation text for destructive operations')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Manage the status of an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        action: Action to perform: "start", "stop", or "reboot"
        confirmation: Confirmation text for destructive operations
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client
        readonly: Whether server is in readonly mode

    Returns:
        Dict[str, Any]: The response from the AWS API
    """

    action = action.lower()
    
    if action not in ["start", "stop", "reboot"]:
        return {
            'error': f"Invalid action: {action}. Must be one of: start, stop, reboot"
        }
    
    # check read-only mode
    if not check_readonly_mode(action, readonly, ctx):
        return {'error': ERROR_READONLY_MODE}
    
    # define confirmation requirements and warning messages for each action
    confirmation_requirements = {
        "start": {
            "required_confirmation": "CONFIRM_START",
            "warning_message": f"WARNING: You are about to start DB cluster {db_cluster_identifier}. Starting a stopped cluster will resume billing charges and may incur costs. To confirm, please provide the confirmation parameter with the value \"CONFIRM_START\".",
            "impact": get_operation_impact('start_db_cluster'),
        },
        "stop": {
            "required_confirmation": "CONFIRM_STOP",
            "warning_message": f"WARNING: You are about to stop DB cluster {db_cluster_identifier}. This will make the database unavailable until it is started again. To confirm, please provide the confirmation parameter with the value \"CONFIRM_STOP\".",
            "impact": get_operation_impact('stop_db_cluster'),
        },
        "reboot": {
            "required_confirmation": "CONFIRM_REBOOT",
            "warning_message": f"WARNING: You are about to reboot DB cluster {db_cluster_identifier}. This will cause a brief interruption in database availability. To confirm, please provide the confirmation parameter with the value \"CONFIRM_REBOOT\".",
            "impact": get_operation_impact('reboot_db_cluster'),
        }
    }
    
    # get confirmation requirements for the current action
    required_confirmation = confirmation_requirements[action]["required_confirmation"]
    warning_message = confirmation_requirements[action]["warning_message"]
    impact = confirmation_requirements[action]["impact"]
    
    # if no confirmation provided, return warning without executing operation
    if not confirmation:
        return {
            'requires_confirmation': True,
            'warning': warning_message,
            'impact': impact,
            'message': warning_message
        }
    
    # if confirmation provided but doesn't match the required confirmation string, return error
    if confirmation != required_confirmation:
        return {
            'error': f'Confirmation value must be exactly "{required_confirmation}" to proceed with this operation. Operation aborted.'
        }

    try:
        if action == "start":
            logger.info(f"Starting DB cluster {db_cluster_identifier}")
            response = await asyncio.to_thread(
                rds_client.start_db_cluster,
                DBClusterIdentifier=db_cluster_identifier
            )
            logger.success(f"Successfully started DB cluster {db_cluster_identifier}")
            
            result = format_aws_response(response)
            result['message'] = SUCCESS_STARTED.format(f'DB cluster {db_cluster_identifier}')
            
        elif action == "stop":
            logger.info(f"Stopping DB cluster {db_cluster_identifier}")
            response = await asyncio.to_thread(
                rds_client.stop_db_cluster,
                DBClusterIdentifier=db_cluster_identifier
            )
            logger.success(f"Successfully stopped DB cluster {db_cluster_identifier}")
            
            result = format_aws_response(response)
            result['message'] = SUCCESS_STOPPED.format(f'DB cluster {db_cluster_identifier}')
            
        elif action == "reboot":
            logger.info(f"Rebooting DB cluster {db_cluster_identifier}")
            response = await asyncio.to_thread(
                rds_client.reboot_db_cluster,
                DBClusterIdentifier=db_cluster_identifier
            )
            logger.success(f"Successfully initiated reboot of DB cluster {db_cluster_identifier}")
            
            result = format_aws_response(response)
            result['message'] = SUCCESS_REBOOTED.format(f'DB cluster {db_cluster_identifier}')
        
        # add formatted cluster info to the result
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'status_db_cluster({db_cluster_identifier}, {action})', e, ctx)


async def failover_db_cluster(
    db_cluster_identifier: Annotated[
        str, Field(description='The identifier for the DB cluster')
    ],
    target_db_instance_identifier: Annotated[
        Optional[str], Field(description='The name of the instance to promote to the primary instance')
    ] = None,
    confirmation: Annotated[
        Optional[str], Field(description='Confirmation text for destructive operation')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Force a failover for an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        target_db_instance_identifier: The name of the instance to promote to primary
        confirmation: Confirmation text for destructive operation
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client
        readonly: Whether server is in readonly mode

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    if not check_readonly_mode('failover', readonly, ctx):
        return {'error': ERROR_READONLY_MODE}

    # get confirmation message and impact
    impact = get_operation_impact('failover_db_cluster')
    confirmation_msg = CONFIRM_FAILOVER.format(cluster_id=db_cluster_identifier)
    
    # if no confirmation provided, return warning without executing operation
    if not confirmation:
        return {
            'requires_confirmation': True,
            'warning': confirmation_msg,
            'impact': impact,
            'message': f'WARNING: You are about to initiate a failover for DB cluster {db_cluster_identifier}. This will cause a brief interruption in database availability. To confirm, please provide the confirmation parameter with the value "CONFIRM_FAILOVER".'
        }
    
    # if confirmation provided but doesn't match the required confirmation string, return error
    if confirmation != "CONFIRM_FAILOVER":
        return {
            'error': f'Confirmation value must be exactly "CONFIRM_FAILOVER" to proceed with this destructive operation. Operation aborted.'
        }

    try:
        params = {
            'DBClusterIdentifier': db_cluster_identifier,
        }
        
        if target_db_instance_identifier:
            params['TargetDBInstanceIdentifier'] = target_db_instance_identifier

        logger.info(f"Initiating failover for DB cluster {db_cluster_identifier}")
        response = await asyncio.to_thread(rds_client.failover_db_cluster, **params)
        logger.success(f"Successfully initiated failover for DB cluster {db_cluster_identifier}")
        
        result = format_aws_response(response)
        result['message'] = f'Successfully initiated failover for DB cluster {db_cluster_identifier}'
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'failover_db_cluster({db_cluster_identifier})', e, ctx)

# describes_db_clusters tool in case the MCP Host does not support MCP resources
async def describe_db_clusters(
    db_cluster_identifier: Annotated[
        Optional[str], Field(description='The user-supplied DB cluster identifier. If this parameter is specified, information from only the specific DB cluster is returned')
    ] = None,
    filters: Annotated[
        Optional[List[Dict[str, Any]]], Field(description='A filter that specifies one or more DB clusters to describe')
    ] = None,
    marker: Annotated[
        Optional[str], Field(description='An optional pagination token provided by a previous DescribeDBClusters request')
    ] = None,
    max_records: Annotated[
        Optional[int], Field(description='The maximum number of records to include in the response')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
) -> Dict[str, Any]:
    """Retrieve information about one or multiple Aurora clusters.

    Args:
        db_cluster_identifier: The user-supplied DB cluster identifier
        filters: A filter that specifies one or more DB clusters to describe
        marker: An optional pagination token
        max_records: The maximum number of records to include in the response
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    try:
        params = {}
        
        if db_cluster_identifier:
            params['DBClusterIdentifier'] = db_cluster_identifier
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        if max_records:
            params['MaxRecords'] = max_records

        logger.info(f"Describing DB clusters")
        response = await asyncio.to_thread(rds_client.describe_db_clusters, **params)
        
        result = format_aws_response(response)
        
        # format cluster information for better readability
        if 'DBClusters' in result:
            result['formatted_clusters'] = [
                format_cluster_info(cluster) for cluster in result['DBClusters']
            ]
        
        return result
    except Exception as e:
        return await handle_aws_error('describe_db_clusters', e, ctx)
