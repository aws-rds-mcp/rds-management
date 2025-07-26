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

"""Resources for listing Amazon RDS parameter groups."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from .describe_parameters import ParameterGroupListModel, ParameterGroupModel, ParameterModel
from loguru import logger


LIST_CLUSTER_PARAMETER_GROUPS_DESCRIPTION = """List all DB cluster parameter groups in your AWS account.

<use_case>
Use this resource to discover all available DB cluster parameter groups.
Parameter groups are used to apply specific configuration settings to your RDS clusters.
</use_case>

<important_notes>
1. This resource lists all cluster parameter groups in the current AWS region
2. Each parameter group contains metadata including family, description, and tags
3. A sample of parameters from each group is included (limited to improve performance)
</important_notes>
"""


@mcp.resource(
    uri='aws-rds://db-cluster/parameter-groups',
    name='GetDBClusterParameterGroups',
    description=LIST_CLUSTER_PARAMETER_GROUPS_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def list_cluster_parameter_groups() -> ParameterGroupListModel:
    """List all DB cluster parameter groups.

    Returns:
        ParameterGroupListModel: A model containing the list of parameter groups
    """
    logger.info('Listing DB cluster parameter groups')
    rds_client = RDSConnectionManager.get_connection()

    # Get parameter groups
    response = await asyncio.to_thread(rds_client.describe_db_cluster_parameter_groups)

    parameter_groups = []
    for pg in response.get('DBClusterParameterGroups', []):
        # Get a sample of parameters for each group
        try:
            params_response = await asyncio.to_thread(
                rds_client.describe_db_cluster_parameters,
                DBClusterParameterGroupName=pg.get('DBClusterParameterGroupName'),
                MaxRecords=20,  # Limit to 20 parameters for performance
            )

            parameters = []
            for param in params_response.get('Parameters', []):
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
        except Exception as e:
            logger.error(
                f'Error getting parameters for group {pg.get("DBClusterParameterGroupName")}: {str(e)}'
            )
            parameters = []

        # Extract tags
        tags = {}
        if 'Tags' in pg:
            tags = {tag.get('Key'): tag.get('Value') for tag in pg.get('Tags', [])}

        # Create parameter group model
        parameter_groups.append(
            ParameterGroupModel(
                name=pg.get('DBClusterParameterGroupName'),
                description=pg.get('Description'),
                family=pg.get('DBParameterGroupFamily'),
                type='cluster',
                parameters=parameters,
                arn=pg.get('DBClusterParameterGroupArn'),
                tags=tags,
                resource_uri=f'aws-rds://db-cluster/parameter-groups/{pg.get("DBClusterParameterGroupName")}',
            )
        )

    # Pagination handling
    marker = response.get('Marker')
    while marker:
        response = await asyncio.to_thread(
            rds_client.describe_db_cluster_parameter_groups, Marker=marker
        )

        for pg in response.get('DBClusterParameterGroups', []):
            # Get a sample of parameters for each group
            try:
                params_response = await asyncio.to_thread(
                    rds_client.describe_db_cluster_parameters,
                    DBClusterParameterGroupName=pg.get('DBClusterParameterGroupName'),
                    MaxRecords=20,  # Limit to 20 parameters for performance
                )

                parameters = []
                for param in params_response.get('Parameters', []):
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
            except Exception as e:
                logger.error(
                    f'Error getting parameters for group {pg.get("DBClusterParameterGroupName")}: {str(e)}'
                )
                parameters = []

            # Extract tags
            tags = {}
            if 'Tags' in pg:
                tags = {tag.get('Key'): tag.get('Value') for tag in pg.get('Tags', [])}

            # Create parameter group model
            parameter_groups.append(
                ParameterGroupModel(
                    name=pg.get('DBClusterParameterGroupName'),
                    description=pg.get('Description'),
                    family=pg.get('DBParameterGroupFamily'),
                    type='cluster',
                    parameters=parameters,
                    arn=pg.get('DBClusterParameterGroupArn'),
                    tags=tags,
                    resource_uri=f'aws-rds://db-cluster/parameter-groups/{pg.get("DBClusterParameterGroupName")}',
                )
            )

        marker = response.get('Marker')

    return ParameterGroupListModel(
        parameter_groups=parameter_groups,
        count=len(parameter_groups),
        resource_uri='aws-rds://db-cluster/parameter-groups',
    )


LIST_INSTANCE_PARAMETER_GROUPS_DESCRIPTION = """List all DB instance parameter groups in your AWS account.

