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

"""Resource for getting backup information for RDS DB Instances."""

from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from loguru import logger
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from typing_extensions import Annotated


GET_INSTANCE_BACKUPS_RESOURCE_DESCRIPTION = """List all backups (snapshots and automated backups) for a specific DB instance.

<use_case>
Use this resource to retrieve information about all available backups for a specific DB instance.
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


class InstanceEndpoint(BaseModel):
    """DB instance endpoint model."""

    address: Optional[str] = Field(None, description='The DNS address of the instance')
    port: Optional[int] = Field(
        None, description='The port that the database engine is listening on'
    )
    hosted_zone_id: Optional[str] = Field(
        None, description='The ID of the Amazon Route 53 hosted zone'
    )


class InstanceStorage(BaseModel):
    """DB instance storage model."""

    type: Optional[str] = Field(None, description='The storage type')
    allocated: Optional[int] = Field(None, description='The allocated storage size in gibibytes')
    encrypted: Optional[bool] = Field(None, description='Whether the storage is encrypted')


class InstanceModel(BaseModel):
    """DB instance model."""

    instance_id: str = Field(description='The DB instance identifier')
    status: str = Field(description='The current status of the DB instance')
    engine: str = Field(description='The database engine')
    engine_version: Optional[str] = Field(None, description='The version of the database engine')
    instance_class: str = Field(
        description='The compute and memory capacity class of the DB instance'
    )
    endpoint: InstanceEndpoint = Field(
        default_factory=InstanceEndpoint, description='The connection endpoint'
    )
    availability_zone: Optional[str] = Field(
        None, description='The Availability Zone of the DB instance'
    )
    multi_az: bool = Field(description='Whether the DB instance is a Multi-AZ deployment')
    storage: InstanceStorage = Field(
        default_factory=InstanceStorage, description='The storage configuration'
    )
    preferred_backup_window: Optional[str] = Field(
        None, description='The daily time range during which automated backups are created'
    )
    preferred_maintenance_window: Optional[str] = Field(
        None, description='The weekly time range during which system maintenance can occur'
    )
    publicly_accessible: bool = Field(description='Whether the DB instance is publicly accessible')
    vpc_security_groups: List[VpcSecurityGroup] = Field(
        default_factory=list,
        description='A list of VPC security groups the DB instance belongs to',
    )
    db_cluster: Optional[str] = Field(
        None, description='The DB cluster identifier, if this is a member of a DB cluster'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    dbi_resource_id: Optional[str] = Field(
        None, description='The AWS Region-unique, immutable identifier for the DB instance'
    )
    resource_uri: Optional[str] = Field(None, description='The resource URI for this instance')


class InstanceListModel(BaseModel):
    """DB instance list model."""

    instances: List[InstanceModel] = Field(
        default_factory=list, description='List of DB instances'
    )
    count: int = Field(description='Total number of DB instances')
    resource_uri: str = Field(description='The resource URI for the DB instances')


class SnapshotModel(BaseModel):
    """DB Instance Snapshot model."""

    snapshot_id: str = Field(description='The identifier for the DB instance snapshot')
    cluster_id: str = Field(description='The identifier of the DB instance')
    creation_time: str = Field(description='The time when the snapshot was taken')
    status: str = Field(description='The status of the DB instance snapshot')
    engine: str = Field(description='The database engine')
    engine_version: str = Field(description='The version of the database engine')
    port: Optional[int] = Field(None, description='The port that the DB instance was listening on')
    vpc_id: Optional[str] = Field(
        None, description='The VPC ID associated with the DB instance snapshot'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    resource_uri: Optional[str] = Field(None, description='The resource URI for this snapshot')


class AutomatedBackupModel(BaseModel):
    """DB Instance Automated Backup model."""

    backup_id: str = Field(description='The identifier for the automated backup')
    cluster_id: str = Field(description='The identifier of the DB instance')
    earliest_time: str = Field(description='The earliest restorable time')
    latest_time: str = Field(description='The latest restorable time')
    status: str = Field(description='The status of the automated backup')
    engine: str = Field(description='The database engine')
    engine_version: str = Field(description='The version of the database engine')
    resource_uri: Optional[str] = Field(None, description='The resource URI for this backup')


class BackupListModel(BaseModel):
    """Backup list model including both snapshots and automated backups."""

    snapshots: List[SnapshotModel] = Field(
        default_factory=list, description='List of DB instance snapshots'
    )
    automated_backups: List[AutomatedBackupModel] = Field(
        default_factory=list, description='List of DB instance automated backups'
    )
    count: int = Field(description='Total number of backups')
    resource_uri: str = Field(description='The resource URI for the backups')


@mcp.resource(
    uri='aws-rds://db-instance/{instance_id}/backups',
    name='DescribeDBInstanceBackups',
    description=GET_INSTANCE_BACKUPS_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def describe_instance_backups(
    instance_id: Annotated[str, Field(description='The instance identifier')],
) -> BackupListModel:
    """Get all backups for a specific DB instance.

    Args:
        instance_id: Identifier of the DB instance

    Returns:
        BackupListModel: Object containing lists of snapshots and automated backups
    """
    logger.info(f'Getting backups for RDS instance: {instance_id}')
    rds_client = RDSConnectionManager.get_connection()

    # Get automated backups
    automated_backups = []
    try:
        auto_backups_response = rds_client.describe_db_instance_automated_backups(
            DBInstanceIdentifier=instance_id
        )

        for backup in auto_backups_response.get('DBInstanceAutomatedBackups', []):
            automated_backups.append(
                AutomatedBackupModel(
                    backup_id=backup.get('DBInstanceAutomatedBackupsArn'),
                    cluster_id=backup.get('DBInstanceIdentifier'),  # Using instance ID here
                    earliest_time=backup.get('RestorableTime'),
                    latest_time=backup.get('LatestRestorableTime'),
                    status=backup.get('Status'),
                    engine=backup.get('Engine'),
                    engine_version=backup.get('EngineVersion'),
                    resource_uri=f'aws-rds://db-instance/{instance_id}/backups',
                )
            )
    except Exception as e:
        logger.error(f'Error fetching automated backups for instance {instance_id}: {e}')

    # Get snapshots
    snapshots = []
    try:
        snapshots_response = rds_client.describe_db_snapshots(DBInstanceIdentifier=instance_id)

        for snapshot in snapshots_response.get('DBSnapshots', []):
            # Convert tags from AWS format to dict
            tags = {}
            for tag in snapshot.get('TagList', []):
                tags[tag.get('Key')] = tag.get('Value')

            snapshots.append(
                SnapshotModel(
                    snapshot_id=snapshot.get('DBSnapshotIdentifier'),
                    cluster_id=snapshot.get('DBInstanceIdentifier'),  # Using instance ID here
                    creation_time=snapshot.get('SnapshotCreateTime'),
                    status=snapshot.get('Status'),
                    engine=snapshot.get('Engine'),
                    engine_version=snapshot.get('EngineVersion'),
                    port=snapshot.get('Port'),
                    vpc_id=snapshot.get('VpcId'),
                    tags=tags,
                    resource_uri=f'aws-rds://db-instance/{instance_id}/backups',
                )
            )
    except Exception as e:
        logger.error(f'Error fetching snapshots for instance {instance_id}: {e}')

    # Create the combined backup list model
    backup_list = BackupListModel(
        snapshots=snapshots,
        automated_backups=automated_backups,
        count=len(snapshots) + len(automated_backups),
        resource_uri=f'aws-rds://db-instance/{instance_id}/backups',
    )

    return backup_list


GET_ALL_INSTANCE_BACKUPS_RESOURCE_DESCRIPTION = """List all backups (snapshots and automated backups) across all DB instances.

