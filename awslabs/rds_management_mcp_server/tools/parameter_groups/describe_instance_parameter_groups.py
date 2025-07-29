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

"""Tool to describe Amazon RDS DB instance parameter groups."""

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
    name='DescribeDBInstanceParamGroups',
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
) -> Dict[str, Any]:
    """List DB instance parameter groups.

    Args:
        db_parameter_group_name: The name of the DB parameter group
        marker: Pagination token
        max_records: Maximum number of records to return

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
