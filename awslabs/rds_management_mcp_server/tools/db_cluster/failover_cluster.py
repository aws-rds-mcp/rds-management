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

"""Tool to force a failover for an Amazon RDS database cluster."""

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


FAILOVER_CLUSTER_TOOL_DESCRIPTION = """Force a failover for an RDS database cluster.

<use_case>
Use this tool to force a failover of an Amazon RDS Multi-AZ DB cluster, promoting a read replica
to become the primary instance. This can be used for disaster recovery testing, to move the primary
to a different availability zone, or to recover from issues with the current primary instance.
</use_case>

<important_notes>
1. This operation requires explicit confirmation with a confirmation token
2. Failover causes a momentary interruption in database availability
3. Any in-flight transactions that haven't been committed may be lost during failover
4. The cluster must be in the "available" state for the failover to succeed
5. If target_db_instance_identifier is not specified, RDS chooses a replica automatically
6. When run with readonly=True (default), this operation will be simulated but not actually performed
</important_notes>

## Response structure
If called without confirmation:
- `requires_confirmation`: Always true
- `warning`: Warning message about the failover
- `impact`: Description of the impact of the failover
- `message`: Instructions for confirming the failover

If called with valid confirmation:
- `message`: Success message confirming the initiated failover
- `formatted_cluster`: A simplified representation of the cluster during failover
- `DBCluster`: The full AWS API response containing cluster details including:
  - `DBClusterIdentifier`: The cluster identifier
  - `Status`: The current status (usually "failing-over")
  - Other cluster details

<examples>
Example usage scenarios:
1. Start failover process (get warning):
   - db_cluster_identifier="production-cluster"

2. Confirm failover without specifying a target:
   - db_cluster_identifier="production-cluster"
   - confirmation_token="abc123xyz" (token received from step 1)

3. Failover to a specific replica instance:
   - db_cluster_identifier="production-cluster"
   - target_db_instance_identifier="production-instance-east-1c"
   - confirmation_token="abc123xyz" (token received from step 1)

4. Regular disaster recovery drill:
   - db_cluster_identifier="production-cluster"
   - confirmation_token="abc123xyz" (token received from step 1)
</examples>
"""


@mcp.tool(
    name='FailoverDBCluster',
    description=FAILOVER_CLUSTER_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('failover_db_cluster')
async def failover_db_cluster(
    db_cluster_identifier: Annotated[str, Field(description='The identifier for the DB cluster')],
    target_db_instance_identifier: Annotated[
        Optional[str],
        Field(description='The name of the instance to promote to the primary instance'),
    ] = None,
    confirmation_token: Annotated[
        Optional[str], Field(description='Confirmation token for destructive operation')
    ] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Force a failover for an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        target_db_instance_identifier: The name of the instance to promote to primary
        confirmation_token: Confirmation token for destructive operation
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    try:
        params = {
            'DBClusterIdentifier': db_cluster_identifier,
        }

        if target_db_instance_identifier:
            params['TargetDBInstanceIdentifier'] = target_db_instance_identifier

        logger.info(f'Initiating failover for DB cluster {db_cluster_identifier}')
        response = await asyncio.to_thread(rds_client.failover_db_cluster, **params)
        logger.success(f'Successfully initiated failover for DB cluster {db_cluster_identifier}')

        result = format_rds_api_response(response)
        result['message'] = (
            f'Successfully initiated failover for DB cluster {db_cluster_identifier}'
        )
        result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))

        return result
    except Exception as e:
        # The decorator will handle the exception
        raise e