<use_case>
Use this resource to discover all available DB instance parameter groups.
Parameter groups are used to apply specific configuration settings to your RDS instances.
</use_case>

<important_notes>
1. This resource lists all instance parameter groups in the current AWS region
2. Each parameter group contains metadata including family, description, and tags
3. A sample of parameters from each group is included (limited to improve performance)
</important_notes>
"""


@mcp.resource(
    uri='aws-rds://db-instance/parameter-groups',
    name='GetDBInstanceParameterGroups',
    description=LIST_INSTANCE_PARAMETER_GROUPS_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def list_instance_parameter_groups() -> ParameterGroupListModel:
    """List all DB instance parameter groups.

    Returns:
        ParameterGroupListModel: A model containing the list of parameter groups
    """
    logger.info('Listing DB instance parameter groups')
    rds_client = RDSConnectionManager.get_connection()

    # Get parameter groups
    response = await asyncio.to_thread(rds_client.describe_db_parameter_groups)

    parameter_groups = []
    for pg in response.get('DBParameterGroups', []):
        # Get a sample of parameters for each group
        try:
            params_response = await asyncio.to_thread(
                rds_client.describe_db_parameters,
                DBParameterGroupName=pg.get('DBParameterGroupName'),
                MaxRecords=20,  # Limit to 20 parameters for performance
            )

            parameters = []
            for param in params_response.get('Parameters', []):
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
        except Exception as e:
            logger.error(
                f'Error getting parameters for group {pg.get("DBParameterGroupName")}: {str(e)}'
            )
            parameters = []

        # Extract tags
        tags = {}
        if 'Tags' in pg:
            tags = {tag.get('Key'): tag.get('Value') for tag in pg.get('Tags', [])}

        # Create parameter group model
        parameter_groups.append(
            ParameterGroupModel(
                name=pg.get('DBParameterGroupName'),
                description=pg.get('Description'),
                family=pg.get('DBParameterGroupFamily'),
                type='instance',
                parameters=parameters,
                arn=pg.get('DBParameterGroupArn'),
                tags=tags,
                resource_uri=f'aws-rds://db-instance/parameter-groups/{pg.get("DBParameterGroupName")}',
            )
        )

    # Pagination handling
    marker = response.get('Marker')
    while marker:
        response = await asyncio.to_thread(rds_client.describe_db_parameter_groups, Marker=marker)

        for pg in response.get('DBParameterGroups', []):
            # Get a sample of parameters for each group
            try:
                params_response = await asyncio.to_thread(
                    rds_client.describe_db_parameters,
                    DBParameterGroupName=pg.get('DBParameterGroupName'),
                    MaxRecords=20,  # Limit to 20 parameters for performance
                )

                parameters = []
                for param in params_response.get('Parameters', []):
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
            except Exception as e:
                logger.error(
                    f'Error getting parameters for group {pg.get("DBParameterGroupName")}: {str(e)}'
                )
                parameters = []

            # Extract tags
            tags = {}
            if 'Tags' in pg:
                tags = {tag.get('Key'): tag.get('Value') for tag in pg.get('Tags', [])}

            # Create parameter group model
            parameter_groups.append(
                ParameterGroupModel(
                    name=pg.get('DBParameterGroupName'),
                    description=pg.get('Description'),
                    family=pg.get('DBParameterGroupFamily'),
                    type='instance',
                    parameters=parameters,
                    arn=pg.get('DBParameterGroupArn'),
                    tags=tags,
                    resource_uri=f'aws-rds://db-instance/parameter-groups/{pg.get("DBParameterGroupName")}',
                )
            )

        marker = response.get('Marker')

    return ParameterGroupListModel(
        parameter_groups=parameter_groups,
        count=len(parameter_groups),
        resource_uri='aws-rds://db-instance/parameter-groups',
    )
