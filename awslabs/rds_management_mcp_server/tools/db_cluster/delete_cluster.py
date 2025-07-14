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

"""Tool to delete an Amazon RDS database cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions, readonly_check, require_confirmation
from ...common.server import mcp
from ...common.utils import (
    format_cluster_info,
    format_rds_api_response,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional
from typing_extensions import Annotated


DELETE_CLUSTER_TOOL_DESCRIPTION = """Delete an RDS database cluster.

<use_case>
Use this tool to permanently remove an Amazon RDS database cluster and optionally
create a final snapshot. This operation cannot be undone, so a confirmation token is
required to prevent accidental deletion.
</use_case>

<important_notes>
1. This is a destructive operation that permanently deletes data
2. A confirmation token is required for safety - first call without token to receive one
3. By default, a final snapshot is created (skip_final_snapshot=False)
4. When creating a final snapshot (default behavior), you must provide final_db_snapshot_identifier
5. The operation may take several minutes to complete
6. All associated instances, automated backups and continuous backups (PITR) will be deleted
7. When run with readonly=True (default), this operation will be simulated but not actually performed
</important_notes>

## Response structure
If called without a confirmation token:
- `requires_confirmation`: Always true
- `warning`: Warning message about the deletion
- `impact`: Description of the impact of deletion
- `confirmation_token`: Token to use in a subsequent call
- `message`: Instructions for confirming the deletion

If called with a valid confirmation token:
- `message`: Success message confirming deletion
- `formatted_cluster`: A simplified representation of the deleted cluster
- `DBCluster`: The full AWS API response containing cluster details including:
  - `DBClusterIdentifier`: The cluster identifier
  - `Status`: The current status (usually "deleting")
  - Other cluster details

<examples>
Example usage scenarios:
1. Start deletion process (get confirmation token):
   - db_cluster_identifier="test-db-cluster"
   - skip_final_snapshot=true

2. Confirm deletion (with confirmation token):
   - db_cluster_identifier="test-db-cluster"
   - skip_final_snapshot=true
   - confirmation_token="abc123xyz" (token received from step 1)

3. Delete with final snapshot:
   - db_cluster_identifier="prod-db-cluster"
   - skip_final_snapshot=false
   - final_db_snapshot_identifier="prod-final-snapshot-20230625"
</examples>
"""


@mcp.tool(
    name='DeleteDBCluster',
    description=DELETE_CLUSTER_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('delete_db_cluster')
async def delete_db_cluster(
    db_cluster_identifier: Annotated[str, Field(description='The identifier for the DB cluster')],
    skip_final_snapshot: Annotated[
        bool,
        Field(
            description='Determines whether a final DB snapshot is created before the DB cluster is deleted'
        ),
    ] = False,
    final_db_snapshot_identifier: Annotated[
        Optional[str],
        Field(
            description='The DB snapshot identifier of the new DB snapshot created when SkipFinalSnapshot is false'
        ),
    ] = None,
    confirmation_token: Annotated[
        Optional[str], Field(description='The confirmation token for the operation')
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Delete an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        skip_final_snapshot: Determines whether a final DB snapshot is created
        final_db_snapshot_identifier: The DB snapshot identifier if creating final snapshot
        confirmation_token: The confirmation token for the operation
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        # AWS API parameters
        aws_params = {
            'DBClusterIdentifier': db_cluster_identifier,
            'SkipFinalSnapshot': skip_final_snapshot,
        }

        if not skip_final_snapshot and final_db_snapshot_identifier:
            aws_params['FinalDBSnapshotIdentifier'] = final_db_snapshot_identifier

        logger.info(f'Deleting DB cluster {db_cluster_identifier}')
        response = await asyncio.to_thread(rds_client.delete_db_cluster, **aws_params)
        logger.success(f'Successfully initiated deletion of DB cluster {db_cluster_identifier}')

        result = format_rds_api_response(response)
        result['message'] = f'Successfully deleted DB cluster {db_cluster_identifier}'
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e
