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

"""Tool to restore an Amazon RDS DB cluster from a snapshot."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions, readonly_check
from ...common.server import mcp
from ...common.utils import (
    add_mcp_tags,
    format_cluster_info,
    format_rds_api_response,
)
from ...constants import (
    SUCCESS_RESTORED,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


RESTORE_SNAPSHOT_TOOL_DESCRIPTION = """Restore an Amazon RDS database cluster from a snapshot.

This tool creates a new RDS DB cluster from a DB cluster snapshot. The new DB cluster is
created with the same configuration as the original DB cluster, except as specified by the
parameters in this request.

<warning>
This operation creates AWS resources that will incur costs on your AWS account.
</warning>
"""


@mcp.tool(
    name='RestoreDBClusterFromSnapshot',
    description=RESTORE_SNAPSHOT_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def restore_db_cluster_from_snapshot(
    db_cluster_identifier: Annotated[
        str, Field(description='The name of the DB cluster to create from the snapshot')
    ],
    snapshot_identifier: Annotated[
        str, Field(description='The identifier for the snapshot to restore from')
    ],
    engine: Annotated[str, Field(description='The database engine to use for the new cluster')],
    vpc_security_group_ids: Annotated[
        Optional[List[str]], Field(description='A list of VPC security groups for the DB cluster')
    ] = None,
    db_subnet_group_name: Annotated[
        Optional[str], Field(description='The DB subnet group name to use for the new DB cluster')
    ] = None,
    engine_version: Annotated[
        Optional[str], Field(description='The version of the database engine to use')
    ] = None,
    port: Annotated[
        Optional[int],
        Field(description='The port number on which the DB cluster accepts connections'),
    ] = None,
    availability_zones: Annotated[
        Optional[List[str]],
        Field(description='A list of Availability Zones for instances in the DB cluster'),
    ] = None,
    tags: Annotated[
        Optional[List[Dict[str, str]]],
        Field(description='Optional list of tags to apply to the new DB cluster'),
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Restore a DB cluster from a snapshot.

    Args:
        db_cluster_identifier: The name of the DB cluster to create from the snapshot
        snapshot_identifier: The identifier for the snapshot to restore from
        engine: The database engine to use for the new cluster
        vpc_security_group_ids: A list of VPC security groups for the DB cluster
        db_subnet_group_name: The DB subnet group name to use for the new DB cluster
        engine_version: The version of the database engine to use
        port: The port number on which the DB cluster accepts connections
        availability_zones: A list of Availability Zones for instances in the DB cluster
        tags: Optional list of tags to apply to the new DB cluster
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        kwargs = {
            'DBClusterIdentifier': db_cluster_identifier,
            'SnapshotIdentifier': snapshot_identifier,
            'Engine': engine,
        }

        # Add optional parameters if provided
        if vpc_security_group_ids:
            kwargs['VpcSecurityGroupIds'] = vpc_security_group_ids
        if db_subnet_group_name:
            kwargs['DBSubnetGroupName'] = db_subnet_group_name
        if engine_version:
            kwargs['EngineVersion'] = engine_version
        if port:
            kwargs['Port'] = port
        if availability_zones:
            kwargs['AvailabilityZones'] = availability_zones

        # Add MCP tags and any user-provided tags
        if tags:
            # Format tags for AWS API
            aws_tags = []
            for tag_item in tags:
                for key, value in tag_item.items():
                    aws_tags.append({'Key': key, 'Value': value})
            kwargs['Tags'] = aws_tags

        # Add MCP tags
        kwargs = add_mcp_tags(kwargs)

        logger.info(
            f'Restoring DB cluster {db_cluster_identifier} from snapshot {snapshot_identifier}'
        )
        response = await asyncio.to_thread(rds_client.restore_db_cluster_from_snapshot, **kwargs)
        logger.success(f'Successfully initiated restore of DB cluster {db_cluster_identifier}')

        # Format the response
        result = format_rds_api_response(response)
        result['message'] = SUCCESS_RESTORED.format(f'DB cluster {db_cluster_identifier}')
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e


RESTORE_POINT_IN_TIME_TOOL_DESCRIPTION = """Restore an Amazon RDS database cluster to a point in time.