<use_case>
Use this resource to retrieve information about all available backups across all DB instances in your account.
This includes both manual snapshots and automated backups.
</use_case>

<important_notes>
1. This resource aggregates backup information from all DB instances
2. Results may be extensive if you have many instances with many backups
3. For more targeted results, use the instance-specific backup resource
</important_notes>
"""


@mcp.resource(
    uri='aws-rds://db-instance/backups',
    name='DescribeAllDBInstanceBackups',
    description=GET_ALL_INSTANCE_BACKUPS_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def describe_all_instance_backups() -> BackupListModel:
    """Get all backups across all DB instances.

    Returns:
        BackupListModel: Object containing lists of snapshots and automated backups
    """
    logger.info('Getting backups for all RDS instances')
    rds_client = RDSConnectionManager.get_connection()

    # Get all instances first
    instances_response = rds_client.describe_db_instances()
    all_snapshots = []
    all_automated_backups = []

    # For each instance, get its backups
    for instance in instances_response.get('DBInstances', []):
        instance_id = instance.get('DBInstanceIdentifier')

        # Get automated backups
        try:
            auto_backups_response = rds_client.describe_db_instance_automated_backups()

            for backup in auto_backups_response.get('DBInstanceAutomatedBackups', []):
                if backup.get('DBInstanceIdentifier') == instance_id:
                    all_automated_backups.append(
                        AutomatedBackupModel(
                            backup_id=backup.get('DBInstanceAutomatedBackupsArn'),
                            cluster_id=backup.get(
                                'DBInstanceIdentifier'
                            ),  # Using instance ID here
                            earliest_time=backup.get('RestorableTime'),
                            latest_time=backup.get('LatestRestorableTime'),
                            status=backup.get('Status'),
                            engine=backup.get('Engine'),
                            engine_version=backup.get('EngineVersion'),
                            resource_uri='aws-rds://db-instance/backups',
                        )
                    )
        except Exception as e:
            logger.error(f'Error fetching automated backups for instance {instance_id}: {e}')

        # Get snapshots
        try:
            snapshots_response = rds_client.describe_db_snapshots(DBInstanceIdentifier=instance_id)

            for snapshot in snapshots_response.get('DBSnapshots', []):
                # Convert tags from AWS format to dict
                tags = {}
                for tag in snapshot.get('TagList', []):
                    tags[tag.get('Key')] = tag.get('Value')

                all_snapshots.append(
                    SnapshotModel(
                        snapshot_id=snapshot.get('DBSnapshotIdentifier'),
                        cluster_id=snapshot.get('DBInstanceIdentifier'),  # Using instance ID here
                        creation_time=snapshot.get('SnapshotCreateTime'),
                        status=snapshot.get('Status'),
                        engine=snapshot.get('Engine'),
                        engine_version=snapshot.get('EngineVersion'),
                        port=snapshot.get('Port'),
                        vpc_id=snapshot.get('VpcId'),
                        tags=tags,
                        resource_uri='aws-rds://db-instance/backups',
                    )
                )
        except Exception as e:
            logger.error(f'Error fetching snapshots for instance {instance_id}: {e}')

    # Create the combined backup list model
    backup_list = BackupListModel(
        snapshots=all_snapshots,
        automated_backups=all_automated_backups,
        count=len(all_snapshots) + len(all_automated_backups),
        resource_uri='aws-rds://db-instance/backups',
    )

    return backup_list
