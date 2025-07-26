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

"""Tool to delete a snapshot of an Amazon RDS DB cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.constants import (
    SUCCESS_DELETED,
)
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.decorators.require_confirmation import require_confirmation
from ...common.server import mcp
from ...common.utils import (
    format_rds_api_response,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict, Optional
from typing_extensions import Annotated


DELETE_SNAPSHOT_TOOL_DESCRIPTION = """Delete a snapshot of an Amazon RDS database cluster.

This tool deletes a manual snapshot of an RDS database cluster. This operation cannot be undone.

<warning>
This is a destructive operation that permanently deletes the snapshot.
Once a snapshot is deleted, it cannot be recovered.
</warning>
"""


@mcp.tool(
    name='DeleteDBClusterSnapshot',
    description=DELETE_SNAPSHOT_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('DeleteDBClusterSnapshot')
async def delete_db_cluster_snapshot(
    db_cluster_snapshot_identifier: Annotated[
        str, Field(description='The identifier for the DB cluster snapshot to delete')
    ],
    confirmation_token: Annotated[
        Optional[str], Field(description='Confirmation token for this destructive operation')
    ] = None,
) -> Dict[str, Any]:
    """Delete a snapshot of an RDS database cluster.

    Args:
        db_cluster_snapshot_identifier: The identifier for the DB cluster snapshot to delete
        confirmation_token: Optional confirmation token for destructive operation

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    logger.info(f'Deleting DB cluster snapshot {db_cluster_snapshot_identifier}')
    response = await asyncio.to_thread(
        rds_client.delete_db_cluster_snapshot,
        DBClusterSnapshotIdentifier=db_cluster_snapshot_identifier,
    )
    logger.success(f'Successfully deleted DB cluster snapshot {db_cluster_snapshot_identifier}')

    # Format the response
    result = format_rds_api_response(response)
    formatted_snapshot = {
        'snapshot_id': response.get('DBClusterSnapshot', {}).get('DBClusterSnapshotIdentifier'),
        'cluster_id': response.get('DBClusterSnapshot', {}).get('DBClusterIdentifier'),
        'status': response.get('DBClusterSnapshot', {}).get('Status'),
        'deletion_time': response.get('DBClusterSnapshot', {}).get('SnapshotCreateTime'),
    }

    result['message'] = SUCCESS_DELETED.format(
        f'DB cluster snapshot {db_cluster_snapshot_identifier}'
    )
    result['formatted_snapshot'] = formatted_snapshot

    return result
