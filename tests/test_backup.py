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

"""Tests for RDS Management MCP Server backup module."""

import asyncio
import json
import secrets
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from botocore.exceptions import ClientError
from awslabs.rds_management_mcp_server import backup


@pytest.fixture
def sample_snapshot():
    """Return a sample DB cluster snapshot response."""
    return {
        'DBClusterSnapshotIdentifier': 'test-snapshot',
        'DBClusterIdentifier': 'test-db-cluster',
        'SnapshotCreateTime': datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        'Status': 'available',
        'Engine': 'aurora-mysql',
        'EngineVersion': '5.7.mysql_aurora.2.10.2',
        'Port': 3306,
        'VpcId': 'vpc-12345678',
        'DBClusterSnapshotArn': 'arn:aws:rds:us-east-1:123456789012:cluster-snapshot:test-snapshot',
        'TagList': [
            {
                'Key': 'Environment',
                'Value': 'Test'
            }
        ]
    }


@pytest.fixture
def sample_automated_backup():
    """Return a sample DB cluster automated backup response."""
    return {
        'DBClusterIdentifier': 'test-db-cluster',
        'DBClusterAutomatedBackupArn': 'arn:aws:rds:us-east-1:123456789012:cluster-backup:test-backup',
        'Status': 'available',
        'Engine': 'aurora-mysql',
        'EngineVersion': '5.7.mysql_aurora.2.10.2',
        'RestoreWindow': {
            'EarliestTime': datetime(2023, 6, 10, 12, 0, 0, tzinfo=timezone.utc),
            'LatestTime': datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        }
    }


@pytest.mark.asyncio
class TestCreateDbClusterSnapshot:
    """Tests for create_db_cluster_snapshot function."""

    async def test_create_snapshot_success(self, context, mock_rds_client, sample_snapshot):
        """Test successful creation of cluster snapshot."""
        # Set up the mock
        mock_rds_client.create_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': sample_snapshot
        }

        # Execute the function
        result = await backup.create_db_cluster_snapshot(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_snapshot_identifier='test-snapshot',
            db_cluster_identifier='test-db-cluster',
            tags=[{'Key': 'Environment', 'Value': 'Test'}]
        )

        # Assert the result
        assert 'message' in result
        assert 'Successfully created DB cluster snapshot' in result['message']
        assert 'formatted_snapshot' in result
        assert result['formatted_snapshot']['snapshot_id'] == 'test-snapshot'
        assert result['formatted_snapshot']['cluster_id'] == 'test-db-cluster'
        assert 'DBClusterSnapshot' in result

        # Assert the API call
        mock_rds_client.create_db_cluster_snapshot.assert_called_once()
        args, kwargs = mock_rds_client.create_db_cluster_snapshot.call_args
        assert kwargs['DBClusterSnapshotIdentifier'] == 'test-snapshot'
        assert kwargs['DBClusterIdentifier'] == 'test-db-cluster'
        assert 'Tags' in kwargs

    async def test_create_snapshot_readonly(self, context, mock_rds_client):
        """Test creation of cluster snapshot in readonly mode."""
        # Execute the function in readonly mode
        result = await backup.create_db_cluster_snapshot(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=True,
            db_cluster_snapshot_identifier='test-snapshot',
            db_cluster_identifier='test-db-cluster'
        )

        # Assert the result indicates read-only simulation
        assert 'message' in result
        assert '[READ-ONLY MODE]' in result['message']
        assert 'simulated' in result and result['simulated'] is True

        # Assert no API calls were made
        mock_rds_client.create_db_cluster_snapshot.assert_not_called()

    async def test_create_snapshot_error(self, context, mock_rds_client):
        """Test error handling for snapshot creation."""
        # Set up the mock to raise an error
        error_response = {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'DB cluster not found'}}
        mock_rds_client.create_db_cluster_snapshot.side_effect = ClientError(error_response, 'CreateDBClusterSnapshot')

        # Execute the function
        result = await backup.create_db_cluster_snapshot(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_snapshot_identifier='test-snapshot',
            db_cluster_identifier='non-existent-cluster'
        )

        # Assert the error is handled
        assert 'error' in result
        assert 'DB cluster not found' in result['error']


