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

"""Resource for getting backup information for RDS DB Clusters."""

from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from loguru import logger
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from typing_extensions import Annotated


GET_CLUSTER_BACKUPS_RESOURCE_DESCRIPTION = """List all backups (snapshots and automated backups) for a specific DB cluster.

<use_case>
Use this resource to retrieve information about all available backups for a specific DB cluster.
This includes both manual snapshots and automated backups.
</use_case>

<important_notes>
1. Snapshots are point-in-time copies of your database that you can use to restore to a specific state
2. Automated backups are system-generated backups that allow point-in-time recovery
3. Both types of backups can be used for restoring your database
</important_notes>
"""


class VpcSecurityGroup(BaseModel):
    """VPC security group model."""

    id: str = Field(description='The VPC security group ID')
    status: str = Field(description='The status of the VPC security group')


class ClusterMember(BaseModel):
    """DB cluster member model."""

    instance_id: str = Field(description='The instance identifier of the DB cluster member')
    is_writer: bool = Field(description='Whether the cluster member is a writer instance')
    status: Optional[str] = Field(
        None, description='The status of the DB cluster parameter group for this member'
    )


class ClusterModel(BaseModel):
    """DB cluster model."""

    cluster_id: str = Field(description='The DB cluster identifier')
    status: str = Field(description='The current status of the DB cluster')
    engine: str = Field(description='The database engine')
    engine_version: Optional[str] = Field(None, description='The version of the database engine')
    endpoint: Optional[str] = Field(
        None, description='The connection endpoint for the primary instance'
    )
    reader_endpoint: Optional[str] = Field(
        None, description='The reader endpoint for the DB cluster'
    )
    multi_az: bool = Field(
        description='Whether the DB cluster has instances in multiple Availability Zones'
    )
    backup_retention: int = Field(description='The retention period for automated backups')
    preferred_backup_window: Optional[str] = Field(
        None, description='The daily time range during which automated backups are created'
    )
    preferred_maintenance_window: Optional[str] = Field(
        None, description='The weekly time range during which system maintenance can occur'
    )
    created_time: Optional[str] = Field(
        None, description='The time when the DB cluster was created'
    )
    members: List[ClusterMember] = Field(
        default_factory=list, description='A list of DB cluster members'
    )
    vpc_security_groups: List[VpcSecurityGroup] = Field(
        default_factory=list, description='A list of VPC security groups the DB cluster belongs to'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    resource_uri: Optional[str] = Field(None, description='The resource URI for this cluster')


class ClusterListModel(BaseModel):
    """DB cluster list model."""

    clusters: List[ClusterModel] = Field(default_factory=list, description='List of DB clusters')
    count: int = Field(description='Total number of DB clusters')
    resource_uri: str = Field(description='The resource URI for the DB clusters')


class SnapshotModel(BaseModel):
    """DB Cluster Snapshot model."""

    snapshot_id: str = Field(description='The identifier for the DB cluster snapshot')
    cluster_id: str = Field(description='The identifier of the DB cluster')
    creation_time: str = Field(description='The time when the snapshot was taken')
    status: str = Field(description='The status of the DB cluster snapshot')
    engine: str = Field(description='The database engine')
    engine_version: str = Field(description='The version of the database engine')
    port: Optional[int] = Field(None, description='The port that the DB cluster was listening on')
    vpc_id: Optional[str] = Field(
        None, description='The VPC ID associated with the DB cluster snapshot'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    resource_uri: Optional[str] = Field(None, description='The resource URI for this snapshot')


class AutomatedBackupModel(BaseModel):
    """DB Cluster Automated Backup model."""

    backup_id: str = Field(description='The identifier for the automated backup')
    cluster_id: str = Field(description='The identifier of the DB cluster')
    earliest_time: str = Field(description='The earliest restorable time')
    latest_time: str = Field(description='The latest restorable time')
    status: str = Field(description='The status of the automated backup')
    engine: str = Field(description='The database engine')
    engine_version: str = Field(description='The version of the database engine')
    resource_uri: Optional[str] = Field(None, description='The resource URI for this backup')


class BackupListModel(BaseModel):
    """Backup list model including both snapshots and automated backups."""

    snapshots: List[SnapshotModel] = Field(
        default_factory=list, description='List of DB cluster snapshots'
    )
    automated_backups: List[AutomatedBackupModel] = Field(
        default_factory=list, description='List of DB cluster automated backups'
    )
    count: int = Field(description='Total number of backups')
    resource_uri: str = Field(description='The resource URI for the backups')


@mcp.resource(
    uri='aws-rds://db-cluster/{cluster_id}/backups',
    name='DescribeDBClusterBackups',
    description=GET_CLUSTER_BACKUPS_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def describe_cluster_backups(
    cluster_id: Annotated[str, Field(description='The cluster identifier')],
) -> BackupListModel:
    """Get all backups for a specific DB cluster.

    Args:
        cluster_id: Identifier of the DB cluster

    Returns:
        BackupListModel: Object containing lists of snapshots and automated backups
    """
    logger.info(f'Getting backups for RDS cluster: {cluster_id}')
    rds_client = RDSConnectionManager.get_connection()

    # Get automated backups
    automated_backups = []
    try:
        auto_backups_response = rds_client.describe_db_cluster_automated_backups(
            DBClusterIdentifier=cluster_id
        )

        for backup in auto_backups_response.get('DBClusterAutomatedBackups', []):
            automated_backups.append(
                AutomatedBackupModel(
                    backup_id=backup.get('DBClusterAutomatedBackupArn'),
                    cluster_id=backup.get('DBClusterIdentifier'),
                    earliest_time=backup.get('RestoreWindow', {}).get('EarliestTime'),
                    latest_time=backup.get('RestoreWindow', {}).get('LatestTime'),
                    status=backup.get('Status'),
                    engine=backup.get('Engine'),
                    engine_version=backup.get('EngineVersion'),
                    resource_uri=f'aws-rds://db-cluster/{cluster_id}/backups',
                )
            )
    except Exception as e:
        logger.error(f'Error fetching automated backups for cluster {cluster_id}: {e}')

    # Get snapshots
    snapshots = []
    try:
        snapshots_response = rds_client.describe_db_cluster_snapshots(
            DBClusterIdentifier=cluster_id
        )

        for snapshot in snapshots_response.get('DBClusterSnapshots', []):
            # Convert tags from AWS format to dict
            tags = {}
            for tag in snapshot.get('TagList', []):
                tags[tag.get('Key')] = tag.get('Value')

            snapshots.append(
                SnapshotModel(
                    snapshot_id=snapshot.get('DBClusterSnapshotIdentifier'),
                    cluster_id=snapshot.get('DBClusterIdentifier'),
                    creation_time=snapshot.get('SnapshotCreateTime'),
                    status=snapshot.get('Status'),
                    engine=snapshot.get('Engine'),
                    engine_version=snapshot.get('EngineVersion'),
                    port=snapshot.get('Port'),
                    vpc_id=snapshot.get('VpcId'),
                    tags=tags,
                    resource_uri=f'aws-rds://db-cluster/{cluster_id}/backups',
                )
            )
    except Exception as e:
        logger.error(f'Error fetching snapshots for cluster {cluster_id}: {e}')

    # Create the combined backup list model
    backup_list = BackupListModel(
        snapshots=snapshots,
        automated_backups=automated_backups,
        count=len(snapshots) + len(automated_backups),
        resource_uri=f'aws-rds://db-cluster/{cluster_id}/backups',
    )

    return backup_list


GET_ALL_CLUSTER_BACKUPS_RESOURCE_DESCRIPTION = """List all backups (snapshots and automated backups) across all DB clusters.

<use_case>
Use this resource to retrieve information about all available backups across all DB clusters in your account.
This includes both manual snapshots and automated backups.
</use_case>

<important_notes>
1. This resource aggregates backup information from all DB clusters
2. Results may be extensive if you have many clusters with many backups
3. For more targeted results, use the cluster-specific backup resource
</important_notes>
"""


@mcp.resource(
    uri='aws-rds://db-cluster/backups',
    name='DescribeAllDBClusterBackups',
    description=GET_ALL_CLUSTER_BACKUPS_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def describe_all_cluster_backups() -> BackupListModel:
    """Get all backups across all DB clusters.

    Returns:
        BackupListModel: Object containing lists of snapshots and automated backups
    """
    logger.info('Getting backups for all RDS clusters')
    rds_client = RDSConnectionManager.get_connection()

    # Get all clusters first
    clusters_response = rds_client.describe_db_clusters()
    all_snapshots = []
    all_automated_backups = []

    # For each cluster, get its backups
    for cluster in clusters_response.get('DBClusters', []):
        cluster_id = cluster.get('DBClusterIdentifier')

        # Get automated backups
        try:
            auto_backups_response = rds_client.describe_db_cluster_automated_backups()

            for backup in auto_backups_response.get('DBClusterAutomatedBackups', []):
                if backup.get('DBClusterIdentifier') == cluster_id:
                    all_automated_backups.append(
                        AutomatedBackupModel(
                            backup_id=backup.get('DBClusterAutomatedBackupArn'),
                            cluster_id=backup.get('DBClusterIdentifier'),
                            earliest_time=backup.get('RestoreWindow', {}).get('EarliestTime'),
                            latest_time=backup.get('RestoreWindow', {}).get('LatestTime'),
                            status=backup.get('Status'),
                            engine=backup.get('Engine'),
                            engine_version=backup.get('EngineVersion'),
                            resource_uri='aws-rds://db-cluster/backups',
                        )
                    )
        except Exception as e:
            logger.error(f'Error fetching automated backups for cluster {cluster_id}: {e}')

        # Get snapshots
        try:
            snapshots_response = rds_client.describe_db_cluster_snapshots(
                DBClusterIdentifier=cluster_id
            )

            for snapshot in snapshots_response.get('DBClusterSnapshots', []):
                # Convert tags from AWS format to dict
                tags = {}
                for tag in snapshot.get('TagList', []):
                    tags[tag.get('Key')] = tag.get('Value')

                all_snapshots.append(
                    SnapshotModel(
                        snapshot_id=snapshot.get('DBClusterSnapshotIdentifier'),
                        cluster_id=snapshot.get('DBClusterIdentifier'),
                        creation_time=snapshot.get('SnapshotCreateTime'),
                        status=snapshot.get('Status'),
                        engine=snapshot.get('Engine'),
                        engine_version=snapshot.get('EngineVersion'),
                        port=snapshot.get('Port'),
                        vpc_id=snapshot.get('VpcId'),
                        tags=tags,
                        resource_uri='aws-rds://db-cluster/backups',
                    )
                )
        except Exception as e:
            logger.error(f'Error fetching snapshots for cluster {cluster_id}: {e}')

    # Create the combined backup list model
    backup_list = BackupListModel(
        snapshots=all_snapshots,
        automated_backups=all_automated_backups,
        count=len(all_snapshots) + len(all_automated_backups),
        resource_uri='aws-rds://db-cluster/backups',
    )

    return backup_list
