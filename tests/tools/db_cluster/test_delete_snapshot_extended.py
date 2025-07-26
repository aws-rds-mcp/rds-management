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

"""Extended tests for delete_snapshot tool to improve coverage."""

import pytest
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    OPERATION_IMPACTS,
)
from awslabs.rds_management_mcp_server.tools.db_cluster.delete_snapshot import (
    delete_db_cluster_snapshot,
)
from botocore.exceptions import ClientError
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
def mock_rds_context_allowed():
    """Mock RDS context with readonly_mode=False."""
    with patch(
        'awslabs.rds_management_mcp_server.common.context.RDSContext.readonly_mode'
    ) as mock_readonly:
        mock_readonly.return_value = False
        yield mock_readonly


@pytest.fixture
def mock_pending_operations():
    """Mock pending operations for confirmation."""
    with patch(
        'awslabs.rds_management_mcp_server.common.decorators.require_confirmation._pending_operations'
    ) as mock_pending:
        yield mock_pending


@pytest.fixture
def add_delete_snapshot_to_impacts():
    """Add DeleteDBClusterSnapshot to OPERATION_IMPACTS temporarily."""
    # Store original value
    original_impacts = OPERATION_IMPACTS.copy()

    # Add the missing operation
    OPERATION_IMPACTS['DeleteDBClusterSnapshot'] = {
        'risk': 'critical',
        'data_loss': 'Permanent data loss',
        'downtime': 'None',
        'estimated_time': '1-2 minutes',
        'reversible': 'No - snapshot is permanently deleted',
    }

    yield

    # Restore original value
    OPERATION_IMPACTS.clear()
    OPERATION_IMPACTS.update(original_impacts)


