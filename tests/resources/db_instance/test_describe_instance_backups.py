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

"""Tests for describe_instance_backups resource."""

import pytest
from awslabs.rds_management_mcp_server.resources.db_instance.describe_all_instance_backups import (
    describe_all_instance_backups,
)
from awslabs.rds_management_mcp_server.resources.db_instance.describe_instance_backups import (
    AutomatedBackupModel,
    BackupListModel,
    SnapshotModel,
    describe_instance_backups,
)
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_rds_client():
    """Mock RDS client."""
    with patch(
        'awslabs.rds_management_mcp_server.common.connection.RDSConnectionManager.get_connection'
    ) as mock_get_connection:
        mock_client = MagicMock()
        mock_get_connection.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_automated_backup():
    """Sample automated backup data."""
    return {
        'DBInstanceAutomatedBackupsArn': 'arn:aws:rds:us-east-1:123456789012:auto-backup:test-backup',
        'DBInstanceIdentifier': 'test-instance',
        'Engine': 'mysql',
        'Status': 'available',
        'RestorableTime': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        'LatestRestorableTime': datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        'AllocatedStorage': 100,
        'EngineVersion': '8.0.35',
        'VpcId': 'vpc-12345678',
        'InstanceCreateTime': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        'MasterUsername': 'admin',
        'BackupRetentionPeriod': 7,
        'StorageEncrypted': True,
        'KmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
        'AvailabilityZone': 'us-east-1a',
        'PreferredBackupWindow': '03:00-04:00',
        'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
        'Port': 3306,
        'DBInstanceClass': 'db.t3.micro',
        'StorageType': 'gp3',
        'Iops': 3000,
        'BackupTarget': 'REGION',
    }


@pytest.fixture
def sample_snapshot():
    """Sample snapshot data."""
    return {
        'DBSnapshotIdentifier': 'test-snapshot',
        'DBInstanceIdentifier': 'test-instance',
        'SnapshotCreateTime': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        'Engine': 'mysql',
        'EngineVersion': '8.0.35',
        'Status': 'available',
        'AllocatedStorage': 100,
        'MasterUsername': 'admin',
        'Port': 3306,
        'VpcId': 'vpc-12345678',
        'InstanceCreateTime': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        'StorageEncrypted': True,
        'KmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
        'DBSnapshotArn': 'arn:aws:rds:us-east-1:123456789012:snapshot:test-snapshot',
        'PercentProgress': 100,
        'SnapshotType': 'manual',
        'AvailabilityZone': 'us-east-1a',
        'StorageType': 'gp3',
        'Iops': 3000,
        'TagList': [{'Key': 'Environment', 'Value': 'Test'}],
    }


