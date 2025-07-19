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

"""Resource for getting detailed information about a specific RDS DB Cluster."""

from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...common.utils import convert_datetime_to_string
from ...models import ClusterMember, ClusterModel, VpcSecurityGroup
from loguru import logger
from pydantic import Field
from typing_extensions import Annotated


GET_CLUSTER_DETAIL_RESOURCE_DESCRIPTION = """Get detailed information about a specific Amazon RDS cluster.

<use_case>
Use this resource to retrieve comprehensive details about a specific RDS database cluster
identified by its cluster ID. This provides deeper insights than the cluster list resource.
</use_case>

<important_notes>
1. The cluster ID must exist in your AWS account and region
2. The response contains full configuration details about the specified cluster
3. This resource includes information not available in the list view such as parameter groups,
   backup configuration, and maintenance windows
4. Use the cluster list resource first to identify valid cluster IDs
5. Error responses will be returned if the cluster doesn't exist or there are permission issues
</important_notes>

## Response structure
Returns a JSON document containing detailed cluster information:
- All fields from the list view plus:
- `endpoint`: The primary endpoint for connecting to the cluster
- `reader_endpoint`: The reader endpoint for read operations (if applicable)
- `port`: The port the database engine is listening on
- `parameter_group`: Database parameter group information
- `backup_retention_period`: How long backups are retained (in days)
- `preferred_backup_window`: When automated backups occur
- `preferred_maintenance_window`: When maintenance operations can occur
- `resource_uri`: The full resource URI for this specific cluster
"""


@mcp.resource(
    uri='aws-rds://db-cluster/{cluster_id}',
    name='GetDBClusterDetail',
    description=GET_CLUSTER_DETAIL_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def get_cluster_detail(
    cluster_id: Annotated[str, Field(description='The cluster identifier')],
) -> ClusterModel:
    """Get detailed information about a specific RDS cluster.

    Retrieves comprehensive details about a specific RDS database cluster identified
    by its cluster ID. This provides detailed insights into the cluster's configuration,
    performance, and status.

    Args:
        cluster_id: The identifier of the DB cluster to retrieve details for

    Returns:
        ClusterModel: Object containing detailed information about the DB cluster
    """
    logger.info(f'Getting details for RDS cluster: {cluster_id}')
    rds_client = RDSConnectionManager.get_connection()

    response = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)
    clusters = response.get('DBClusters', [])

    if not clusters:
        raise ValueError(f'DB cluster {cluster_id} not found')

    cluster_data = clusters[0]

    # Format cluster members
    members = []
    for member in cluster_data.get('DBClusterMembers', []):
        members.append(
            ClusterMember(
                instance_id=member.get('DBInstanceIdentifier'),
                is_writer=member.get('IsClusterWriter'),
                status=member.get('DBClusterParameterGroupStatus'),
            )
        )

    # Format VPC security groups
    vpc_security_groups = []
    for sg in cluster_data.get('VpcSecurityGroups', []):
        vpc_security_groups.append(
            VpcSecurityGroup(id=sg.get('VpcSecurityGroupId'), status=sg.get('Status'))
        )

    # Format tags
    tags = {}
    if cluster_data.get('TagList'):
        for tag in cluster_data.get('TagList', []):
            if 'Key' in tag and 'Value' in tag:
                tags[tag['Key']] = tag['Value']

    # Create the cluster model
    cluster = ClusterModel(
        cluster_id=cluster_data.get('DBClusterIdentifier'),
        status=cluster_data.get('Status'),
        engine=cluster_data.get('Engine'),
        engine_version=cluster_data.get('EngineVersion'),
        endpoint=cluster_data.get('Endpoint'),
        reader_endpoint=cluster_data.get('ReaderEndpoint'),
        multi_az=cluster_data.get('MultiAZ', False),
        backup_retention=cluster_data.get('BackupRetentionPeriod', 0),
        preferred_backup_window=cluster_data.get('PreferredBackupWindow'),
        preferred_maintenance_window=cluster_data.get('PreferredMaintenanceWindow'),
        created_time=convert_datetime_to_string(cluster_data.get('ClusterCreateTime')),
        members=members,
        vpc_security_groups=vpc_security_groups,
        tags=tags,
        resource_uri=f'aws-rds://db-cluster/{cluster_id}',
    )

    return cluster