class TestDeleteSnapshotCoverage:
    """Test delete_db_cluster_snapshot for better coverage."""

    @pytest.mark.asyncio
    async def test_delete_snapshot_successful_with_confirmation(
        self,
        mock_rds_client,
        mock_rds_context_allowed,
        mock_pending_operations,
        add_delete_snapshot_to_impacts,
    ):
        """Test successful snapshot deletion with proper confirmation flow."""
        import time

        # Set up pending operation - mock the get method
        mock_pending_operations.get.return_value = (
            'DeleteDBClusterSnapshot',
            {'db_cluster_snapshot_identifier': 'test-snapshot'},
            time.time() + 300,  # 5 minutes from now
        )

        # Mock successful deletion
        mock_rds_client.delete_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': {
                'DBClusterSnapshotIdentifier': 'test-snapshot',
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'deleting',
                'SnapshotType': 'manual',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'SnapshotCreateTime': '2025-01-01T00:00:00Z',
                'PercentProgress': 100,
                'StorageEncrypted': True,
                'Port': 3306,
                'VpcId': 'vpc-12345678',
                'TagList': [{'Key': 'test', 'Value': 'value'}],
            }
        }

        result = await delete_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot', confirmation_token='test-token'
        )

        assert result['message'] == 'Successfully deleted DB cluster snapshot test-snapshot'
        assert result['formatted_snapshot']['snapshot_id'] == 'test-snapshot'
        assert result['formatted_snapshot']['cluster_id'] == 'test-cluster'
        assert result['formatted_snapshot']['status'] == 'deleting'
        assert result['formatted_snapshot']['deletion_time'] == '2025-01-01T00:00:00Z'

        # Full details in DBClusterSnapshot
        assert result['DBClusterSnapshot']['SnapshotType'] == 'manual'
        assert result['DBClusterSnapshot']['Engine'] == 'aurora-mysql'
        assert result['DBClusterSnapshot']['EngineVersion'] == '5.7.mysql_aurora.2.10.2'
        assert result['DBClusterSnapshot']['PercentProgress'] == 100
        assert result['DBClusterSnapshot']['StorageEncrypted'] is True
        assert result['DBClusterSnapshot']['Port'] == 3306
        assert result['DBClusterSnapshot']['VpcId'] == 'vpc-12345678'
        assert result['DBClusterSnapshot']['TagList'] == [{'Key': 'test', 'Value': 'value'}]

        # Verify API call
        mock_rds_client.delete_db_cluster_snapshot.assert_called_once_with(
            DBClusterSnapshotIdentifier='test-snapshot'
        )

    @pytest.mark.asyncio
    async def test_delete_snapshot_with_complete_snapshot_data(
        self,
        mock_rds_client,
        mock_rds_context_allowed,
        mock_pending_operations,
        add_delete_snapshot_to_impacts,
    ):
        """Test deletion with all possible snapshot fields to ensure full coverage."""
        import time

        # Set up pending operation - mock the get method
        mock_pending_operations.get.return_value = (
            'DeleteDBClusterSnapshot',
            {'db_cluster_snapshot_identifier': 'full-snapshot'},
            time.time() + 300,
        )

        # Mock response with all possible fields
        mock_rds_client.delete_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': {
                'DBClusterSnapshotIdentifier': 'full-snapshot',
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'deleting',
                'SnapshotType': 'manual',
                'Engine': 'aurora-postgresql',
                'EngineVersion': '13.7',
                'SnapshotCreateTime': '2025-01-01T12:00:00Z',
                'PercentProgress': 100,
                'StorageEncrypted': True,
                'KmsKeyId': 'arn:aws:kms:us-east-1:12345:key/67890',
                'Port': 5432,
                'VpcId': 'vpc-abcdef',
                'ClusterCreateTime': '2024-12-01T00:00:00Z',
                'MasterUsername': 'postgres',
                'AllocatedStorage': 200,
                'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
                'DBClusterSnapshotArn': 'arn:aws:rds:us-east-1:12345:cluster-snapshot:full-snapshot',
                'EngineMode': 'provisioned',
                'StorageType': 'aurora',
                'Iops': 1000,
                'TagList': [
                    {'Key': 'Environment', 'Value': 'Production'},
                    {'Key': 'Owner', 'Value': 'TeamA'},
                ],
            }
        }

        result = await delete_db_cluster_snapshot(
            db_cluster_snapshot_identifier='full-snapshot', confirmation_token='test-token'
        )

        assert result['message'] == 'Successfully deleted DB cluster snapshot full-snapshot'
        assert result['formatted_snapshot']['snapshot_id'] == 'full-snapshot'
        assert result['formatted_snapshot']['cluster_id'] == 'test-cluster'
        assert result['formatted_snapshot']['status'] == 'deleting'
        assert result['formatted_snapshot']['deletion_time'] == '2025-01-01T12:00:00Z'

        # Full details in DBClusterSnapshot
        assert result['DBClusterSnapshot']['Engine'] == 'aurora-postgresql'
        assert result['DBClusterSnapshot']['Port'] == 5432
        assert result['DBClusterSnapshot']['MasterUsername'] == 'postgres'
        assert result['DBClusterSnapshot']['AllocatedStorage'] == 200
        assert result['DBClusterSnapshot']['KmsKeyId'] == 'arn:aws:kms:us-east-1:12345:key/67890'

    @pytest.mark.asyncio
    async def test_delete_snapshot_with_minimal_response(
        self,
        mock_rds_client,
        mock_rds_context_allowed,
        mock_pending_operations,
        add_delete_snapshot_to_impacts,
    ):
        """Test deletion with minimal response data."""
        import time

        # Set up pending operation - mock the get method
        mock_pending_operations.get.return_value = (
            'DeleteDBClusterSnapshot',
            {'db_cluster_snapshot_identifier': 'minimal-snapshot'},
            time.time() + 300,
        )

        # Mock response with minimal fields
        mock_rds_client.delete_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': {
                'DBClusterSnapshotIdentifier': 'minimal-snapshot',
                'Status': 'deleting',
            }
        }

        result = await delete_db_cluster_snapshot(
            db_cluster_snapshot_identifier='minimal-snapshot', confirmation_token='test-token'
        )

        assert result['message'] == 'Successfully deleted DB cluster snapshot minimal-snapshot'
        assert result['formatted_snapshot']['snapshot_id'] == 'minimal-snapshot'
        assert result['formatted_snapshot']['status'] == 'deleting'
        # Optional fields should be None if not present
        assert result['formatted_snapshot']['cluster_id'] is None
        assert result['formatted_snapshot']['deletion_time'] is None

    @pytest.mark.asyncio
    async def test_delete_snapshot_requires_confirmation_flow(
        self, mock_rds_context_allowed, add_delete_snapshot_to_impacts
    ):
        """Test the confirmation requirement flow."""
        # First call without token should require confirmation
        result = await delete_db_cluster_snapshot(db_cluster_snapshot_identifier='test-snapshot')

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result
        assert 'impact' in result
        assert 'warning' in result
        # Check for operation name in warning - the decorator formats it without spaces
        assert 'deletedbclustersnapshot' in result['warning'].lower()
        assert result['impact']['downtime'] == 'None'
        assert result['impact']['estimated_time'] == '1-2 minutes'

    @pytest.mark.asyncio
    async def test_delete_snapshot_client_error_handling(
        self,
        mock_rds_client,
        mock_rds_context_allowed,
        mock_pending_operations,
        add_delete_snapshot_to_impacts,
    ):
        """Test proper handling of various client errors."""
        import time

        # Set up pending operation - mock the get method
        mock_pending_operations.get.return_value = (
            'DeleteDBClusterSnapshot',
            {'db_cluster_snapshot_identifier': 'error-snapshot'},
            time.time() + 300,
        )

        # Test specific error codes
        mock_rds_client.delete_db_cluster_snapshot.side_effect = ClientError(
            {'Error': {'Code': 'DBClusterSnapshotNotFoundFault', 'Message': 'Snapshot not found'}},
            'DeleteDBClusterSnapshot',
        )

        result = await delete_db_cluster_snapshot(
            db_cluster_snapshot_identifier='error-snapshot', confirmation_token='test-token'
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'DBClusterSnapshotNotFoundFault'
