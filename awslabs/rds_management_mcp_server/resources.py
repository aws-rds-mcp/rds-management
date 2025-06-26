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

"""Resource implementations for RDS Management MCP Server."""

import asyncio
import json
from typing import Any, Dict
from loguru import logger
from .constants import (
    RESOURCE_PREFIX_CLUSTER,
)
from .utils import format_cluster_info, handle_aws_error


async def get_cluster_list_resource(rds_client: Any) -> str:
    """Get list of all RDS clusters as a resource.
    
    Args:
        rds_client: AWS RDS client
        
    Returns:
        JSON string with cluster list
    """
    try:
        logger.info("Getting cluster list resource")
        response = await asyncio.to_thread(rds_client.describe_db_clusters)
        
        clusters = []
        for cluster in response.get('DBClusters', []):
            clusters.append(format_cluster_info(cluster))
        
        result = {
            'clusters': clusters,
            'count': len(clusters),
            'resource_uri': RESOURCE_PREFIX_CLUSTER,
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        error_result = await handle_aws_error('get_cluster_list_resource', e)
        return json.dumps(error_result, indent=2)


async def get_cluster_detail_resource(cluster_id: str, rds_client: Any) -> str:
    """Get detailed information about a specific cluster as a resource.
    
    Args:
        cluster_id: The cluster identifier
        rds_client: AWS RDS client
        
    Returns:
        JSON string with cluster details
    """
    try:
        logger.info(f"Getting cluster detail resource for {cluster_id}")
        response = await asyncio.to_thread(
            rds_client.describe_db_clusters,
            DBClusterIdentifier=cluster_id
        )
        
        clusters = response.get('DBClusters', [])
        if not clusters:
            return json.dumps({'error': f'Cluster {cluster_id} not found'}, indent=2)
        
        cluster = format_cluster_info(clusters[0])
        cluster['resource_uri'] = f'{RESOURCE_PREFIX_CLUSTER}/{cluster_id}'
        
        return json.dumps(cluster, indent=2)
    except Exception as e:
        error_result = await handle_aws_error(f'get_cluster_detail_resource({cluster_id})', e)
        return json.dumps(error_result, indent=2)