This tool creates a new DB cluster from an existing DB cluster at a specific point in time.
You can restore to any point in time during the backup retention period.

<warning>
This operation creates AWS resources that will incur costs on your AWS account.
</warning>
"""


@mcp.tool(
    name='RestoreDBClusterToPointInTime',
    description=RESTORE_POINT_IN_TIME_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def restore_db_cluster_to_point_in_time(
    db_cluster_identifier: Annotated[
        str, Field(description='The name of the new DB cluster to be created')
    ],
    source_db_cluster_identifier: Annotated[
        str, Field(description='The identifier of the source DB cluster')
    ],
    restore_to_time: Annotated[
        Optional[str],
        Field(
            description='The date and time to restore the DB cluster to (format: YYYY-MM-DDTHH:MM:SSZ)'
        ),
    ] = None,
    use_latest_restorable_time: Annotated[
        Optional[bool],
        Field(
            description='Specifies whether to restore the DB cluster to the latest restorable backup time'
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        Field(description='The port number on which the DB cluster accepts connections'),
    ] = None,
    db_subnet_group_name: Annotated[
        Optional[str], Field(description='The DB subnet group name to use for the new DB cluster')
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]], Field(description='A list of VPC security groups for the DB cluster')
    ] = None,
    tags: Annotated[
        Optional[List[Dict[str, str]]],
        Field(description='Optional list of tags to apply to the new DB cluster'),
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Restore a DB cluster to a point in time.

    Args:
        db_cluster_identifier: The name of the new DB cluster to be created
        source_db_cluster_identifier: The identifier of the source DB cluster
        restore_to_time: The date and time to restore the DB cluster to
        use_latest_restorable_time: Whether to restore to the latest restorable time
        port: The port number on which the DB cluster accepts connections
        db_subnet_group_name: The DB subnet group name to use for the new DB cluster
        vpc_security_group_ids: A list of VPC security groups for the DB cluster
        tags: Optional list of tags to apply to the new DB cluster
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    # Validate that either restore_to_time or use_latest_restorable_time is provided
    if not restore_to_time and not use_latest_restorable_time:
        return {'error': 'Either restore_to_time or use_latest_restorable_time must be provided'}

    try:
        kwargs = {
            'DBClusterIdentifier': db_cluster_identifier,
            'SourceDBClusterIdentifier': source_db_cluster_identifier,
        }

        # Add optional parameters if provided
        if restore_to_time:
            kwargs['RestoreToTime'] = restore_to_time
        if use_latest_restorable_time is not None:
            kwargs['UseLatestRestorableTime'] = use_latest_restorable_time
        if port:
            kwargs['Port'] = port
        if db_subnet_group_name:
            kwargs['DBSubnetGroupName'] = db_subnet_group_name
        if vpc_security_group_ids:
            kwargs['VpcSecurityGroupIds'] = vpc_security_group_ids

        # Add MCP tags and any user-provided tags
        if tags:
            # Format tags for AWS API
            aws_tags = []
            for tag_item in tags:
                for key, value in tag_item.items():
                    aws_tags.append({'Key': key, 'Value': value})
            kwargs['Tags'] = aws_tags

        # Add MCP tags
        kwargs = add_mcp_tags(kwargs)

        logger.info(f'Restoring DB cluster {db_cluster_identifier} to point in time')
        response = await asyncio.to_thread(
            rds_client.restore_db_cluster_to_point_in_time, **kwargs
        )
        logger.success(
            f'Successfully initiated point-in-time restore of DB cluster {db_cluster_identifier}'
        )

        # Format the response
        result = format_rds_api_response(response)
        result['message'] = SUCCESS_RESTORED.format(
            f'DB cluster {db_cluster_identifier} to point in time'
        )
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e
