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

"""Tool to modify Amazon RDS parameter group parameters."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions
from ...common.server import mcp
from ...common.utils import (
    check_readonly_mode,
    format_rds_api_response,
)
from ...constants import (
    ERROR_READONLY_MODE,
    SUCCESS_MODIFIED,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List
from typing_extensions import Annotated


MODIFY_CLUSTER_PARAMETER_GROUP_DESCRIPTION = """Modify parameters in an Amazon RDS DB cluster parameter group.

This tool allows you to modify one or more parameters in a DB cluster parameter group.
Parameters define various configuration settings for the database engine used by
your DB clusters.

<warning>
Some parameter changes require a DB instance reboot to take effect. The apply_method
parameter can be set to 'pending-reboot' to apply the change during the next reboot,
or 'immediate' to apply it as soon as possible.
</warning>
"""


@mcp.tool(
    name='ModifyDBClusterParameterGroup',
    description=MODIFY_CLUSTER_PARAMETER_GROUP_DESCRIPTION,
)
@handle_exceptions
async def modify_db_cluster_parameter_group(
    db_cluster_parameter_group_name: Annotated[
        str, Field(description='The name of the DB cluster parameter group to modify')
    ],
    parameters: Annotated[
        List[Dict[str, Any]],
        Field(
            description='List of parameters to modify. Each parameter should include name, value, and optionally apply_method ("immediate" or "pending-reboot")'
        ),
    ],
    ctx: Context = None,
) -> Dict[str, Any]:
    """Modify parameters in a DB cluster parameter group.

    Args:
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        parameters: List of parameters to modify. Each parameter should include name, value,
                   and optionally apply_method ("immediate" or "pending-reboot")
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    # Check if server is in readonly mode
    if not check_readonly_mode('modify', Context.readonly_mode(), ctx):
        return {'error': ERROR_READONLY_MODE}

    try:
        # Format parameters for AWS API
        formatted_parameters = []
        for param in parameters:
            formatted_param = {
                'ParameterName': param.get('name'),
                'ParameterValue': param.get('value'),
            }
            if param.get('apply_method'):
                formatted_param['ApplyMethod'] = param.get('apply_method')
            formatted_parameters.append(formatted_param)

        logger.info(f'Modifying DB cluster parameter group {db_cluster_parameter_group_name}')
        response = await asyncio.to_thread(
            rds_client.modify_db_cluster_parameter_group,
            DBClusterParameterGroupName=db_cluster_parameter_group_name,
            Parameters=formatted_parameters,
        )
        logger.success(
            f'Successfully modified parameters in DB cluster parameter group {db_cluster_parameter_group_name}'
        )

        # Get updated parameters for reference
        params_response = await asyncio.to_thread(
            rds_client.describe_db_cluster_parameters,
            DBClusterParameterGroupName=db_cluster_parameter_group_name,
            MaxRecords=100,  # Limit the number of parameters returned
        )

        result = format_rds_api_response(response)

        # Format parameters for better readability
        formatted_parameters_list = []
        for param in params_response.get('Parameters', []):
            formatted_parameters_list.append(
                {
                    'name': param.get('ParameterName'),
                    'value': param.get('ParameterValue'),
                    'description': param.get('Description'),
                    'allowed_values': param.get('AllowedValues'),
                    'source': param.get('Source'),
                    'apply_type': param.get('ApplyType'),
                    'data_type': param.get('DataType'),
                    'is_modifiable': param.get('IsModifiable', False),
                }
            )

        result['message'] = SUCCESS_MODIFIED.format(
            f'parameters in DB cluster parameter group {db_cluster_parameter_group_name}'
        )
        result['parameters_modified'] = len(response.get('Parameters', []))
        result['formatted_parameters'] = formatted_parameters_list[
            :10
        ]  # Only show first 10 parameters
        result['total_parameters'] = len(formatted_parameters_list)

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e


MODIFY_INSTANCE_PARAMETER_GROUP_DESCRIPTION = """Modify parameters in an Amazon RDS DB instance parameter group.

This tool allows you to modify one or more parameters in a DB instance parameter group.
Parameters define various configuration settings for the database engine used by
your DB instances.

<warning>
Some parameter changes require a DB instance reboot to take effect. The apply_method
parameter can be set to 'pending-reboot' to apply the change during the next reboot,
or 'immediate' to apply it as soon as possible.
</warning>
"""


@mcp.tool(
    name='ModifyDBInstanceParameterGroup',
    description=MODIFY_INSTANCE_PARAMETER_GROUP_DESCRIPTION,
)
@handle_exceptions
async def modify_db_instance_parameter_group(
    db_parameter_group_name: Annotated[
        str, Field(description='The name of the DB instance parameter group to modify')
    ],
    parameters: Annotated[
        List[Dict[str, Any]],
        Field(
            description='List of parameters to modify. Each parameter should include name, value, and optionally apply_method ("immediate" or "pending-reboot")'
        ),
    ],
    ctx: Context = None,
) -> Dict[str, Any]:
    """Modify parameters in a DB instance parameter group.

    Args:
        db_parameter_group_name: The name of the DB instance parameter group
        parameters: List of parameters to modify. Each parameter should include name, value,
                   and optionally apply_method ("immediate" or "pending-reboot")
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    # Check if server is in readonly mode
    if not check_readonly_mode('modify', Context.readonly_mode(), ctx):
        return {'error': ERROR_READONLY_MODE}

    try:
        # Format parameters for AWS API
        formatted_parameters = []
        for param in parameters:
            formatted_param = {
                'ParameterName': param.get('name'),
                'ParameterValue': param.get('value'),
            }
            if param.get('apply_method'):
                formatted_param['ApplyMethod'] = param.get('apply_method')
            formatted_parameters.append(formatted_param)

        logger.info(f'Modifying DB instance parameter group {db_parameter_group_name}')
        response = await asyncio.to_thread(
            rds_client.modify_db_parameter_group,
            DBParameterGroupName=db_parameter_group_name,
            Parameters=formatted_parameters,
        )
        logger.success(
            f'Successfully modified parameters in DB instance parameter group {db_parameter_group_name}'
        )

        # Get updated parameters for reference
        params_response = await asyncio.to_thread(
            rds_client.describe_db_parameters,
            DBParameterGroupName=db_parameter_group_name,
            MaxRecords=100,  # Limit the number of parameters returned
        )

        result = format_rds_api_response(response)

        # Format parameters for better readability
        formatted_parameters_list = []
        for param in params_response.get('Parameters', []):
            formatted_parameters_list.append(
                {
                    'name': param.get('ParameterName'),
                    'value': param.get('ParameterValue'),
                    'description': param.get('Description'),
                    'allowed_values': param.get('AllowedValues'),
                    'source': param.get('Source'),
                    'apply_type': param.get('ApplyType'),
                    'data_type': param.get('DataType'),
                    'is_modifiable': param.get('IsModifiable', False),
                }
            )

        result['message'] = SUCCESS_MODIFIED.format(
            f'parameters in DB instance parameter group {db_parameter_group_name}'
        )
        result['parameters_modified'] = len(response.get('Parameters', []))
        result['formatted_parameters'] = formatted_parameters_list[
            :10
        ]  # Only show first 10 parameters
        result['total_parameters'] = len(formatted_parameters_list)

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e
