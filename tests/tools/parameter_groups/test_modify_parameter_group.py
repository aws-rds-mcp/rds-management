"""Tests for modify_parameter_group tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.parameter_groups.modify_parameter_group import (
    modify_db_cluster_parameter_group,
    modify_db_instance_parameter_group,
)


class TestModifyParameterGroups:
    """Test cases for modify parameter group functions."""

    @pytest.mark.asyncio
    async def test_modify_cluster_parameter_group_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful modification of cluster parameter group."""
        mock_rds_client.modify_db_cluster_parameter_group.return_value = {
            'DBClusterParameterGroupName': 'test-cluster-parameter-group'
        }
        mock_rds_client.describe_db_cluster_parameters.return_value = {'Parameters': []}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-parameter-group',
            parameters=[
                {
                    'ParameterName': 'max_connections',
                    'ParameterValue': '200',
                    'ApplyMethod': 'immediate',
                }
            ],
        )

        assert (
            result['message']
            == 'Successfully modified parameters in DB cluster parameter group test-cluster-parameter-group'
        )
        assert 'parameters_modified' in result
        assert 'formatted_parameters' in result

    @pytest.mark.asyncio
    async def test_modify_instance_parameter_group_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful modification of instance parameter group."""
        mock_rds_client.modify_db_parameter_group.return_value = {
            'DBParameterGroupName': 'test-parameter-group'
        }
        mock_rds_client.describe_db_parameters.return_value = {'Parameters': []}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group',
            parameters=[
                {
                    'ParameterName': 'innodb_buffer_pool_size',
                    'ParameterValue': '268435456',
                    'ApplyMethod': 'pending-reboot',
                },
                {
                    'ParameterName': 'max_connections',
                    'ParameterValue': '150',
                    'ApplyMethod': 'immediate',
                },
            ],
        )

        assert (
            result['message']
            == 'Successfully modified parameters in DB instance parameter group test-parameter-group'
        )
        assert 'parameters_modified' in result
        assert 'formatted_parameters' in result

    @pytest.mark.asyncio
    async def test_modify_cluster_parameter_group_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster parameter group modification in readonly mode."""
        result = await modify_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-parameter-group',
            parameters=[{'ParameterName': 'max_connections', 'ParameterValue': '200'}],
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_modify_instance_parameter_group_readonly_mode(self, mock_rds_context_readonly):
        """Test instance parameter group modification in readonly mode."""
        result = await modify_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group',
            parameters=[{'ParameterName': 'max_connections', 'ParameterValue': '150'}],
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_modify_parameter_group_empty_parameters(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test modification with empty parameters list."""
        mock_rds_client.modify_db_parameter_group.return_value = {
            'DBParameterGroupName': 'test-parameter-group'
        }
        mock_rds_client.describe_db_parameters.return_value = {'Parameters': []}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group', parameters=[]
        )

        # The function should succeed even with empty parameters
        assert (
            result['message']
            == 'Successfully modified parameters in DB instance parameter group test-parameter-group'
        )

    @pytest.mark.asyncio
    async def test_modify_parameter_group_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test error handling in parameter group modification."""
        mock_rds_client.modify_db_parameter_group.side_effect = Exception('Test error')

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance_parameter_group(
            db_parameter_group_name='test-parameter-group',
            parameters=[{'ParameterName': 'max_connections', 'ParameterValue': '150'}],
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'Test error' in result['error_message']
