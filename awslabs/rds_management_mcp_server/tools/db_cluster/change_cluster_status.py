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

"""Tool to manage the status (start, stop, reboot) of a DB cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions, readonly_check, require_confirmation
from ...common.server import mcp
from ...common.utils import (
    format_cluster_info,
    format_rds_api_response,
)
from ...constants import (
    SUCCESS_REBOOTED,
    SUCCESS_STARTED,
    SUCCESS_STOPPED,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional
from typing_extensions import Annotated


CHANGE_CLUSTER_STATUS_TOOL_DESCRIPTION = """Manage the status of an RDS database cluster.

<use_case>
Use this tool to change the operational status of an Amazon RDS database cluster.
You can start a stopped cluster, stop a running cluster, or reboot a cluster to apply
configuration changes or resolve certain issues.
</use_case>

<important_notes>
1. Each action requires explicit confirmation with a confirmation token
2. Stopping a cluster will make it unavailable but will continue to incur storage charges
3. Starting a cluster will resume full billing charges
4. Rebooting causes a brief interruption but preserves cluster settings and data
5. Aurora Serverless v1 clusters cannot be stopped manually
6. When run with readonly=True (default), this operation will be simulated but not actually performed
</important_notes>

## Response structure
If called without confirmation:
- `requires_confirmation`: Always true
- `warning`: Warning message about the action
- `impact`: Description of the impact of the action
- `message`: Instructions for confirming the action

If called with valid confirmation:
- `message`: Success message confirming the action
- `formatted_cluster`: A simplified representation of the cluster in its new state
- `DBCluster`: The full AWS API response containing cluster details including:
  - `DBClusterIdentifier`: The cluster identifier
  - `Status`: The current status (e.g., "starting", "stopping", "rebooting")
  - Other cluster details

<examples>
Example usage scenarios:
1. Stop a development cluster (first call to get warning):
   - db_cluster_identifier="dev-db-cluster"
   - action="stop"

2. Confirm stopping the cluster:
   - db_cluster_identifier="dev-db-cluster"
   - action="stop"
   - confirmation_token="abc123xyz" (token received from step 1)

3. Reboot a cluster that's experiencing issues:
   - db_cluster_identifier="prod-db-cluster"
   - action="reboot"
   - confirmation_token="abc123xyz" (token received from step 1)

4. Start a previously stopped cluster:
   - db_cluster_identifier="dev-db-cluster"
   - action="start"
   - confirmation_token="abc123xyz" (token received from step 1)
</examples>
"""


@mcp.tool(
    name='ChangeDBClusterStatus',
    description=CHANGE_CLUSTER_STATUS_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('status_db_cluster')
async def status_db_cluster(
    db_cluster_identifier: Annotated[str, Field(description='The identifier for the DB cluster')],
    action: Annotated[str, Field(description='Action to perform: "start", "stop", or "reboot"')],
    confirmation_token: Annotated[
        Optional[str], Field(description='Confirmation token for destructive operations')
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Manage the status of an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        action: Action to perform: "start", "stop", or "reboot"
        confirmation_token: Confirmation token for destructive operations
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    action = action.lower()

    if action not in ['start', 'stop', 'reboot']:
        return {'error': f'Invalid action: {action}. Must be one of: start, stop, reboot'}

    try:
        if action == 'start':
            logger.info(f'Starting DB cluster {db_cluster_identifier}')
            response = await asyncio.to_thread(
                rds_client.start_db_cluster, DBClusterIdentifier=db_cluster_identifier
            )
            logger.success(f'Successfully started DB cluster {db_cluster_identifier}')

            result = format_rds_api_response(response)
            result['message'] = SUCCESS_STARTED.format(f'DB cluster {db_cluster_identifier}')

        elif action == 'stop':
            logger.info(f'Stopping DB cluster {db_cluster_identifier}')
            response = await asyncio.to_thread(
                rds_client.stop_db_cluster, DBClusterIdentifier=db_cluster_identifier
            )
            logger.success(f'Successfully stopped DB cluster {db_cluster_identifier}')

            result = format_rds_api_response(response)
            result['message'] = SUCCESS_STOPPED.format(f'DB cluster {db_cluster_identifier}')

        elif action == 'reboot':
            logger.info(f'Rebooting DB cluster {db_cluster_identifier}')
            response = await asyncio.to_thread(
                rds_client.reboot_db_cluster, DBClusterIdentifier=db_cluster_identifier
            )
            logger.success(f'Successfully initiated reboot of DB cluster {db_cluster_identifier}')

            result = format_rds_api_response(response)
            result['message'] = SUCCESS_REBOOTED.format(f'DB cluster {db_cluster_identifier}')

        # add formatted cluster info to the result
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e
