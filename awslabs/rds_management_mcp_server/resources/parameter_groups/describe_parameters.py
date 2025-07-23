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

"""Resources for getting parameters from Amazon RDS parameter groups."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from loguru import logger
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from typing_extensions import Annotated


GET_CLUSTER_PARAMETERS_DESCRIPTION = """Get parameters for a specific DB cluster parameter group.

<use_case>
Use this resource to retrieve all parameters and their values from a specific DB cluster
parameter group. This information is useful for understanding the current configuration
of your RDS clusters.
</use_case>

<important_notes>
1. Parameters are divided into engine-default values and customized values
2. The source field indicates whether a parameter value is from the engine default or a custom setting
3. Some parameters may only be applied during specific events (e.g. database restart)
</important_notes>
"""


class ParameterModel(BaseModel):
    """DB Parameter model."""

    name: str = Field(description='The name of the parameter')
    value: Optional[str] = Field(None, description='The value of the parameter')
    description: Optional[str] = Field(None, description='Description of the parameter')
    allowed_values: Optional[str] = Field(
        None, description='The valid range of values for the parameter'
    )
    source: Optional[str] = Field(None, description='The source of the parameter value')
    apply_type: Optional[str] = Field(None, description='The apply type of the parameter')
    data_type: Optional[str] = Field(None, description='The data type of the parameter')
    is_modifiable: bool = Field(description='Whether the parameter can be modified')


class ParameterGroupModel(BaseModel):
    """DB Parameter group model."""

    name: str = Field(description='The name of the DB parameter group')
    description: str = Field(description='The description of the parameter group')
    family: str = Field(description='The DB parameter group family name')
    type: str = Field(description='The type of the parameter group (cluster or instance)')
    parameters: List[ParameterModel] = Field(
        default_factory=list, description='List of parameters'
    )
    arn: Optional[str] = Field(
        None, description='The Amazon Resource Name (ARN) for the parameter group'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    resource_uri: Optional[str] = Field(
        None, description='The resource URI for this parameter group'
    )


class ParameterGroupListModel(BaseModel):
    """DB Parameter group list model."""

    parameter_groups: List[ParameterGroupModel] = Field(
        default_factory=list, description='List of DB parameter groups'
    )
    count: int = Field(description='Total number of DB parameter groups')
    resource_uri: str = Field(description='The resource URI for the DB parameter groups')


class ParameterListModel(BaseModel):
    """DB Parameter list model."""

    parameters: List[ParameterModel] = Field(
        default_factory=list, description='List of DB parameters'
    )
    count: int = Field(description='Total number of DB parameters')
    parameter_group_name: str = Field(description='The name of the DB parameter group')
    resource_uri: str = Field(description='The resource URI for the DB parameters')


@mcp.resource(
    uri='aws-rds://db-cluster/parameter-groups/{parameter_group_name}/parameters',
    name='DescribeDBClusterParameters',
    description=GET_CLUSTER_PARAMETERS_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def describe_cluster_parameters(
    parameter_group_name: Annotated[
        str, Field(description='The name of the DB cluster parameter group')
    ],
) -> ParameterListModel:
    """Get parameters for a specific DB cluster parameter group.

    Args:
        parameter_group_name: Name of the DB cluster parameter group
        source: Parameter source filter

    Returns:
        ParameterListModel: A model containing the list of parameters
    """
    logger.info(f'Getting parameters for DB cluster parameter group: {parameter_group_name}')
    rds_client = RDSConnectionManager.get_connection()

    # Prepare parameters for API call
    params = {'DBClusterParameterGroupName': parameter_group_name}

    # Get parameters
    response = await asyncio.to_thread(rds_client.describe_db_cluster_parameters, **params)

    parameters = []
    for param in response.get('Parameters', []):
        parameters.append(
            ParameterModel(
                name=param.get('ParameterName'),
                value=param.get('ParameterValue'),
                description=param.get('Description'),
                allowed_values=param.get('AllowedValues'),
                source=param.get('Source'),
                apply_type=param.get('ApplyType'),
                data_type=param.get('DataType'),
                is_modifiable=param.get('IsModifiable', False),
            )
        )

    # Pagination handling
    marker = response.get('Marker')
    while marker:
        params['Marker'] = marker
        response = await asyncio.to_thread(rds_client.describe_db_cluster_parameters, **params)

        for param in response.get('Parameters', []):
            parameters.append(
                ParameterModel(
                    name=param.get('ParameterName'),
                    value=param.get('ParameterValue'),
                    description=param.get('Description'),
                    allowed_values=param.get('AllowedValues'),
                    source=param.get('Source'),
                    apply_type=param.get('ApplyType'),
                    data_type=param.get('DataType'),
                    is_modifiable=param.get('IsModifiable', False),
                )
            )

        marker = response.get('Marker')

    return ParameterListModel(
        parameters=parameters,
        count=len(parameters),
        parameter_group_name=parameter_group_name,
        resource_uri=f'aws-rds://db-cluster/parameter-groups/{parameter_group_name}/parameters',
    )


GET_INSTANCE_PARAMETERS_DESCRIPTION = """Get parameters for a specific DB instance parameter group.