@pytest.mark.asyncio
class TestRestoreDbClusterFromSnapshot:
    """Tests for restore_db_cluster_from_snapshot function."""

    async def test_restore_from_snapshot_success(self, context, mock_rds_client, sample_db_cluster):
        """Test successful restore from snapshot."""
        # Set up the mock
        mock_rds_client.restore_db_cluster_from_snapshot.return_value = {
            'DBCluster': sample_db_cluster
        }

        # Execute the function
        result = await backup.restore_db_cluster_from_snapshot(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql',
            vpc_security_group_ids=['sg-12345678'],
            engine_version='5.7.mysql_aurora.2.10.2'
        )

        # Assert the result
        assert 'message' in result
        assert 'Successfully restored DB cluster' in result['message']
        assert 'formatted_cluster' in result
        assert result['formatted_cluster']['cluster_id'] == 'test-db-cluster'
        assert 'DBCluster' in result

        # Assert the API call
        mock_rds_client.restore_db_cluster_from_snapshot.assert_called_once()
        args, kwargs = mock_rds_client.restore_db_cluster_from_snapshot.call_args
        assert kwargs['DBClusterIdentifier'] == 'restored-cluster'
        assert kwargs['SnapshotIdentifier'] == 'test-snapshot'
        assert kwargs['Engine'] == 'aurora-mysql'
        assert kwargs['VpcSecurityGroupIds'] == ['sg-12345678']
        assert kwargs['EngineVersion'] == '5.7.mysql_aurora.2.10.2'

    async def test_restore_from_snapshot_readonly(self, context, mock_rds_client):
        """Test restore from snapshot in readonly mode."""
        # Execute the function in readonly mode
        result = await backup.restore_db_cluster_from_snapshot(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=True,
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql'
        )

        # Assert the result indicates read-only simulation
        assert 'message' in result
        assert '[READ-ONLY MODE]' in result['message']
        assert 'simulated' in result and result['simulated'] is True

        # Assert no API calls were made
        mock_rds_client.restore_db_cluster_from_snapshot.assert_not_called()

    async def test_restore_from_snapshot_error(self, context, mock_rds_client):
        """Test error handling for snapshot restore."""
        # Set up the mock to raise an error
        error_response = {'Error': {'Code': 'DBSnapshotNotFoundFault', 'Message': 'DB snapshot not found'}}
        mock_rds_client.restore_db_cluster_from_snapshot.side_effect = ClientError(error_response, 'RestoreDBClusterFromSnapshot')

        # Execute the function
        result = await backup.restore_db_cluster_from_snapshot(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='non-existent-snapshot',
            engine='aurora-mysql'
        )

        # Assert the error is handled
        assert 'error' in result
        assert 'DB snapshot not found' in result['error']


@pytest.mark.asyncio
class TestRestoreDbClusterToPointInTime:
    """Tests for restore_db_cluster_to_point_in_time function."""

    async def test_restore_to_point_in_time_success(self, context, mock_rds_client, sample_db_cluster):
        """Test successful point-in-time restore."""
        # Set up the mock
        mock_rds_client.restore_db_cluster_to_point_in_time.return_value = {
            'DBCluster': sample_db_cluster
        }
        
        restore_time = '2023-06-15T12:00:00Z'

        # Execute the function
        result = await backup.restore_db_cluster_to_point_in_time(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier='restored-cluster',
            source_db_cluster_identifier='test-db-cluster',
            restore_to_time=restore_time,
            vpc_security_group_ids=['sg-12345678']
        )

        # Assert the result
        assert 'message' in result
        assert 'Successfully restored DB cluster' in result['message']
        assert 'formatted_cluster' in result
        assert result['formatted_cluster']['cluster_id'] == 'test-db-cluster'
        assert 'DBCluster' in result

        # Assert the API call
        mock_rds_client.restore_db_cluster_to_point_in_time.assert_called_once()
        args, kwargs = mock_rds_client.restore_db_cluster_to_point_in_time.call_args
        assert kwargs['DBClusterIdentifier'] == 'restored-cluster'
        assert kwargs['SourceDBClusterIdentifier'] == 'test-db-cluster'
        assert kwargs['RestoreToTime'] == restore_time
        assert kwargs['VpcSecurityGroupIds'] == ['sg-12345678']

    async def test_restore_to_latest_time_success(self, context, mock_rds_client, sample_db_cluster):
        """Test successful restore to latest time."""
        # Set up the mock
        mock_rds_client.restore_db_cluster_to_point_in_time.return_value = {
            'DBCluster': sample_db_cluster
        }

        # Execute the function
        result = await backup.restore_db_cluster_to_point_in_time(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier='restored-cluster',
            source_db_cluster_identifier='test-db-cluster',
            use_latest_restorable_time=True
        )

        # Assert the result
        assert 'message' in result
        assert 'Successfully restored DB cluster' in result['message']
        
        # Assert the API call
        mock_rds_client.restore_db_cluster_to_point_in_time.assert_called_once()
        args, kwargs = mock_rds_client.restore_db_cluster_to_point_in_time.call_args
        assert kwargs['UseLatestRestorableTime'] is True

    async def test_restore_to_point_in_time_missing_time_params(self, context, mock_rds_client):
        """Test error when neither time nor latest flag is provided."""
        # Execute the function with missing parameters
        result = await backup.restore_db_cluster_to_point_in_time(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier='restored-cluster',
            source_db_cluster_identifier='test-db-cluster'
        )

        # Assert the appropriate error is returned
        assert 'error' in result
        assert 'Either restore_to_time or use_latest_restorable_time must be provided' in result['error']

        # Assert no API calls were made
        mock_rds_client.restore_db_cluster_to_point_in_time.assert_not_called()


