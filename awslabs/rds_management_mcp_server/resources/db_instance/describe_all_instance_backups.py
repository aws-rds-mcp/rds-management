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

"""Resource for getting backup information across all RDS DB Instances."""

from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from .describe_instance_backups import AutomatedBackupModel, BackupListModel, SnapshotModel
from loguru import logger


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
                            instance_id=backup.get('DBInstanceIdentifier'),
                            earliest_time=str(backup.get('RestorableTime'))
                            if backup.get('RestorableTime')
                            else None,
                            latest_time=str(backup.get('LatestRestorableTime'))
                            if backup.get('LatestRestorableTime')
                            else None,
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
                        instance_id=snapshot.get('DBInstanceIdentifier'),
                        creation_time=str(snapshot.get('SnapshotCreateTime'))
                        if snapshot.get('SnapshotCreateTime')
                        else None,
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