class TestDescribeInstanceBackups:
    """Test describe_instance_backups function."""

    @pytest.mark.asyncio
    async def test_describe_instance_backups_success(
        self, mock_rds_client, sample_automated_backup, sample_snapshot
    ):
        """Test successful instance backups retrieval."""
        # Mock automated backups
        mock_rds_client.describe_db_instance_automated_backups.return_value = {
            'DBInstanceAutomatedBackups': [sample_automated_backup]
        }

        # Mock snapshots
        mock_rds_client.describe_db_snapshots.return_value = {'DBSnapshots': [sample_snapshot]}

        result = await describe_instance_backups('test-instance')

        assert isinstance(result, BackupListModel)
        assert result.count == 2
        assert len(result.automated_backups) == 1
        assert len(result.snapshots) == 1

        # Verify automated backup
        auto_backup = result.automated_backups[0]
        assert (
            auto_backup.backup_id == 'arn:aws:rds:us-east-1:123456789012:auto-backup:test-backup'
        )
        assert auto_backup.instance_id == 'test-instance'
        assert auto_backup.status == 'available'
        assert auto_backup.engine == 'mysql'
        assert auto_backup.engine_version == '8.0.35'

        # Verify snapshot
        snapshot = result.snapshots[0]
        assert snapshot.snapshot_id == 'test-snapshot'
        assert snapshot.instance_id == 'test-instance'
        assert snapshot.status == 'available'
        assert snapshot.engine == 'mysql'
        assert snapshot.engine_version == '8.0.35'
        assert snapshot.port == 3306
        assert snapshot.vpc_id == 'vpc-12345678'
        assert snapshot.tags == {'Environment': 'Test'}

    @pytest.mark.asyncio
    async def test_describe_instance_backups_no_backups(self, mock_rds_client):
        """Test instance backups with no backups found."""
        mock_rds_client.describe_db_instance_automated_backups.return_value = {
            'DBInstanceAutomatedBackups': []
        }
        mock_rds_client.describe_db_snapshots.return_value = {'DBSnapshots': []}

        result = await describe_instance_backups('test-instance')

        assert result.count == 0
        assert len(result.automated_backups) == 0
        assert len(result.snapshots) == 0

    @pytest.mark.asyncio
    async def test_describe_instance_backups_handles_exception(self, mock_rds_client):
        """Test error handling in describe_instance_backups."""
        # One succeeds, one fails - should still return partial results
        mock_rds_client.describe_db_instance_automated_backups.side_effect = Exception(
            'Automated backups error'
        )
        mock_rds_client.describe_db_snapshots.return_value = {'DBSnapshots': []}

        result = await describe_instance_backups('test-instance')

        # Should still return result with empty automated backups
        assert result.count == 0
        assert len(result.automated_backups) == 0
        assert len(result.snapshots) == 0

    @pytest.mark.asyncio
    async def test_describe_instance_backups_multiple_backups(
        self, mock_rds_client, sample_automated_backup, sample_snapshot
    ):
        """Test instance backups with multiple backups of each type."""
        # Create multiple backups
        backup2 = sample_automated_backup.copy()
        backup2['DBInstanceAutomatedBackupsArn'] = (
            'arn:aws:rds:us-east-1:123456789012:auto-backup:test-backup-2'
        )

        snapshot2 = sample_snapshot.copy()
        snapshot2['DBSnapshotIdentifier'] = 'test-snapshot-2'

        # Mock responses
        mock_rds_client.describe_db_instance_automated_backups.return_value = {
            'DBInstanceAutomatedBackups': [sample_automated_backup, backup2]
        }
        mock_rds_client.describe_db_snapshots.return_value = {
            'DBSnapshots': [sample_snapshot, snapshot2]
        }

        result = await describe_instance_backups('test-instance')

        assert result.count == 4
        assert len(result.automated_backups) == 2
        assert len(result.snapshots) == 2