@pytest.mark.asyncio
class TestDeleteDbClusterSnapshot:
    """Tests for delete_db_cluster_snapshot function."""

    async def test_delete_snapshot_request_confirmation(self, context, mock_rds_client):
        """Test snapshot deletion confirmation request."""
        # Mock the secrets.token_hex function to return a predictable token
        with patch('secrets.token_hex', return_value='abc123'):
            # Execute the function without a confirmation token
            result = await backup.delete_db_cluster_snapshot(
                ctx=context,
                rds_client=mock_rds_client,
                readonly=False,
                db_cluster_snapshot_identifier='test-snapshot'
            )

            # Assert the confirmation request is returned
            assert 'requires_confirmation' in result and result['requires_confirmation'] is True
            assert 'confirmation_token' in result and result['confirmation_token'] == 'abc123'
            assert 'warning' in result
            assert 'impact' in result
            assert 'message' in result

            # Assert no API calls were made
            mock_rds_client.delete_db_cluster_snapshot.assert_not_called()

    async def test_delete_snapshot_with_confirmation(self, context, mock_rds_client, sample_snapshot):
        """Test successful snapshot deletion with confirmation token."""
        # Set up the mock
        mock_rds_client.delete_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': sample_snapshot
        }

        # Execute the function with a confirmation token
        result = await backup.delete_db_cluster_snapshot(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_snapshot_identifier='test-snapshot',
            confirmation_token='valid-token'
        )

        # Assert the result
        assert 'message' in result
        assert 'Successfully deleted DB cluster snapshot' in result['message']
        assert 'formatted_snapshot' in result
        assert 'DBClusterSnapshot' in result

        # Assert the API call
        mock_rds_client.delete_db_cluster_snapshot.assert_called_once_with(
            DBClusterSnapshotIdentifier='test-snapshot'
        )


@pytest.mark.asyncio
class TestGetClusterBackupsResource:
    """Tests for get_cluster_backups_resource function."""

    async def test_get_cluster_backups_success(self, mock_rds_client, sample_snapshot, sample_automated_backup):
        """Test successful retrieval of cluster backups."""
        # Set up the mocks
        mock_rds_client.describe_db_cluster_snapshots.return_value = {
            'DBClusterSnapshots': [sample_snapshot]
        }
        mock_rds_client.describe_db_cluster_automated_backups.return_value = {
            'DBClusterAutomatedBackups': [sample_automated_backup]
        }

        # Execute the function
        result = await backup.get_cluster_backups_resource(
            db_cluster_identifier='test-db-cluster',
            rds_client=mock_rds_client
        )

        # Parse the JSON result
        parsed_result = json.loads(result)
        
        # Assert the result structure
        assert 'snapshots' in parsed_result
        assert 'automated_backups' in parsed_result
        assert 'count' in parsed_result
        assert parsed_result['count'] == 2  # 1 snapshot + 1 automated backup
        assert 'resource_uri' in parsed_result
        
        # Check snapshot details
        assert len(parsed_result['snapshots']) == 1
        assert parsed_result['snapshots'][0]['snapshot_id'] == 'test-snapshot'
        assert parsed_result['snapshots'][0]['cluster_id'] == 'test-db-cluster'
        
        # Check automated backup details
        assert len(parsed_result['automated_backups']) == 1
        assert parsed_result['automated_backups'][0]['cluster_id'] == 'test-db-cluster'
        
        # Assert API calls
        mock_rds_client.describe_db_cluster_snapshots.assert_called_once_with(
            DBClusterIdentifier='test-db-cluster'
        )
        mock_rds_client.describe_db_cluster_automated_backups.assert_called_once_with(
            DBClusterIdentifier='test-db-cluster'
        )


@pytest.mark.asyncio
class TestGetAllClusterBackupsResource:
    """Tests for get_all_cluster_backups_resource function."""

    async def test_get_all_cluster_backups_success(self, mock_rds_client, sample_db_cluster, sample_snapshot, sample_automated_backup):
        """Test successful retrieval of all cluster backups."""
        # Set up the mocks
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [sample_db_cluster]
        }
        mock_rds_client.describe_db_cluster_snapshots.return_value = {
            'DBClusterSnapshots': [sample_snapshot]
        }
        mock_rds_client.describe_db_cluster_automated_backups.return_value = {
            'DBClusterAutomatedBackups': [sample_automated_backup]
        }

        # Execute the function
        result = await backup.get_all_cluster_backups_resource(
            rds_client=mock_rds_client
        )

        # Parse the JSON result
        parsed_result = json.loads(result)
        
        # Assert the result structure
        assert 'snapshots' in parsed_result
        assert 'automated_backups' in parsed_result
        assert 'count' in parsed_result
        assert parsed_result['count'] > 0
        assert 'resource_uri' in parsed_result
        assert parsed_result['resource_uri'] == 'aws-rds://db-cluster/backups'
        
        # Assert API calls
        mock_rds_client.describe_db_clusters.assert_called_once()
        mock_rds_client.describe_db_cluster_snapshots.assert_called()
