"""Tests for change_instance_status tool."""

import pytest
import time
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    _pending_operations,
)
from awslabs.rds_management_mcp_server.tools.db_instance.change_instance_status import (
    status_db_instance,
)


class TestChangeInstanceStatus:
    """Test cases for status_db_instance function."""

    def setup_method(self):
        """Clear pending operations before each test."""
        _pending_operations.clear()

    @pytest.mark.asyncio
    async def test_start_instance_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test successful instance start."""
        mock_rds_client.start_db_instance.return_value = {'DBInstance': sample_db_instance}

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'start'},
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await status_db_instance(
            db_instance_identifier='test-instance', action='start', confirmation_token='test-token'
        )

        assert result.get('message', '').startswith('Successfully')
        assert result['formatted_instance']['instance_id'] == 'test-db-instance'
        assert 'DBInstance' in result

    @pytest.mark.asyncio
    async def test_stop_instance_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test successful instance stop."""
        mock_rds_client.stop_db_instance.return_value = {'DBInstance': sample_db_instance}

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'stop'},
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await status_db_instance(
            db_instance_identifier='test-instance', action='stop', confirmation_token='test-token'
        )

        assert result.get('message', '').startswith('Successfully')
        assert result['formatted_instance']['instance_id'] == 'test-db-instance'
        assert 'DBInstance' in result

    @pytest.mark.asyncio
    async def test_reboot_instance_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test successful instance reboot."""
        mock_rds_client.reboot_db_instance.return_value = {'DBInstance': sample_db_instance}

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'reboot'},
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await status_db_instance(
            db_instance_identifier='test-instance',
            action='reboot',
            confirmation_token='test-token',
        )

        assert 'Successfully rebooted' in result['message']
        assert result['formatted_instance']['instance_id'] == 'test-db-instance'
        assert 'DBInstance' in result

    @pytest.mark.asyncio
    async def test_change_instance_status_readonly_mode(self, mock_rds_context_readonly):
        """Test instance status change in readonly mode."""
        result = await status_db_instance(
            db_instance_identifier='test-instance', action='start', confirmation_token='test-token'
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_change_instance_status_requires_confirmation(self, mock_rds_context_allowed):
        """Test instance status change without confirmation token."""
        result = await status_db_instance(db_instance_identifier='test-instance', action='start')

        assert 'requires_confirmation' in result
        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result

    @pytest.mark.asyncio
    async def test_reboot_instance_with_force_failover(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test instance reboot with force failover."""
        mock_rds_client.reboot_db_instance.return_value = {'DBInstance': sample_db_instance}

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ChangeDBInstanceStatus',
            {
                'db_instance_identifier': 'test-instance',
                'action': 'reboot',
                'force_failover': True,
            },
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await status_db_instance(
            db_instance_identifier='test-instance',
            action='reboot',
            force_failover=True,
            confirmation_token='test-token',
        )

        assert 'Successfully rebooted' in result['message']
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['ForceFailover'] is True

    @pytest.mark.asyncio
    async def test_change_instance_status_invalid_action(self, mock_rds_context_allowed):
        """Test instance status change with invalid action."""
        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'invalid'},
            time.time() + 300,  # 5 minutes from now
        )

        result = await status_db_instance(
            db_instance_identifier='test-instance',
            action='invalid',
            confirmation_token='test-token',
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'Invalid action' in result['error']
