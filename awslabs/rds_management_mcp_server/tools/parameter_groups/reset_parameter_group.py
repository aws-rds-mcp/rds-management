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

"""Tool to reset parameters in Amazon RDS parameter groups."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.decorators.require_confirmation import require_confirmation
from ...common.server import mcp
from ...common.utils import (
    format_rds_api_response,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


RESET_CLUSTER_PARAMETER_GROUP_DESCRIPTION = """Reset parameters in an Amazon RDS DB cluster parameter group to their default values.

This tool allows you to reset one or more parameters in a DB cluster parameter group to their
default values, or to reset all parameters in the parameter group.

<warning>
Resetting parameters will revert them to their default values, which may impact database behavior.
Some changes may require a DB instance reboot to take effect.
</warning>
"""


@mcp.tool(
    name='ResetDBClusterParameterGroup',
    description=RESET_CLUSTER_PARAMETER_GROUP_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation
async def reset_db_cluster_parameter_group(
    db_cluster_parameter_group_name: Annotated[
        str, Field(description='The name of the DB cluster parameter group')
    ],
    reset_all_parameters: Annotated[
        bool,
        Field(description='Whether to reset all parameters in the DB cluster parameter group'),
    ] = False,
    parameters: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(
            description='List of parameters to reset. Each parameter should include name and optionally apply_method ("immediate" or "pending-reboot")'
        ),
    ] = None,
    confirmation_token: Annotated[
        Optional[str], Field(description='Token to confirm this potentially disruptive operation')
    ] = None,
) -> Dict[str, Any]:
    """Reset parameters in a DB cluster parameter group to their default values.

    Args:
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        reset_all_parameters: Whether to reset all parameters
        parameters: The parameters to reset (if not resetting all)
        confirmation_token: Token to confirm this operation

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        # Format parameters for AWS API
        formatted_parameters = []
        if not reset_all_parameters and parameters:
            for param in parameters:
                formatted_param = {
                    'ParameterName': param.get('name'),
                }
                if param.get('apply_method'):
                    formatted_param['ApplyMethod'] = param.get('apply_method')
                formatted_parameters.append(formatted_param)

        logger.info(
            f'Resetting {"all parameters" if reset_all_parameters else "specified parameters"} in DB cluster parameter group {db_cluster_parameter_group_name}'
        )
        response = await asyncio.to_thread(
            rds_client.reset_db_cluster_parameter_group,
            DBClusterParameterGroupName=db_cluster_parameter_group_name,
            ResetAllParameters=reset_all_parameters,
            Parameters=formatted_parameters if not reset_all_parameters else [],
        )
        logger.success(
            f'Successfully reset parameters in DB cluster parameter group {db_cluster_parameter_group_name}'
        )

        result = format_rds_api_response(response)
        result['message'] = (
            f'Successfully reset {"all parameters" if reset_all_parameters else "specified parameters"} in DB cluster parameter group {db_cluster_parameter_group_name}'
        )
        result['parameters_reset'] = len(response.get('Parameters', []))

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e


RESET_INSTANCE_PARAMETER_GROUP_DESCRIPTION = """Reset parameters in an Amazon RDS DB instance parameter group to their default values.

This tool allows you to reset one or more parameters in a DB instance parameter group to their
default values, or to reset all parameters in the parameter group.

<warning>
Resetting parameters will revert them to their default values, which may impact database behavior.
Some changes may require a DB instance reboot to take effect.
</warning>
"""


@mcp.tool(
    name='ResetDBInstanceParameterGroup',
    description=RESET_INSTANCE_PARAMETER_GROUP_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation
async def reset_db_instance_parameter_group(
    db_parameter_group_name: Annotated[
        str, Field(description='The name of the DB instance parameter group')
    ],
    reset_all_parameters: Annotated[
        bool,
        Field(description='Whether to reset all parameters in the DB instance parameter group'),
    ] = False,
    parameters: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(
            description='List of parameters to reset. Each parameter should include name and optionally apply_method ("immediate" or "pending-reboot")'
        ),
    ] = None,
    confirmation_token: Annotated[
        Optional[str], Field(description='Token to confirm this potentially disruptive operation')
    ] = None,
) -> Dict[str, Any]:
    """Reset parameters in a DB instance parameter group to their default values.

    Args:
        db_parameter_group_name: The name of the DB instance parameter group
        reset_all_parameters: Whether to reset all parameters
        parameters: The parameters to reset (if not resetting all)
        confirmation_token: Token to confirm this operation

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    # Format parameters for AWS API
    formatted_parameters = []
    if not reset_all_parameters and parameters:
        for param in parameters:
            formatted_param = {
                'ParameterName': param.get('name'),
            }
            if param.get('apply_method'):
                formatted_param['ApplyMethod'] = param.get('apply_method')
            formatted_parameters.append(formatted_param)

    logger.info(
        f'Resetting {"all parameters" if reset_all_parameters else "specified parameters"} in DB instance parameter group {db_parameter_group_name}'
    )
    response = await asyncio.to_thread(
        rds_client.reset_db_parameter_group,
        DBParameterGroupName=db_parameter_group_name,
        ResetAllParameters=reset_all_parameters,
        Parameters=formatted_parameters if not reset_all_parameters else [],
    )
    logger.success(
        f'Successfully reset parameters in DB instance parameter group {db_parameter_group_name}'
    )

    result = format_rds_api_response(response)
    result['message'] = (
        f'Successfully reset {"all parameters" if reset_all_parameters else "specified parameters"} in DB instance parameter group {db_parameter_group_name}'
    )
    result['parameters_reset'] = len(response.get('Parameters', []))

    return result