class TestDescribeAllInstanceBackups:
    """Test describe_all_instance_backups function."""

    @pytest.mark.asyncio
    async def test_describe_all_instance_backups_success(
        self, mock_rds_client, sample_automated_backup, sample_snapshot
    ):
        """Test successful all instance backups retrieval."""
        # Mock instances
        mock_rds_client.describe_db_instances.return_value = {
            'DBInstances': [
                {'DBInstanceIdentifier': 'test-instance'},
                {'DBInstanceIdentifier': 'test-instance-2'},
            ]
        }

        # Mock automated backups for all instances
        backup2 = sample_automated_backup.copy()
        backup2['DBInstanceIdentifier'] = 'test-instance-2'
        backup2['DBInstanceAutomatedBackupsArn'] = (
            'arn:aws:rds:us-east-1:123456789012:auto-backup:test-backup-2'
        )

        mock_rds_client.describe_db_instance_automated_backups.return_value = {
            'DBInstanceAutomatedBackups': [sample_automated_backup, backup2]
        }

        # Mock snapshots - one for each instance
        snapshot2 = sample_snapshot.copy()
        snapshot2['DBInstanceIdentifier'] = 'test-instance-2'
        snapshot2['DBSnapshotIdentifier'] = 'test-snapshot-2'

        mock_rds_client.describe_db_snapshots.side_effect = [
            {'DBSnapshots': [sample_snapshot]},
            {'DBSnapshots': [snapshot2]},
        ]

        result = await describe_all_instance_backups()

        assert isinstance(result, BackupListModel)
        assert result.count == 4  # 2 automated backups + 2 snapshots
        assert len(result.automated_backups) == 2
        assert len(result.snapshots) == 2

        # Verify automated backups
        backup_instance_ids = [b.instance_id for b in result.automated_backups]
        assert 'test-instance' in backup_instance_ids
        assert 'test-instance-2' in backup_instance_ids

        # Verify snapshots
        snapshot_ids = [s.snapshot_id for s in result.snapshots]
        assert 'test-snapshot' in snapshot_ids
        assert 'test-snapshot-2' in snapshot_ids

    @pytest.mark.asyncio
    async def test_describe_all_instance_backups_no_instances(self, mock_rds_client):
        """Test all instance backups with no instances."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': []}

        result = await describe_all_instance_backups()

        assert result.count == 0
        assert len(result.automated_backups) == 0
        assert len(result.snapshots) == 0

    @pytest.mark.asyncio
    async def test_describe_all_instance_backups_handles_errors(
        self, mock_rds_client, sample_snapshot
    ):
        """Test error handling when fetching backups fails for some instances."""
        # Mock instances
        mock_rds_client.describe_db_instances.return_value = {
            'DBInstances': [
                {'DBInstanceIdentifier': 'test-instance'},
                {'DBInstanceIdentifier': 'test-instance-2'},
            ]
        }

        # Mock automated backups - fails
        mock_rds_client.describe_db_instance_automated_backups.side_effect = Exception(
            'Automated backups error'
        )

        # Mock snapshots - first succeeds, second fails
        mock_rds_client.describe_db_snapshots.side_effect = [
            {'DBSnapshots': [sample_snapshot]},
            Exception('Snapshot error'),
        ]

        result = await describe_all_instance_backups()

        # Should still return partial results
        assert result.count == 1
        assert len(result.automated_backups) == 0
        assert len(result.snapshots) == 1
        assert result.snapshots[0].snapshot_id == 'test-snapshot'


class TestBackupModels:
    """Test backup-related models."""

    def test_automated_backup_model_creation(self):
        """Test AutomatedBackupModel creation."""
        backup = AutomatedBackupModel(
            backup_id='arn:aws:rds:us-east-1:123456789012:auto-backup:test-backup',
            instance_id='test-instance',
            earliest_time='2025-01-01T00:00:00Z',
            latest_time='2025-01-02T00:00:00Z',
            status='available',
            engine='mysql',
            engine_version='8.0.35',
            resource_uri='aws-rds://db-instance/test-instance/backups',
        )

        assert backup.backup_id == 'arn:aws:rds:us-east-1:123456789012:auto-backup:test-backup'
        assert backup.instance_id == 'test-instance'
        assert backup.status == 'available'
        assert backup.engine == 'mysql'

    def test_snapshot_model_creation(self):
        """Test SnapshotModel creation."""
        snapshot = SnapshotModel(
            snapshot_id='test-snapshot',
            instance_id='test-instance',
            creation_time='2025-01-01T00:00:00Z',
            status='available',
            engine='mysql',
            engine_version='8.0.35',
            port=3306,
            vpc_id='vpc-12345678',
            tags={'Environment': 'Test'},
            resource_uri='aws-rds://db-instance/test-instance/backups',
        )

        assert snapshot.snapshot_id == 'test-snapshot'
        assert snapshot.instance_id == 'test-instance'
        assert snapshot.status == 'available'
        assert snapshot.engine == 'mysql'
        assert snapshot.port == 3306
        assert snapshot.tags == {'Environment': 'Test'}

    def test_backup_list_model_creation(self):
        """Test BackupListModel creation."""
        automated_backup = AutomatedBackupModel(
            backup_id='backup1',
            instance_id='test-instance',
            earliest_time='2025-01-01T00:00:00Z',
            latest_time='2025-01-02T00:00:00Z',
            status='available',
            engine='mysql',
            engine_version='8.0.35',
            resource_uri='aws-rds://db-instance/test-instance/backups',
        )

        snapshot = SnapshotModel(
            snapshot_id='snapshot1',
            instance_id='test-instance',
            creation_time='2025-01-01T00:00:00Z',
            status='available',
            engine='mysql',
            engine_version='8.0.35',
            resource_uri='aws-rds://db-instance/test-instance/backups',
        )

        backup_list = BackupListModel(
            snapshots=[snapshot],
            automated_backups=[automated_backup],
            count=2,
            resource_uri='aws-rds://db-instance/test-instance/backups',
        )

        assert backup_list.count == 2
        assert len(backup_list.snapshots) == 1
        assert len(backup_list.automated_backups) == 1
        assert backup_list.snapshots[0].snapshot_id == 'snapshot1'
        assert backup_list.automated_backups[0].backup_id == 'backup1'

    def test_backup_list_model_with_minimal_data(self):
        """Test BackupListModel with minimal required data."""
        # Test with minimal required fields
        minimal_snapshot = SnapshotModel(
            snapshot_id='minimal-snapshot',
            instance_id='test-instance',
            creation_time='2025-01-01T00:00:00Z',
            status='available',
            engine='mysql',
            engine_version='8.0.35',
        )

        backup_list = BackupListModel(
            snapshots=[minimal_snapshot],
            automated_backups=[],
            count=1,
            resource_uri='aws-rds://db-instance/test-instance/backups',
        )

        assert backup_list.count == 1
        assert len(backup_list.snapshots) == 1
        assert backup_list.snapshots[0].port is None  # Optional field
        assert backup_list.snapshots[0].vpc_id is None  # Optional field
        assert backup_list.snapshots[0].tags == {}  # Default empty dict