<use_case>
Use this resource to retrieve all parameters and their values from a specific DB instance
parameter group. This information is useful for understanding the current configuration
of your RDS instances.
</use_case>

<important_notes>
1. Parameters are divided into engine-default values and customized values
2. The source field indicates whether a parameter value is from the engine default or a custom setting
3. Some parameters may only be applied during specific events (e.g. database restart)
</important_notes>
"""


@mcp.resource(
    uri='aws-rds://db-instance/parameter-groups/{parameter_group_name}/parameters',
    name='DescribeDBInstanceParameters',
    description=GET_INSTANCE_PARAMETERS_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def describe_instance_parameters(
    parameter_group_name: Annotated[
        str, Field(description='The name of the DB instance parameter group')
    ],
) -> ParameterListModel:
    """Get parameters for a specific DB instance parameter group.

    Args:
        parameter_group_name: Name of the DB instance parameter group
        source: Parameter source filter

    Returns:
        ParameterListModel: A model containing the list of parameters
    """
    logger.info(f'Getting parameters for DB instance parameter group: {parameter_group_name}')
    rds_client = RDSConnectionManager.get_connection()

    # Prepare parameters for API call
    params = {'DBParameterGroupName': parameter_group_name}

    # Get parameters
    response = await asyncio.to_thread(rds_client.describe_db_parameters, **params)

    parameters = []
    for param in response.get('Parameters', []):
        parameters.append(
            ParameterModel(
                name=param.get('ParameterName'),
                value=param.get('ParameterValue'),
                description=param.get('Description'),
                allowed_values=param.get('AllowedValues'),
                source=param.get('Source'),
                apply_type=param.get('ApplyType'),
                data_type=param.get('DataType'),
                is_modifiable=param.get('IsModifiable', False),
            )
        )

    # Pagination handling
    marker = response.get('Marker')
    while marker:
        params['Marker'] = marker
        response = await asyncio.to_thread(rds_client.describe_db_parameters, **params)

        for param in response.get('Parameters', []):
            parameters.append(
                ParameterModel(
                    name=param.get('ParameterName'),
                    value=param.get('ParameterValue'),
                    description=param.get('Description'),
                    allowed_values=param.get('AllowedValues'),
                    source=param.get('Source'),
                    apply_type=param.get('ApplyType'),
                    data_type=param.get('DataType'),
                    is_modifiable=param.get('IsModifiable', False),
                )
            )

        marker = response.get('Marker')

    return ParameterListModel(
        parameters=parameters,
        count=len(parameters),
        parameter_group_name=parameter_group_name,
        resource_uri=f'aws-rds://db-instance/parameter-groups/{parameter_group_name}/parameters',
    )
