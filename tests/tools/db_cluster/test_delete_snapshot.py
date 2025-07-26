"""Tests for delete_snapshot tool."""

import pytest
import time
from awslabs.rds_management_mcp_server.tools.db_cluster.delete_snapshot import (
    delete_db_cluster_snapshot,
)
from unittest.mock import patch


class TestDeleteSnapshot:
    """Test cases for delete_db_cluster_snapshot function."""

    @pytest.mark.asyncio
    async def test_delete_snapshot_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful snapshot deletion."""
        # Mock the pending operation for confirmation
        with patch(
            'awslabs.rds_management_mcp_server.common.decorators.require_confirmation._pending_operations'
        ) as mock_pending:
            mock_pending.get.return_value = (
                'DeleteDBClusterSnapshot',
                {'db_cluster_snapshot_identifier': 'test-snapshot'},
                time.time() + 300,  # 5 minutes from now
            )

            mock_rds_client.delete_db_cluster_snapshot.return_value = {
                'DBClusterSnapshot': {
                    'DBClusterSnapshotIdentifier': 'test-snapshot',
                    'DBClusterIdentifier': 'test-cluster',
                    'Status': 'deleting',
                    'SnapshotType': 'manual',
                    'Engine': 'aurora-mysql',
                    'EngineVersion': '5.7.mysql_aurora.2.10.2',
                }
            }

            async def async_return(func, **kwargs):
                return func(**kwargs)

            mock_asyncio_thread.side_effect = async_return

            result = await delete_db_cluster_snapshot(
                db_cluster_snapshot_identifier='test-snapshot', confirmation_token='test-token'
            )

            assert result['message'] == 'Successfully deleted DB cluster snapshot test-snapshot'
            assert result['formatted_snapshot']['snapshot_id'] == 'test-snapshot'
            assert result['formatted_snapshot']['cluster_id'] == 'test-cluster'
            assert result['formatted_snapshot']['status'] == 'deleting'
            assert 'DBClusterSnapshot' in result

    @pytest.mark.asyncio
    async def test_delete_snapshot_without_confirmation(self, mock_rds_context_allowed):
        """Test snapshot deletion without confirmation token."""
        result = await delete_db_cluster_snapshot(db_cluster_snapshot_identifier='test-snapshot')

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result

    @pytest.mark.asyncio
    async def test_delete_snapshot_readonly_mode(self, mock_rds_context_readonly):
        """Test snapshot deletion in readonly mode."""
        result = await delete_db_cluster_snapshot(db_cluster_snapshot_identifier='test-snapshot')

        assert isinstance(result, dict) and 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_delete_snapshot_invalid_token(self, mock_rds_context_allowed):
        """Test snapshot deletion with invalid confirmation token."""
        with patch(
            'awslabs.rds_management_mcp_server.common.decorators.require_confirmation._pending_operations'
        ) as mock_pending:
            mock_pending.get.return_value = None  # Token not found

            result = await delete_db_cluster_snapshot(
                db_cluster_snapshot_identifier='test-snapshot', confirmation_token='invalid-token'
            )

            assert 'error' in result
            assert 'Invalid' in result['error'] or 'expired' in result['error']

    @pytest.mark.asyncio
    async def test_delete_snapshot_general_exception(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""
        with patch(
            'awslabs.rds_management_mcp_server.common.decorators.require_confirmation._pending_operations'
        ) as mock_pending:
            mock_pending.get.return_value = (
                'DeleteDBClusterSnapshot',
                {'db_cluster_snapshot_identifier': 'test-snapshot'},
                time.time() + 300,
            )

            async def async_error(func, **kwargs):
                raise Exception('General error')

            mock_asyncio_thread.side_effect = async_error

            result = await delete_db_cluster_snapshot(
                db_cluster_snapshot_identifier='test-snapshot', confirmation_token='test-token'
            )

            assert isinstance(result, dict) and 'error' in result
            assert 'General error' in result['error']

    @pytest.mark.asyncio
    async def test_delete_snapshot_result_formatting(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test the formatting of the snapshot information in the result."""
        with patch(
            'awslabs.rds_management_mcp_server.common.decorators.require_confirmation._pending_operations'
        ) as mock_pending:
            mock_pending.get.return_value = (
                'DeleteDBClusterSnapshot',
                {'db_cluster_snapshot_identifier': 'test-snapshot'},
                time.time() + 300,
            )

            mock_rds_client.delete_db_cluster_snapshot.return_value = {
                'DBClusterSnapshot': {
                    'DBClusterSnapshotIdentifier': 'test-snapshot',
                    'DBClusterIdentifier': 'test-cluster',
                    'Status': 'deleting',
                    'SnapshotType': 'manual',
                    'Engine': 'aurora-mysql',
                    'EngineVersion': '5.7.mysql_aurora.2.10.2',
                    'SnapshotCreateTime': '2023-01-01T12:00:00Z',
                    'AllocatedStorage': 100,
                    'Port': 3306,
                    'AvailabilityZones': ['us-west-2a', 'us-west-2b'],
                    'StorageEncrypted': True,
                }
            }

            async def async_return(func, **kwargs):
                return func(**kwargs)

            mock_asyncio_thread.side_effect = async_return

            result = await delete_db_cluster_snapshot(
                db_cluster_snapshot_identifier='test-snapshot', confirmation_token='test-token'
            )

            formatted_snapshot = result['formatted_snapshot']
            assert formatted_snapshot['snapshot_id'] == 'test-snapshot'
            assert formatted_snapshot['cluster_id'] == 'test-cluster'
            assert formatted_snapshot['status'] == 'deleting'
            assert formatted_snapshot['deletion_time'] == '2023-01-01T12:00:00Z'

            # Check that the full response is included
            assert result['DBClusterSnapshot']['SnapshotType'] == 'manual'
            assert result['DBClusterSnapshot']['AllocatedStorage'] == 100
            assert result['DBClusterSnapshot']['StorageEncrypted'] is True
