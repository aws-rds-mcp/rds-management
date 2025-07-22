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

"""Tool to describe Amazon RDS database clusters."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...common.utils import (
    format_cluster_info,
    format_rds_api_response,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


DESCRIBE_CLUSTERS_TOOL_DESCRIPTION = """Retrieve information about one or multiple Amazon RDS database clusters.

This tool allows you to fetch detailed information about RDS database clusters
in your account. You can retrieve information about all clusters or filter by
specific cluster identifier or other criteria.

<use_case>
Use this tool when you need programmatic access to cluster information, especially
when MCP resources are not available or when you need more control over the filtering.
</use_case>
"""


@mcp.tool(
    name='DescribeDBClusters',
    description=DESCRIBE_CLUSTERS_TOOL_DESCRIPTION,
)
@handle_exceptions
async def describe_db_clusters(
    db_cluster_identifier: Annotated[
        Optional[str],
        Field(
            description='The user-supplied DB cluster identifier. If this parameter is specified, information from only the specific DB cluster is returned'
        ),
    ] = None,
    filters: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(description='A filter that specifies one or more DB clusters to describe'),
    ] = None,
    marker: Annotated[
        Optional[str],
        Field(
            description='An optional pagination token provided by a previous DescribeDBClusters request'
        ),
    ] = None,
    max_records: Annotated[
        Optional[int],
        Field(description='The maximum number of records to include in the response'),
    ] = None,
) -> Dict[str, Any]:
    """Retrieve information about one or multiple Amazon RDS clusters.

    Args:
        db_cluster_identifier: The user-supplied DB cluster identifier
        filters: A filter that specifies one or more DB clusters to describe
        marker: An optional pagination token
        max_records: The maximum number of records to include in the response

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    params = {}

    if db_cluster_identifier:
        params['DBClusterIdentifier'] = db_cluster_identifier
    if filters:
        params['Filters'] = filters
    if marker:
        params['Marker'] = marker
    if max_records:
        params['MaxRecords'] = max_records

    logger.info('Describing DB clusters')
    response = await asyncio.to_thread(rds_client.describe_db_clusters, **params)

    result = format_rds_api_response(response)

    # format cluster information for better readability
    if 'DBClusters' in result:
        result['formatted_clusters'] = [
            format_cluster_info(cluster) for cluster in result['DBClusters']
        ]

    if db_cluster_identifier:
        result['message'] = (
            f'Successfully retrieved information for DB cluster {db_cluster_identifier}'
        )
    else:
        cluster_count = len(result.get('DBClusters', []))
        result['message'] = f'Successfully retrieved information for {cluster_count} DB clusters'

    return result
