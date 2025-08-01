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

"""Tool to describe Amazon RDS DB cluster parameters."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...common.utils import (
    format_rds_api_response,
)
from loguru import logger
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
) -> Dict[str, Any]:
    """List all parameters for a DB cluster parameter group.

    Args:
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        source: The parameter source
        marker: Pagination token
        max_records: Maximum number of records to return

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
