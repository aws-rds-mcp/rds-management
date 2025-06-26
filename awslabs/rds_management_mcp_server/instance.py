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

"""Instance management operations for RDS Management MCP Server."""

import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing_extensions import Annotated
from .constants import (
    CONFIRM_DELETE_INSTANCE,
    CONFIRM_REBOOT,
    CONFIRM_STOP,
    CONFIRM_START,
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
    format_instance_info,
    get_operation_impact,
    handle_aws_error,
    validate_db_identifier,
    add_pending_operation,
    get_pending_operation,
    remove_pending_operation,
)


async def create_db_instance(
    db_instance_identifier: Annotated[
        str, Field(description='The DB instance identifier')
    ],
    db_cluster_identifier: Annotated[
        str, Field(description='The identifier of the DB cluster that the instance will belong to')
    ],
    db_instance_class: Annotated[
        str, Field(description='The compute and memory capacity of the DB instance (e.g., db.r5.large)')
    ],
    availability_zone: Annotated[
        Optional[str], Field(description='The Availability Zone (AZ) where the DB instance will be created')
    ] = None,
    engine: Annotated[
        Optional[str], Field(description='The name of the database engine to be used for this instance')
    ] = None,
    publicly_accessible: Annotated[
        Optional[bool], Field(description='Specifies whether the DB instance is publicly accessible')
    ] = None,
    tags: Annotated[
        Optional[List[Dict[str, str]]], Field(description='A list of tags to assign to the DB instance')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Create a new RDS DB instance within an existing DB cluster.

    Args:
        db_instance_identifier: The DB instance identifier
        db_cluster_identifier: The identifier of the DB cluster
        db_instance_class: The compute and memory capacity of the DB instance
        availability_zone: The Availability Zone where the DB instance will be created
        engine: The name of the database engine
        publicly_accessible: Whether the DB instance is publicly accessible
        tags: A list of tags to assign to the DB instance
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client
        readonly: Whether server is in readonly mode

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    if not check_readonly_mode('create', readonly, ctx):
        return {'error': ERROR_READONLY_MODE}

    # Validate identifier
    if not validate_db_identifier(db_instance_identifier):
        error_msg = ERROR_INVALID_PARAMS.format('db_instance_identifier must be 1-63 characters, begin with a letter, and contain only alphanumeric characters and hyphens')
        if ctx:
            await ctx.error(error_msg)
        return {'error': error_msg}

    try:
        params = {
            'DBInstanceIdentifier': db_instance_identifier,
            'DBClusterIdentifier': db_cluster_identifier,
            'DBInstanceClass': db_instance_class,
        }

        # Add optional parameters if provided
        if availability_zone:
            params['AvailabilityZone'] = availability_zone
        if engine:
            params['Engine'] = engine
        if publicly_accessible is not None:
            params['PubliclyAccessible'] = publicly_accessible
        if tags:
            params['Tags'] = tags
        else:
            # Add default MCP tags
            params = add_mcp_tags(params)

        logger.info(f"Creating DB instance {db_instance_identifier} in cluster {db_cluster_identifier}")
        response = await asyncio.to_thread(rds_client.create_db_instance, **params)
        logger.success(f"Successfully created DB instance {db_instance_identifier}")
        
        result = format_aws_response(response)
        result['message'] = SUCCESS_CREATED.format(f'DB instance {db_instance_identifier}')
        result['formatted_instance'] = format_instance_info(result.get('DBInstance', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'create_db_instance({db_instance_identifier})', e, ctx)


async def modify_db_instance(
    db_instance_identifier: Annotated[
        str, Field(description='The DB instance identifier')
    ],
    apply_immediately: Annotated[
        Optional[bool], Field(description='Specifies whether the modifications are applied immediately, or during the next maintenance window')
    ] = None,
    db_instance_class: Annotated[
        Optional[str], Field(description='The new compute and memory capacity of the DB instance')
    ] = None,
    db_parameter_group_name: Annotated[
        Optional[str], Field(description='The name of the DB parameter group to apply to the DB instance')
    ] = None,
    publicly_accessible: Annotated[
        Optional[bool], Field(description='Specifies whether the DB instance is publicly accessible')
    ] = None,
    auto_minor_version_upgrade: Annotated[
        Optional[bool], Field(description='Indicates whether minor engine upgrades are applied automatically to the DB instance during the maintenance window')
    ] = None,
    preferred_maintenance_window: Annotated[
        Optional[str], Field(description='The weekly time range during which system maintenance can occur (e.g., sun:05:00-sun:06:00)')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Modify an existing RDS database instance.

    Args:
        db_instance_identifier: The DB instance identifier
        apply_immediately: Whether modifications are applied immediately
        db_instance_class: The new compute and memory capacity
        db_parameter_group_name: The name of the DB parameter group
        publicly_accessible: Whether the DB instance is publicly accessible
        auto_minor_version_upgrade: Whether minor upgrades are applied automatically
        preferred_maintenance_window: The weekly maintenance window
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
            'DBInstanceIdentifier': db_instance_identifier,
        }

        # Add optional parameters if provided
        if apply_immediately is not None:
            params['ApplyImmediately'] = apply_immediately
        if db_instance_class:
            params['DBInstanceClass'] = db_instance_class
        if db_parameter_group_name:
            params['DBParameterGroupName'] = db_parameter_group_name
        if publicly_accessible is not None:
            params['PubliclyAccessible'] = publicly_accessible
        if auto_minor_version_upgrade is not None:
            params['AutoMinorVersionUpgrade'] = auto_minor_version_upgrade
        if preferred_maintenance_window:
            params['PreferredMaintenanceWindow'] = preferred_maintenance_window

        logger.info(f"Modifying DB instance {db_instance_identifier}")
        response = await asyncio.to_thread(rds_client.modify_db_instance, **params)
        logger.success(f"Successfully modified DB instance {db_instance_identifier}")
        
        result = format_aws_response(response)
        result['message'] = SUCCESS_MODIFIED.format(f'DB instance {db_instance_identifier}')
        result['formatted_instance'] = format_instance_info(result.get('DBInstance', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'modify_db_instance({db_instance_identifier})', e, ctx)


async def delete_db_instance(
    db_instance_identifier: Annotated[
        str, Field(description='The DB instance identifier')
    ],
    skip_final_snapshot: Annotated[
        bool, Field(description='Determines whether a final DB snapshot is created before the DB instance is deleted')
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
    """Delete an RDS database instance.

    Args:
        db_instance_identifier: The DB instance identifier
        skip_final_snapshot: Whether to skip creating a final snapshot
        final_db_snapshot_identifier: The snapshot identifier if creating final snapshot
        confirmation_token: The confirmation token for the operation
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client
        readonly: Whether server is in readonly mode

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    if not check_readonly_mode('delete', readonly, ctx):
        return {'error': ERROR_READONLY_MODE}

    # Get confirmation message and impact
    impact = get_operation_impact('delete_db_instance')
    confirmation_msg = CONFIRM_DELETE_INSTANCE.format(instance_id=db_instance_identifier)
    
    # If no confirmation token provided, create a pending operation and return a token
    if not confirmation_token:
        # Create parameters for the operation
        params = {
            'db_instance_identifier': db_instance_identifier,
            'skip_final_snapshot': skip_final_snapshot,
        }
        
        if not skip_final_snapshot and final_db_snapshot_identifier:
            params['final_db_snapshot_identifier'] = final_db_snapshot_identifier
            
        # Add the pending operation and get a token
        token = add_pending_operation('delete_db_instance', params)
        
        # Return the token directly in the response
        return {
            'requires_confirmation': True,
            'warning': confirmation_msg,
            'impact': impact,
            'confirmation_token': token,
            'message': f'WARNING: You are about to delete DB instance {db_instance_identifier}. This operation cannot be undone.\n\nTo confirm, please copy the following confirmation token:\n\n{token}\n\nThen call this function again with the confirmation_token parameter set to this token.'
        }
    
    # If confirmation token provided, check if it's valid
    pending_op = get_pending_operation(confirmation_token)
    if not pending_op:
        return {
            'error': f'Invalid or expired confirmation token. Please request a new token by calling this function without a confirmation_token parameter.'
        }
    
    # Extract operation details
    op_type, params, _ = pending_op
    
    # Verify that this is the correct operation type
    if op_type != 'delete_db_instance':
        return {
            'error': f'Invalid operation type. Expected "delete_db_instance", got "{op_type}".'
        }
    
    # Verify that the parameters match
    if params.get('db_instance_identifier') != db_instance_identifier:
        return {
            'error': f'Parameter mismatch. The confirmation token is for a different DB instance.'
        }
    
    try:
        # Remove the pending operation
        remove_pending_operation(confirmation_token)
        
        # Prepare AWS API parameters
        aws_params = {
            'DBInstanceIdentifier': db_instance_identifier,
            'SkipFinalSnapshot': skip_final_snapshot,
        }

        if not skip_final_snapshot and final_db_snapshot_identifier:
            aws_params['FinalDBSnapshotIdentifier'] = final_db_snapshot_identifier

        logger.info(f"Deleting DB instance {db_instance_identifier}")
        response = await asyncio.to_thread(rds_client.delete_db_instance, **aws_params)
        logger.success(f"Successfully initiated deletion of DB instance {db_instance_identifier}")
        
        result = format_aws_response(response)
        result['message'] = SUCCESS_DELETED.format(f'DB instance {db_instance_identifier}')
        result['formatted_instance'] = format_instance_info(result.get('DBInstance', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'delete_db_instance({db_instance_identifier})', e, ctx)


async def status_db_instance(
    db_instance_identifier: Annotated[
        str, Field(description='The DB instance identifier')
    ],
    action: Annotated[
        str, Field(description='Action to perform: "start", "stop", or "reboot"')
    ],
    confirmation: Annotated[
        Optional[str], Field(description='Confirmation text for destructive operations - required for all actions')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    """Manage the status of an RDS database instance.

    Args:
        db_instance_identifier: The DB instance identifier
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
            "required_confirmation": CONFIRM_START,
            "warning_message": f"WARNING: You are about to start DB instance {db_instance_identifier}. Starting a stopped instance will resume billing charges and may incur costs. To confirm, please provide the confirmation parameter with the value \"{CONFIRM_START}\".",
            "impact": get_operation_impact('start_db_instance'),
        },
        "stop": {
            "required_confirmation": CONFIRM_STOP,
            "warning_message": f"WARNING: You are about to stop DB instance {db_instance_identifier}. This will make the database unavailable until it is started again. To confirm, please provide the confirmation parameter with the value \"{CONFIRM_STOP}\".",
            "impact": get_operation_impact('stop_db_instance'),
        },
        "reboot": {
            "required_confirmation": CONFIRM_REBOOT,
            "warning_message": f"WARNING: You are about to reboot DB instance {db_instance_identifier}. This will cause a brief interruption in database availability. To confirm, please provide the confirmation parameter with the value \"{CONFIRM_REBOOT}\".",
            "impact": get_operation_impact('reboot_db_instance'),
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
            logger.info(f"Starting DB instance {db_instance_identifier}")
            response = await asyncio.to_thread(
                rds_client.start_db_instance,
                DBInstanceIdentifier=db_instance_identifier
            )
            logger.success(f"Successfully started DB instance {db_instance_identifier}")
            
            result = format_aws_response(response)
            result['message'] = SUCCESS_STARTED.format(f'DB instance {db_instance_identifier}')
            
        elif action == "stop":
            logger.info(f"Stopping DB instance {db_instance_identifier}")
            response = await asyncio.to_thread(
                rds_client.stop_db_instance,
                DBInstanceIdentifier=db_instance_identifier
            )
            logger.success(f"Successfully stopped DB instance {db_instance_identifier}")
            
            result = format_aws_response(response)
            result['message'] = SUCCESS_STOPPED.format(f'DB instance {db_instance_identifier}')
            
        elif action == "reboot":
            logger.info(f"Rebooting DB instance {db_instance_identifier}")
            response = await asyncio.to_thread(
                rds_client.reboot_db_instance,
                DBInstanceIdentifier=db_instance_identifier
            )
            logger.success(f"Successfully initiated reboot of DB instance {db_instance_identifier}")
            
            result = format_aws_response(response)
            result['message'] = SUCCESS_REBOOTED.format(f'DB instance {db_instance_identifier}')
        
        # add formatted instance info to the result
        result['formatted_instance'] = format_instance_info(result.get('DBInstance', {}))
        
        return result
    except Exception as e:
        return await handle_aws_error(f'status_db_instance({db_instance_identifier}, {action})', e, ctx)


async def describe_db_instances(
    db_instance_identifier: Annotated[
        Optional[str], Field(description='The user-supplied DB instance identifier. If this parameter is specified, information from only the specific DB instance is returned')
    ] = None,
    filters: Annotated[
        Optional[List[Dict[str, Any]]], Field(description='A filter that specifies one or more DB instances to describe')
    ] = None,
    marker: Annotated[
        Optional[str], Field(description='An optional pagination token provided by a previous DescribeDBInstances request')
    ] = None,
    max_records: Annotated[
        Optional[int], Field(description='The maximum number of records to include in the response')
    ] = None,
    ctx: Context = None,
    rds_client: Any = None,
) -> Dict[str, Any]:
    """Retrieve information about one or multiple RDS instances.

    Args:
        db_instance_identifier: The user-supplied DB instance identifier
        filters: A filter that specifies one or more DB instances to describe
        marker: An optional pagination token
        max_records: The maximum number of records to include in the response
        ctx: MCP context for logging and state management
        rds_client: AWS RDS client

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    try:
        params = {}
        
        if db_instance_identifier:
            params['DBInstanceIdentifier'] = db_instance_identifier
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        if max_records:
            params['MaxRecords'] = max_records

        logger.info(f"Describing DB instances")
        response = await asyncio.to_thread(rds_client.describe_db_instances, **params)
        
        result = format_aws_response(response)
        
        # Format instance information for better readability
        if 'DBInstances' in result:
            result['formatted_instances'] = [
                format_instance_info(instance) for instance in result['DBInstances']
            ]
        
        return result
    except Exception as e:
        return await handle_aws_error('describe_db_instances', e, ctx)
