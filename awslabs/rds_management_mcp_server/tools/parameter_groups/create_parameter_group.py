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

"""Tool to create Amazon RDS parameter groups."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.server import mcp
from ...common.utils import (
    add_mcp_tags,
    format_rds_api_response,
)
from ...constants import (
    SUCCESS_CREATED,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


CREATE_CLUSTER_PARAMETER_GROUP_TOOL_DESCRIPTION = """Create a new custom DB cluster parameter group.

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


@mcp.tool(
    name='CreateDBClusterParameterGroup',
    description=CREATE_CLUSTER_PARAMETER_GROUP_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def create_db_cluster_parameter_group(
    db_cluster_parameter_group_name: Annotated[
        str, Field(description='The name of the DB cluster parameter group')
    ],
    db_parameter_group_family: Annotated[
        str, Field(description='The DB parameter group family name (e.g., mysql8.0, postgres13)')
    ],
    description: Annotated[
        str, Field(description='The description for the DB cluster parameter group')
    ],
    tags: Annotated[
        Optional[List[Dict[str, str]]],
        Field(description='A list of tags to apply to the parameter group'),
    ] = None,
) -> Dict[str, Any]:
    """Create a new DB cluster parameter group.

    Args:
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        db_parameter_group_family: The DB parameter group family name
        description: The description for the DB cluster parameter group
        tags: A list of tags to apply to the parameter group

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        params = {
            'DBClusterParameterGroupName': db_cluster_parameter_group_name,
            'DBParameterGroupFamily': db_parameter_group_family,
            'Description': description,
        }

        # Format and add tags
        if tags:
            aws_tags = []
            for tag_item in tags:
                for key, value in tag_item.items():
                    aws_tags.append({'Key': key, 'Value': value})
            params['Tags'] = aws_tags

        # Add MCP tags
        params = add_mcp_tags(params)

        logger.info(f'Creating DB cluster parameter group {db_cluster_parameter_group_name}')
        response = await asyncio.to_thread(rds_client.create_db_cluster_parameter_group, **params)
        logger.success(
            f'Successfully created DB cluster parameter group {db_cluster_parameter_group_name}'
        )

        result = format_rds_api_response(response)

        # Format response for better readability
        formatted_parameter_group = {
            'name': response.get('DBClusterParameterGroup', {}).get('DBClusterParameterGroupName'),
            'description': response.get('DBClusterParameterGroup', {}).get('Description'),
            'family': response.get('DBClusterParameterGroup', {}).get('DBParameterGroupFamily'),
            'type': 'cluster',
            'arn': response.get('DBClusterParameterGroup', {}).get('DBClusterParameterGroupArn'),
        }

        result['message'] = SUCCESS_CREATED.format(
            f'DB cluster parameter group {db_cluster_parameter_group_name}'
        )
        result['formatted_parameter_group'] = formatted_parameter_group

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e


CREATE_INSTANCE_PARAMETER_GROUP_TOOL_DESCRIPTION = """Create a new custom DB instance parameter group.

<use_case>
Use this tool to create a custom parameter group for DB instances, allowing you to customize
database engine parameters according to your specific requirements. Custom parameter groups
let you optimize database performance, security, and behavior at the instance level.
</use_case>

<important_notes>
1. Parameter group names must be 1-255 letters, numbers, or hyphens
2. Parameter group names must start with a letter and cannot end with a hyphen
3. You must specify a valid DB parameter group family (e.g., 'mysql8.0', 'postgres13')
4. The parameter group family determines which parameters are available
5. When run with readonly=True (default), this operation will be simulated but not actually performed
</important_notes>

## Response structure
Returns a dictionary with the following keys:
- `message`: Success message confirming the creation
- `formatted_parameter_group`: A simplified representation of the parameter group
- `DBParameterGroup`: The full AWS API response

<examples>
Example usage scenarios:
1. Create a parameter group for MySQL instances:
   - db_parameter_group_name="prod-mysql-instance-params"
   - db_parameter_group_family="mysql8.0"
   - description="Production MySQL 8.0 instance parameters with optimized settings"

2. Create a parameter group for PostgreSQL instances:
   - db_parameter_group_name="reporting-postgres-params"
   - db_parameter_group_family="postgres13"
   - description="Reporting database optimized parameters"
   - tags=[{"Environment": "Production", "Purpose": "Reporting"}]
</examples>
"""


@mcp.tool(
    name='CreateDBInstanceParameterGroup',
    description=CREATE_INSTANCE_PARAMETER_GROUP_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def create_db_instance_parameter_group(
    db_parameter_group_name: Annotated[
        str, Field(description='The name of the DB instance parameter group')
    ],
    db_parameter_group_family: Annotated[
        str, Field(description='The DB parameter group family name (e.g., mysql8.0, postgres13)')
    ],
    description: Annotated[
        str, Field(description='The description for the DB instance parameter group')
    ],
    tags: Annotated[
        Optional[List[Dict[str, str]]],
        Field(description='A list of tags to apply to the parameter group'),
    ] = None,
) -> Dict[str, Any]:
    """Create a new DB instance parameter group.

    Args:
        db_parameter_group_name: The name of the DB instance parameter group
        db_parameter_group_family: The DB parameter group family name
        description: The description for the DB instance parameter group
        tags: A list of tags to apply to the parameter group

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        params = {
            'DBParameterGroupName': db_parameter_group_name,
            'DBParameterGroupFamily': db_parameter_group_family,
            'Description': description,
        }

        # Format and add tags
        if tags:
            aws_tags = []
            for tag_item in tags:
                for key, value in tag_item.items():
                    aws_tags.append({'Key': key, 'Value': value})
            params['Tags'] = aws_tags

        # Add MCP tags
        params = add_mcp_tags(params)

        logger.info(f'Creating DB instance parameter group {db_parameter_group_name}')
        response = await asyncio.to_thread(rds_client.create_db_parameter_group, **params)
        logger.success(
            f'Successfully created DB instance parameter group {db_parameter_group_name}'
        )

        result = format_rds_api_response(response)

        # Format response for better readability
        formatted_parameter_group = {
            'name': response.get('DBParameterGroup', {}).get('DBParameterGroupName'),
            'description': response.get('DBParameterGroup', {}).get('Description'),
            'family': response.get('DBParameterGroup', {}).get('DBParameterGroupFamily'),
            'type': 'instance',
            'arn': response.get('DBParameterGroup', {}).get('DBParameterGroupArn'),
        }

        result['message'] = SUCCESS_CREATED.format(
            f'DB instance parameter group {db_parameter_group_name}'
        )
        result['formatted_parameter_group'] = formatted_parameter_group

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e
