"""Tests for reset_parameter_group tool."""

import pytest
import time
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    _pending_operations,
)
from awslabs.rds_management_mcp_server.tools.parameter_groups.reset_parameter_group import (
    reset_db_cluster_parameter_group,
    reset_db_instance_parameter_group,
)


class TestResetParameterGroups:
    """Test cases for reset parameter group functions."""

    @pytest.mark.asyncio
    async def test_reset_cluster_parameter_group_all_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful reset of all cluster parameter group parameters."""
        mock_rds_client.reset_db_cluster_parameter_group.return_value = {
            'DBClusterParameterGroupName': 'test-cluster-parameter-group'
        }

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ResetDBClusterParameterGroup',
            {
                'db_cluster_parameter_group_name': 'test-cluster-parameter-group',
                'reset_all_parameters': True,
            },
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await reset_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-parameter-group',
            reset_all_parameters=True,
            confirmation_token='test-token',
        )

        assert (
            result['message']
            == 'Successfully reset all parameters in DB cluster parameter group test-cluster-parameter-group'
        )
        assert result['parameters_reset'] == 0  # No parameters in mock response

    @pytest.mark.asyncio
    async def test_reset_instance_parameter_group_all_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful reset of all instance parameter group parameters."""
        mock_rds_client.reset_db_parameter_group.return_value = {
            'DBParameterGroupName': 'test-parameter-group'
        }

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ResetDBInstanceParameterGroup',
            {'db_parameter_group_name': 'test-parameter-group', 'reset_all_parameters': True},
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await reset_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group',
            reset_all_parameters=True,
            confirmation_token='test-token',
        )

        assert (
            result['message']
            == 'Successfully reset all parameters in DB instance parameter group test-parameter-group'
        )
        assert result['parameters_reset'] == 0  # No parameters in mock response

    @pytest.mark.asyncio
    async def test_reset_cluster_parameter_group_specific_parameters(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test reset of specific cluster parameter group parameters."""
        mock_rds_client.reset_db_cluster_parameter_group.return_value = {
            'DBClusterParameterGroupName': 'test-cluster-parameter-group'
        }

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ResetDBClusterParameterGroup',
            {
                'db_cluster_parameter_group_name': 'test-cluster-parameter-group',
                'reset_all_parameters': False,
                'parameters': [
                    {'ParameterName': 'max_connections', 'ApplyMethod': 'immediate'},
                    {'ParameterName': 'character_set_database', 'ApplyMethod': 'pending-reboot'},
                ],
            },
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await reset_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-parameter-group',
            reset_all_parameters=False,
            parameters=[
                {'ParameterName': 'max_connections', 'ApplyMethod': 'immediate'},
                {'ParameterName': 'character_set_database', 'ApplyMethod': 'pending-reboot'},
            ],
            confirmation_token='test-token',
        )

        assert (
            result['message']
            == 'Successfully reset specified parameters in DB cluster parameter group test-cluster-parameter-group'
        )
        assert result['parameters_reset'] == 0  # No parameters in mock response

    @pytest.mark.asyncio
    async def test_reset_parameter_group_requires_confirmation(self, mock_rds_context_allowed):
        """Test reset without confirmation token."""
        result = await reset_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group', reset_all_parameters=True
        )

        assert 'requires_confirmation' in result
        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result

    @pytest.mark.asyncio
    async def test_reset_cluster_parameter_group_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster parameter group reset in readonly mode."""
        result = await reset_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-parameter-group',
            reset_all_parameters=True,
            confirmation_token='test-token',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_reset_parameter_group_no_parameters(
        self, mock_rds_client, mock_rds_context_allowed
    ):
        """Test reset with no parameters specified."""
        # First call should ask for confirmation
        result = await reset_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group',
            reset_all_parameters=False,
            parameters=None,
        )

        assert 'requires_confirmation' in result
        assert result['requires_confirmation'] is True

        # Now call with the confirmation token to get the validation error
        confirmation_token = result['confirmation_token']
        result = await reset_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group',
            reset_all_parameters=False,
            parameters=None,
            confirmation_token=confirmation_token,
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'must specify' in result['error']

    @pytest.mark.asyncio
    async def test_reset_parameter_group_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test error handling in parameter group reset."""
        mock_rds_client.reset_db_parameter_group.side_effect = Exception('Test error')

        # Set up pending operation for confirmation
        _pending_operations['test-token'] = (
            'ResetDBInstanceParameterGroup',
            {'db_parameter_group_name': 'test-parameter-group', 'reset_all_parameters': True},
            time.time() + 300,  # 5 minutes from now
        )

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await reset_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group',
            reset_all_parameters=True,
            confirmation_token='test-token',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'Test error' in result['error_message']
