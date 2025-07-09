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

"""Tool to describe Amazon RDS parameter groups and parameters."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions
from ...common.server import mcp
from ...common.utils import (
    format_rds_api_response,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional
from typing_extensions import Annotated


DESCRIBE_DB_CLUSTER_PARAMETERS_TOOL_DESCRIPTION = """Returns a list of parameters for a DB cluster parameter group.

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


@mcp.tool(
    name='DescribeDBClusterParameters',
    description=DESCRIBE_DB_CLUSTER_PARAMETERS_TOOL_DESCRIPTION,
)
@handle_exceptions
async def describe_db_cluster_parameters(
    db_cluster_parameter_group_name: Annotated[
        str, Field(description='The name of the DB cluster parameter group')
    ],
    source: Annotated[
        Optional[str], Field(description='The parameter source (system, engine-default, or user)')
    ] = None,
    marker: Annotated[Optional[str], Field(description='Pagination token')] = None,
    max_records: Annotated[
        Optional[int], Field(description='Maximum number of records to return')
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """List all parameters for a DB cluster parameter group.

    Args:
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        source: The parameter source
        marker: Pagination token
        max_records: Maximum number of records to return
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        params = {'DBClusterParameterGroupName': db_cluster_parameter_group_name}

        if source:
            params['Source'] = source
        if marker:
            params['Marker'] = marker
        if max_records:
            params['MaxRecords'] = max_records

        logger.info(
            f'Describing parameters for DB cluster parameter group {db_cluster_parameter_group_name}'
        )
        response = await asyncio.to_thread(rds_client.describe_db_cluster_parameters, **params)

        result = format_rds_api_response(response)

        # Format parameters for better readability
        formatted_parameters = []
        for param in result.get('Parameters', []):
            formatted_param = {
                'name': param.get('ParameterName'),
                'value': param.get('ParameterValue'),
                'description': param.get('Description'),
                'source': param.get('Source'),
                'is_modifiable': param.get('IsModifiable', False),
                'data_type': param.get('DataType'),
                'allowed_values': param.get('AllowedValues'),
                'apply_type': param.get('ApplyType'),
                'apply_method': param.get('ApplyMethod'),
            }
            formatted_parameters.append(formatted_param)

        result['formatted_parameters'] = formatted_parameters

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e


DESCRIBE_DB_INSTANCE_PARAMETERS_TOOL_DESCRIPTION = """Returns a list of parameters for a DB instance parameter group.

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


@mcp.tool(
    name='DescribeDBInstanceParameters',
    description=DESCRIBE_DB_INSTANCE_PARAMETERS_TOOL_DESCRIPTION,
)
@handle_exceptions
async def describe_db_instance_parameters(
    db_parameter_group_name: Annotated[
        str, Field(description='The name of the DB parameter group')
    ],
    source: Annotated[
        Optional[str], Field(description='The parameter source (system, engine-default, or user)')
    ] = None,
    marker: Annotated[Optional[str], Field(description='Pagination token')] = None,
    max_records: Annotated[
        Optional[int], Field(description='Maximum number of records to return')
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """List all parameters for a DB instance parameter group.

    Args:
        db_parameter_group_name: The name of the DB parameter group
        source: The parameter source
        marker: Pagination token
        max_records: Maximum number of records to return
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        params = {'DBParameterGroupName': db_parameter_group_name}

        if source:
            params['Source'] = source
        if marker:
            params['Marker'] = marker
        if max_records:
            params['MaxRecords'] = max_records

        logger.info(
            f'Describing parameters for DB instance parameter group {db_parameter_group_name}'
        )
        response = await asyncio.to_thread(rds_client.describe_db_parameters, **params)

        result = format_rds_api_response(response)

        # Format parameters for better readability
        formatted_parameters = []
        for param in result.get('Parameters', []):
            formatted_param = {
                'name': param.get('ParameterName'),
                'value': param.get('ParameterValue'),
                'description': param.get('Description'),
                'source': param.get('Source'),
                'is_modifiable': param.get('IsModifiable', False),
                'data_type': param.get('DataType'),
                'allowed_values': param.get('AllowedValues'),
                'apply_type': param.get('ApplyType'),
                'apply_method': param.get('ApplyMethod'),
            }
            formatted_parameters.append(formatted_param)

        result['formatted_parameters'] = formatted_parameters

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e


DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS_TOOL_DESCRIPTION = """Returns a list of DB cluster parameter group descriptions.

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


@mcp.tool(
    name='DescribeDBClusterParameterGroups',
    description=DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS_TOOL_DESCRIPTION,
)
@handle_exceptions
async def describe_db_cluster_parameter_groups(
    db_cluster_parameter_group_name: Annotated[
        Optional[str], Field(description='The name of the DB cluster parameter group')
    ] = None,
    marker: Annotated[Optional[str], Field(description='Pagination token')] = None,
    max_records: Annotated[
        Optional[int], Field(description='Maximum number of records to return')
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """List DB cluster parameter groups.

    Args:
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        marker: Pagination token
        max_records: Maximum number of records to return
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        params = {}

        if db_cluster_parameter_group_name:
            params['DBClusterParameterGroupName'] = db_cluster_parameter_group_name
        if marker:
            params['Marker'] = marker
        if max_records:
            params['MaxRecords'] = max_records

        logger.info('Describing DB cluster parameter groups')
        response = await asyncio.to_thread(
            rds_client.describe_db_cluster_parameter_groups, **params
        )

        result = format_rds_api_response(response)

        # Format parameter groups for better readability
        formatted_parameter_groups = []
        for group in result.get('DBClusterParameterGroups', []):
            formatted_group = {
                'name': group.get('DBClusterParameterGroupName'),
                'description': group.get('Description'),
                'family': group.get('DBParameterGroupFamily'),
                'type': 'cluster',
                'arn': group.get('DBClusterParameterGroupArn'),
            }
            formatted_parameter_groups.append(formatted_group)

        result['formatted_parameter_groups'] = formatted_parameter_groups

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e


DESCRIBE_DB_INSTANCE_PARAMETER_GROUPS_TOOL_DESCRIPTION = """Returns a list of DB instance parameter group descriptions.

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


@mcp.tool(
    name='DescribeDBInstanceParameterGroups',
    description=DESCRIBE_DB_INSTANCE_PARAMETER_GROUPS_TOOL_DESCRIPTION,
)
@handle_exceptions
async def describe_db_instance_parameter_groups(
    db_parameter_group_name: Annotated[
        Optional[str], Field(description='The name of the DB parameter group')
    ] = None,
    marker: Annotated[Optional[str], Field(description='Pagination token')] = None,
    max_records: Annotated[
        Optional[int], Field(description='Maximum number of records to return')
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """List DB instance parameter groups.

    Args:
        db_parameter_group_name: The name of the DB parameter group
        marker: Pagination token
        max_records: Maximum number of records to return
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        params = {}

        if db_parameter_group_name:
            params['DBParameterGroupName'] = db_parameter_group_name
        if marker:
            params['Marker'] = marker
        if max_records:
            params['MaxRecords'] = max_records

        logger.info('Describing DB instance parameter groups')
        response = await asyncio.to_thread(rds_client.describe_db_parameter_groups, **params)

        result = format_rds_api_response(response)

        # Format parameter groups for better readability
        formatted_parameter_groups = []
        for group in result.get('DBParameterGroups', []):
            formatted_group = {
                'name': group.get('DBParameterGroupName'),
                'description': group.get('Description'),
                'family': group.get('DBParameterGroupFamily'),
                'type': 'instance',
                'arn': group.get('DBParameterGroupArn'),
            }
            formatted_parameter_groups.append(formatted_group)

        result['formatted_parameter_groups'] = formatted_parameter_groups

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e
