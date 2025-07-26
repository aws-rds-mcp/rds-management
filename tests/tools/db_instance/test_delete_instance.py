"""Tests for delete_instance tool."""

import pytest
import time
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    _pending_operations,
)
from awslabs.rds_management_mcp_server.tools.db_instance.delete_instance import delete_db_instance


class TestDeleteInstance:
    """Test cases for delete_db_instance function."""

    def setup_method(self):
        """Clear pending operations before each test."""
        _pending_operations.clear()

    @pytest.mark.asyncio
    async def test_delete_instance_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test successful instance deletion."""
        mock_rds_client.delete_db_instance.return_value = {'DBInstance': sample_db_instance}

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'DeleteDBInstance',
            {'db_instance_identifier': 'test-instance'},
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await delete_db_instance(
            db_instance_identifier='test-instance', confirmation_token='test-token'
        )

        assert result['message'] == 'Successfully deleted DB instance test-instance'
        assert result['formatted_instance']['instance_id'] == 'test-db-instance'
        assert 'DBInstance' in result

    @pytest.mark.asyncio
    async def test_delete_instance_readonly_mode(self, mock_rds_context_readonly):
        """Test instance deletion in readonly mode."""
        result = await delete_db_instance(
            db_instance_identifier='test-instance', confirmation_token='test-token'
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_delete_instance_requires_confirmation(self, mock_rds_context_allowed):
        """Test instance deletion without confirmation token."""
        result = await delete_db_instance(db_instance_identifier='test-instance')

        assert 'requires_confirmation' in result
        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result

    @pytest.mark.asyncio
    async def test_delete_instance_with_final_snapshot(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test instance deletion with final snapshot."""
        mock_rds_client.delete_db_instance.return_value = {'DBInstance': sample_db_instance}

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'DeleteDBInstance',
            {
                'db_instance_identifier': 'test-instance',
                'skip_final_snapshot': False,
                'final_db_snapshot_identifier': 'final-snapshot',
            },
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await delete_db_instance(
            db_instance_identifier='test-instance',
            skip_final_snapshot=False,
            final_db_snapshot_identifier='final-snapshot',
            confirmation_token='test-token',
        )

        assert result['message'] == 'Successfully deleted DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['SkipFinalSnapshot'] is False
        assert call_args['FinalDBSnapshotIdentifier'] == 'final-snapshot'

    @pytest.mark.asyncio
    async def test_delete_instance_skip_final_snapshot(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test instance deletion skipping final snapshot."""
        mock_rds_client.delete_db_instance.return_value = {'DBInstance': sample_db_instance}

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'DeleteDBInstance',
            {'db_instance_identifier': 'test-instance', 'skip_final_snapshot': True},
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await delete_db_instance(
            db_instance_identifier='test-instance',
            skip_final_snapshot=True,
            confirmation_token='test-token',
        )

        assert result['message'] == 'Successfully deleted DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['SkipFinalSnapshot'] is True
        assert 'FinalDBSnapshotIdentifier' not in call_args
