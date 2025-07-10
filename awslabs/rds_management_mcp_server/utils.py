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

"""Utility functions for RDS Management MCP Server."""

import asyncio
import time
import uuid
from .constants import (
    ERROR_READONLY_MODE,
    MCP_SERVER_VERSION,
    OPERATION_IMPACTS,
)
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any, Dict, Optional


def check_readonly_mode(operation: str, readonly: bool, ctx: Optional[Context] = None) -> bool:
    """Check if operation is allowed in current mode.

    Args:
        operation: The operation being attempted
        readonly: Whether server is in readonly mode
        ctx: MCP context for error reporting

    Returns:
        True if operation is allowed, False otherwise
    """
    if readonly and operation not in ['describe', 'list', 'get']:
        logger.warning(f'Operation {operation} blocked in readonly mode')
        if ctx:
            asyncio.create_task(ctx.error(ERROR_READONLY_MODE))
        return False
    return True


def format_rds_api_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Format AWS API response for MCP.

    Args:
        response: Raw AWS API response

    Returns:
        Formatted response dictionary
    """
    # remove ResponseMetadata as it's not useful for LLMs
    if 'ResponseMetadata' in response:
        del response['ResponseMetadata']

    # convert datetime objects to strings
    return convert_datetime_to_string(response)


def convert_datetime_to_string(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings.

    Args:
        obj: Object to convert

    Returns:
        Object with datetime objects converted to strings
    """
    import datetime

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetime_to_string(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    return obj


def add_mcp_tags(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add MCP server version tag to resource creation parameters.

    Args:
        params: Parameters for resource creation

    Returns:
        Parameters with MCP tags added
    """
    tags = params.get('Tags', [])
    tags.append({'Key': 'mcp_server_version', 'Value': MCP_SERVER_VERSION})
    tags.append({'Key': 'created_by', 'Value': 'rds-management-mcp-server'})
    params['Tags'] = tags
    return params


def get_operation_impact(operation: str) -> Dict[str, Any]:
    """Get detailed impact information for an operation.

    Args:
        operation: The operation name

    Returns:
        Dictionary with impact details
    """
    if operation in OPERATION_IMPACTS:
        return OPERATION_IMPACTS[operation]

    # default impact for unknown operations
    return {
        'risk': get_operation_risk_level(operation),
        'downtime': 'Unknown',
        'data_loss': 'Unknown',
        'reversible': 'Unknown',
        'estimated_time': 'Unknown',
    }


def get_operation_risk_level(operation: str) -> str:
    """Get the risk level for an operation.

    Args:
        operation: The operation name

    Returns:
        Risk level (low, high, or critical)
    """
    if operation in OPERATION_IMPACTS:
        return OPERATION_IMPACTS[operation]['risk']

    # default risk levels based on operation type
    if operation.startswith('delete_'):
        return 'critical'
    elif operation.startswith(('modify_', 'stop_', 'reboot_', 'failover_')):
        return 'high'
    else:
        return 'low'


def validate_db_identifier(identifier: str) -> bool:
    """Validate a database identifier according to AWS rules.

    Args:
        identifier: The identifier to validate

    Returns:
        True if valid, False otherwise
    """
    import re

    # AWS RDS identifier rules:
    # - 1-63 characters
    # - Begin with a letter
    # - Contain only alphanumeric characters and hyphens
    # - No two consecutive hyphens
    # - Not end with a hyphen

    if not identifier or len(identifier) > 63:
        return False

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9-]*$', identifier):
        return False

    if '--' in identifier or identifier.endswith('-'):
        return False

    return True


def format_cluster_info(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Format cluster information for better readability.

    Args:
        cluster: Raw cluster data from AWS

    Returns:
        Formatted cluster information
    """
    return {
        'cluster_id': cluster.get('DBClusterIdentifier'),
        'status': cluster.get('Status'),
        'engine': cluster.get('Engine'),
        'engine_version': cluster.get('EngineVersion'),
        'endpoint': cluster.get('Endpoint'),
        'reader_endpoint': cluster.get('ReaderEndpoint'),
        'multi_az': cluster.get('MultiAZ'),
        'backup_retention': cluster.get('BackupRetentionPeriod'),
        'preferred_backup_window': cluster.get('PreferredBackupWindow'),
        'preferred_maintenance_window': cluster.get('PreferredMaintenanceWindow'),
        'created_time': convert_datetime_to_string(cluster.get('ClusterCreateTime')),
        'members': [
            {
                'instance_id': member.get('DBInstanceIdentifier'),
                'is_writer': member.get('IsClusterWriter'),
                'status': member.get('DBClusterParameterGroupStatus'),
            }
            for member in cluster.get('DBClusterMembers', [])
        ],
        'vpc_security_groups': [
            {'id': sg.get('VpcSecurityGroupId'), 'status': sg.get('Status')}
            for sg in cluster.get('VpcSecurityGroups', [])
        ],
        'tags': {tag['Key']: tag['Value'] for tag in cluster.get('TagList', [])},
    }


def format_instance_info(instance: Dict[str, Any]) -> Dict[str, Any]:
    """Format instance information for better readability.

    Args:
        instance: Raw instance data from AWS

    Returns:
        Formatted instance information
    """
    # Handle potentially nested endpoint structure
    endpoint = {}
    if instance.get('Endpoint'):
        if isinstance(instance['Endpoint'], dict):
            endpoint = {
                'address': instance['Endpoint'].get('Address'),
                'port': instance['Endpoint'].get('Port'),
                'hosted_zone_id': instance['Endpoint'].get('HostedZoneId'),
            }
        else:
            endpoint = {'address': instance.get('Endpoint')}

    return {
        'instance_id': instance.get('DBInstanceIdentifier'),
        'status': instance.get('DBInstanceStatus'),
        'engine': instance.get('Engine'),
        'engine_version': instance.get('EngineVersion'),
        'instance_class': instance.get('DBInstanceClass'),
        'endpoint': endpoint,
        'availability_zone': instance.get('AvailabilityZone'),
        'multi_az': instance.get('MultiAZ', False),
        'storage': {
            'type': instance.get('StorageType'),
            'allocated': instance.get('AllocatedStorage'),
            'encrypted': instance.get('StorageEncrypted'),
        },
        'publicly_accessible': instance.get('PubliclyAccessible', False),
        'vpc_security_groups': [
            {'id': sg.get('VpcSecurityGroupId'), 'status': sg.get('Status')}
            for sg in instance.get('VpcSecurityGroups', [])
        ],
        'db_cluster': instance.get('DBClusterIdentifier'),
        'preferred_backup_window': instance.get('PreferredBackupWindow'),
        'preferred_maintenance_window': instance.get('PreferredMaintenanceWindow'),
        'tags': {tag['Key']: tag['Value'] for tag in instance.get('TagList', [])}
        if instance.get('TagList')
        else {},
        'resource_id': instance.get('DbiResourceId'),
    }


# dictionary to store pending operations
# key: confirmation_token, value: (operation_type, params, expiration_time)
_pending_operations = {}


# expiration time for pending operations (in seconds)
EXPIRATION_TIME = 300  # 5 minutes


def generate_confirmation_token() -> str:
    """Generate a unique confirmation token.

    Returns:
        str: A unique confirmation token
    """
    return str(uuid.uuid4())


def add_pending_operation(operation_type: str, params: Dict[str, Any]) -> str:
    """Add a pending operation.

    Args:
        operation_type: The type of operation (e.g., 'delete_db_cluster')
        params: The parameters for the operation

    Returns:
        str: The confirmation token for the operation
    """
    token = generate_confirmation_token()
    expiration_time = time.time() + EXPIRATION_TIME
    _pending_operations[token] = (operation_type, params, expiration_time)
    return token


def get_pending_operation(token: str) -> Optional[tuple]:
    """Get a pending operation by its confirmation token.

    Args:
        token: The confirmation token

    Returns:
        Optional[tuple]: The operation type, parameters, and expiration time, or None if not found
    """
    # clean up expired operations
    cleanup_expired_operations()

    # return the operation if it exists
    return _pending_operations.get(token)


def remove_pending_operation(token: str) -> bool:
    """Remove a pending operation.

    Args:
        token: The confirmation token

    Returns:
        bool: True if the operation was removed, False otherwise
    """
    if token in _pending_operations:
        del _pending_operations[token]
        return True
    return False


def cleanup_expired_operations() -> None:
    """Clean up expired operations."""
    current_time = time.time()
    expired_tokens = [
        token
        for token, (_, _, expiration_time) in _pending_operations.items()
        if expiration_time < current_time
    ]
    for token in expired_tokens:
        del _pending_operations[token]
