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

"""General utility functions for the RDS Management MCP Server."""

import asyncio
from ..common.server import SERVER_VERSION
from ..constants import ERROR_READONLY_MODE
from botocore.client import BaseClient
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any, Callable, Dict, List, Optional, TypeVar


# Default port values
DEFAULT_PORT_MYSQL = 3306
DEFAULT_PORT_POSTGRESQL = 5432
DEFAULT_PORT_MARIADB = 3306
DEFAULT_PORT_ORACLE = 1521
DEFAULT_PORT_SQLSERVER = 1433
DEFAULT_PORT_AURORA = 3306  # compatible with MySQL
DEFAULT_PORT_AURORA_POSTGRESQL = 5432  # Aurora PostgreSQL


T = TypeVar('T', bound=object)


def handle_paginated_aws_api_call(
    client: BaseClient,
    paginator_name: str,
    operation_parameters: Dict[str, Any],
    format_function: Callable[[Any], T],
    result_key: str,
) -> List[T]:
    """Fetch all results using AWS API pagination.

    Args:
        client: Boto3 client to use for the API call
        paginator_name: Name of the paginator to use (e.g. 'describe_db_clusters')
        operation_parameters: Parameters to pass to the paginator
        format_function: Function to format each item in the result
        result_key: Key in the response that contains the list of items

    Returns:
        List of formatted results
    """
    results = []
    paginator = client.get_paginator(paginator_name)
    operation_parameters['PaginationConfig'] = {
        'MaxItems': int(operation_parameters.get('MaxItems', 100))
    }
    page_iterator = paginator.paginate(**operation_parameters)
    for page in page_iterator:
        for item in page.get(result_key, []):
            results.append(format_function(item))

    return results


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
    tags.append({'Key': 'mcp_server_version', 'Value': SERVER_VERSION})
    tags.append({'Key': 'created_by', 'Value': 'rds-management-mcp-server'})
    params['Tags'] = tags
    return params


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


def get_engine_port(engine: str) -> int:
    """Get the default port for a database engine.

    Args:
        engine: The database engine type

    Returns:
        Default port number
    """
    engine_lower = engine.lower()

    if 'aurora-postgresql' in engine_lower:
        return DEFAULT_PORT_AURORA_POSTGRESQL
    elif 'aurora' in engine_lower:
        return DEFAULT_PORT_AURORA
    elif 'postgres' in engine_lower:
        return DEFAULT_PORT_POSTGRESQL
    elif 'mysql' in engine_lower:
        return DEFAULT_PORT_MYSQL
    elif 'mariadb' in engine_lower:
        return DEFAULT_PORT_MARIADB
    elif 'oracle' in engine_lower:
        return DEFAULT_PORT_ORACLE
    elif 'sqlserver' in engine_lower:
        return DEFAULT_PORT_SQLSERVER
    else:
        # default to MySQL port if unknown engine
        logger.warning(f'Unknown engine type: {engine}. Using default MySQL port.')
        return DEFAULT_PORT_MYSQL


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
        'tags': {tag['Key']: tag['Value'] for tag in cluster.get('TagList', [])}
        if cluster.get('TagList')
        else {},
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
