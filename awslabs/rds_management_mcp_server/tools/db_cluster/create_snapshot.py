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

"""Tool to create a snapshot of an Amazon RDS DB cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.constants import (
    SUCCESS_CREATED,
)
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.server import mcp
from ...common.utils import (
    add_mcp_tags,
    format_rds_api_response,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


CREATE_SNAPSHOT_TOOL_DESCRIPTION = """Create a snapshot of an Amazon RDS database cluster.

This tool creates a manual snapshot of an RDS database cluster. You can use this snapshot
to restore the database cluster to a specific point in time.

<warning>
Creating snapshots may temporarily affect database performance.
</warning>
"""


@mcp.tool(
    name='CreateDBClusterSnapshot',
    description=CREATE_SNAPSHOT_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def create_db_cluster_snapshot(
    db_cluster_snapshot_identifier: Annotated[
        str, Field(description='The identifier for the DB cluster snapshot')
    ],
    db_cluster_identifier: Annotated[
        str, Field(description='The identifier of the DB cluster to create a snapshot for')
    ],
    tags: Annotated[
        Optional[List[Dict[str, str]]],
        Field(description='Optional list of tags to apply to the snapshot'),
    ] = None,
) -> Dict[str, Any]:
    """Create a snapshot of an RDS database cluster.

    Args:
        db_cluster_snapshot_identifier: The identifier for the DB cluster snapshot
        db_cluster_identifier: The identifier of the DB cluster to create a snapshot for
        tags: Optional list of tags to apply to the snapshot

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    kwargs = {
        'DBClusterSnapshotIdentifier': db_cluster_snapshot_identifier,
        'DBClusterIdentifier': db_cluster_identifier,
    }

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
        f'Creating DB cluster snapshot {db_cluster_snapshot_identifier} for cluster {db_cluster_identifier}'
    )
    response = await asyncio.to_thread(rds_client.create_db_cluster_snapshot, **kwargs)
    logger.success(f'Successfully created DB cluster snapshot {db_cluster_snapshot_identifier}')

    # Format the response
    result = format_rds_api_response(response)
    formatted_snapshot = {
        'snapshot_id': response.get('DBClusterSnapshot', {}).get('DBClusterSnapshotIdentifier'),
        'cluster_id': response.get('DBClusterSnapshot', {}).get('DBClusterIdentifier'),
        'status': response.get('DBClusterSnapshot', {}).get('Status'),
        'creation_time': response.get('DBClusterSnapshot', {}).get('SnapshotCreateTime'),
        'engine': response.get('DBClusterSnapshot', {}).get('Engine'),
        'engine_version': response.get('DBClusterSnapshot', {}).get('EngineVersion'),
    }

    result['message'] = SUCCESS_CREATED.format(
        f'DB cluster snapshot {db_cluster_snapshot_identifier}'
    )
    result['formatted_snapshot'] = formatted_snapshot

    return result
