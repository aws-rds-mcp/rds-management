"""Tests for restore_snapshot tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_cluster.restore_snapshot import (
    restore_db_cluster_from_snapshot,
    restore_db_cluster_to_point_in_time,
)


class TestRestoreSnapshot:
    """Test cases for restore snapshot functions."""

    @pytest.mark.asyncio
    async def test_restore_from_snapshot_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_cluster
    ):
        """Test successful cluster restoration from snapshot."""
        mock_rds_client.restore_db_cluster_from_snapshot.return_value = {
            'DBCluster': sample_db_cluster
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await restore_db_cluster_from_snapshot(
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql',
        )

        assert result['message'] == 'Successfully restored DB cluster restored-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-db-cluster'
        assert result['formatted_cluster']['status'] == sample_db_cluster['Status']
        assert result['formatted_cluster']['engine'] == sample_db_cluster['Engine']
        assert 'DBCluster' in result

    @pytest.mark.asyncio
    async def test_restore_from_snapshot_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster restoration in readonly mode."""
        result = await restore_db_cluster_from_snapshot(
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_restore_from_snapshot_with_optional_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_cluster
    ):
        """Test cluster restoration with optional parameters."""
        mock_rds_client.restore_db_cluster_from_snapshot.return_value = {
            'DBCluster': sample_db_cluster
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await restore_db_cluster_from_snapshot(
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql',
            port=3306,
            availability_zones=['us-east-1a', 'us-east-1b'],
            vpc_security_group_ids=['sg-123456'],
        )

        assert result['message'] == 'Successfully restored DB cluster restored-cluster'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['Port'] == 3306
        assert call_args['AvailabilityZones'] == ['us-east-1a', 'us-east-1b']
        assert call_args['VpcSecurityGroupIds'] == ['sg-123456']

    @pytest.mark.asyncio
    async def test_restore_to_point_in_time_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_cluster
    ):
        """Test successful cluster restoration to point in time."""
        mock_rds_client.restore_db_cluster_to_point_in_time.return_value = {
            'DBCluster': sample_db_cluster
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await restore_db_cluster_to_point_in_time(
            db_cluster_identifier='restored-cluster',
            source_db_cluster_identifier='source-cluster',
            restore_to_time='2023-01-01T12:00:00Z',
        )

        assert (
            result['message']
            == 'Successfully restored DB cluster restored-cluster to point in time'
        )
        assert result['formatted_cluster']['cluster_id'] == 'test-db-cluster'
        assert result['formatted_cluster']['status'] == sample_db_cluster['Status']
        assert result['formatted_cluster']['engine'] == sample_db_cluster['Engine']
        assert 'DBCluster' in result

    @pytest.mark.asyncio
    async def test_restore_to_point_in_time_readonly_mode(self, mock_rds_context_readonly):
        """Test point in time restoration in readonly mode."""
        result = await restore_db_cluster_to_point_in_time(
            db_cluster_identifier='restored-cluster',
            source_db_cluster_identifier='source-cluster',
            restore_to_time='2023-01-01T12:00:00Z',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_restore_to_point_in_time_use_latest(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_cluster
    ):
        """Test point in time restoration using latest restorable time."""
        mock_rds_client.restore_db_cluster_to_point_in_time.return_value = {
            'DBCluster': sample_db_cluster
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await restore_db_cluster_to_point_in_time(
            db_cluster_identifier='restored-cluster',
            source_db_cluster_identifier='source-cluster',
            use_latest_restorable_time=True,
        )

        assert (
            result['message']
            == 'Successfully restored DB cluster restored-cluster to point in time'
        )
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['UseLatestRestorableTime'] is True

    @pytest.mark.asyncio
    async def test_restore_from_non_existent_snapshot(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test restoring from a non-existent snapshot."""
        from botocore.exceptions import ClientError

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'DBSnapshotNotFound', 'Message': 'Snapshot not found'}},
                'RestoreDBClusterFromSnapshot',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await restore_db_cluster_from_snapshot(
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='non-existent-snapshot',
            engine='aurora-mysql',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['error_code'] == 'DBSnapshotNotFound'
        assert 'Snapshot not found' in result['error_message']

    @pytest.mark.asyncio
    async def test_restore_to_invalid_point_in_time(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test restoring to a point in time that's out of range."""
        from botocore.exceptions import ClientError

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidRestoreTime',
                        'Message': 'Restore time is out of range',
                    }
                },
                'RestoreDBClusterToPointInTime',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await restore_db_cluster_to_point_in_time(
            db_cluster_identifier='restored-cluster',
            source_db_cluster_identifier='source-cluster',
            restore_to_time='2020-01-01T00:00:00Z',  # Assuming this is an invalid time
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['error_code'] == 'InvalidRestoreTime'
        assert 'Restore time is out of range' in result['error_message']

    @pytest.mark.asyncio
    async def test_restore_with_invalid_engine_version(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test restoring with an invalid engine version."""
        from botocore.exceptions import ClientError

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'InvalidParameterValue', 'Message': 'Invalid engine version'}},
                'RestoreDBClusterFromSnapshot',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await restore_db_cluster_from_snapshot(
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql',
            engine_version='invalid-version',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['error_code'] == 'InvalidParameterValue'
        assert 'Invalid engine version' in result['error_message']

    @pytest.mark.asyncio
    async def test_restore_result_formatting(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test the formatting of the restored cluster information in the result."""
        mock_rds_client.restore_db_cluster_from_snapshot.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'restored-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'Port': 3306,
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123456'}],
                'AvailabilityZones': ['us-west-2a', 'us-west-2b', 'us-west-2c'],
                'MultiAZ': True,
                'Endpoint': 'restored-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com',
                'ReaderEndpoint': 'restored-cluster.cluster-ro-123456789012.us-west-2.rds.amazonaws.com',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await restore_db_cluster_from_snapshot(
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql',
        )

        assert result['message'] == 'Successfully restored DB cluster restored-cluster'
        formatted_cluster = result['formatted_cluster']
        assert formatted_cluster['cluster_id'] == 'restored-cluster'
        assert formatted_cluster['status'] == 'creating'
        assert formatted_cluster['engine'] == 'aurora-mysql'
        assert formatted_cluster['engine_version'] == '5.7.mysql_aurora.2.10.2'
        # The format_cluster_info function doesn't include port
        assert len(formatted_cluster['vpc_security_groups']) == 1
        assert formatted_cluster['vpc_security_groups'][0]['id'] == 'sg-123456'
        assert formatted_cluster['multi_az'] is True
        assert (
            formatted_cluster['endpoint']
            == 'restored-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com'
        )
        assert (
            formatted_cluster['reader_endpoint']
            == 'restored-cluster.cluster-ro-123456789012.us-west-2.rds.amazonaws.com'
        )
        assert 'DBCluster' in result

    @pytest.mark.asyncio
    async def test_restore_general_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling during restoration."""

        async def async_error(func, **kwargs):
            raise Exception('Unexpected error occurred')

        mock_asyncio_thread.side_effect = async_error

        result = await restore_db_cluster_from_snapshot(
            db_cluster_identifier='restored-cluster',
            snapshot_identifier='test-snapshot',
            engine='aurora-mysql',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'Unexpected error occurred' in result['error_message']
        assert result['operation'] == 'restore_db_cluster_from_snapshot'
