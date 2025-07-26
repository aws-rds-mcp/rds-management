"""Tests for describe_parameters resource."""

import pytest
from awslabs.rds_management_mcp_server.resources.parameter_groups.describe_parameters import (
    describe_cluster_parameters,
    describe_instance_parameters,
)


class TestDescribeParameters:
    """Test cases for describe parameter functions."""

    @pytest.mark.asyncio
    async def test_describe_cluster_parameters_success(self, mock_rds_client, mock_asyncio_thread):
        """Test successful description of cluster parameters."""
        mock_rds_client.describe_db_cluster_parameters.return_value = {
            'Parameters': [
                {
                    'ParameterName': 'character_set_database',
                    'ParameterValue': 'utf8mb4',
                    'Description': 'The default character set for the database',
                    'Source': 'engine-default',
                    'ApplyType': 'static',
                    'DataType': 'string',
                    'AllowedValues': 'utf8,utf8mb4',
                    'IsModifiable': True,
                    'ApplyMethod': 'pending-reboot',
                },
                {
                    'ParameterName': 'max_connections',
                    'ParameterValue': '100',
                    'Description': 'Maximum number of connections',
                    'Source': 'user',
                    'ApplyType': 'dynamic',
                    'DataType': 'integer',
                    'IsModifiable': True,
                    'ApplyMethod': 'immediate',
                },
            ],
            'Marker': None,
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_cluster_parameters('test-cluster-parameter-group')

        assert result.parameter_group_name == 'test-cluster-parameter-group'
        assert hasattr(result, 'parameters')
        assert result.count == 2
        assert len(result.parameters) == 2

        # Check the parameters by source
        engine_default_params = [p for p in result.parameters if p.source == 'engine-default']
        custom_params = [p for p in result.parameters if p.source == 'user']

        assert len(engine_default_params) == 1
        assert len(custom_params) == 1
        assert custom_params[0].name == 'max_connections'

    @pytest.mark.asyncio
    async def test_describe_instance_parameters_success(
        self, mock_rds_client, mock_asyncio_thread
    ):
        """Test successful description of instance parameters."""
        mock_rds_client.describe_db_parameters.return_value = {
            'Parameters': [
                {
                    'ParameterName': 'innodb_buffer_pool_size',
                    'ParameterValue': '134217728',
                    'Description': 'Size of the InnoDB buffer pool',
                    'Source': 'engine-default',
                    'ApplyType': 'static',
                    'DataType': 'integer',
                    'IsModifiable': True,
                    'ApplyMethod': 'pending-reboot',
                }
            ],
            'Marker': None,
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_instance_parameters('test-parameter-group')

        assert result.parameter_group_name == 'test-parameter-group'
        assert hasattr(result, 'parameters')
        assert result.count == 1
        assert len(result.parameters) == 1
        assert result.parameters[0].name == 'innodb_buffer_pool_size'
        assert result.parameters[0].source == 'engine-default'

    @pytest.mark.asyncio
    async def test_describe_cluster_parameters_empty(self, mock_rds_client, mock_asyncio_thread):
        """Test description when no parameters exist."""
        mock_rds_client.describe_db_cluster_parameters.return_value = {
            'Parameters': [],
            'Marker': None,
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_cluster_parameters('empty-parameter-group')

        assert result.parameter_group_name == 'empty-parameter-group'
        assert len(result.parameters) == 0
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_describe_cluster_parameters_error(self, mock_rds_client, mock_asyncio_thread):
        """Test error handling in describe cluster parameters."""
        mock_rds_client.describe_db_cluster_parameters.side_effect = Exception('Test error')

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_cluster_parameters('test-parameter-group')

        assert isinstance(result, dict) and 'error' in result
        assert 'Test error' in result['error']

    @pytest.mark.asyncio
    async def test_describe_parameters_with_pagination(self, mock_rds_client, mock_asyncio_thread):
        """Test parameter description with pagination."""
        # First call returns partial results with marker
        mock_rds_client.describe_db_parameters.side_effect = [
            {
                'Parameters': [
                    {
                        'ParameterName': 'param1',
                        'ParameterValue': 'value1',
                        'Source': 'engine-default',
                    }
                ],
                'Marker': 'next-page',
            },
            {
                'Parameters': [
                    {'ParameterName': 'param2', 'ParameterValue': 'value2', 'Source': 'user'}
                ],
                'Marker': None,
            },
        ]

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_instance_parameters('test-parameter-group')

        # Should have called twice due to pagination
        assert mock_asyncio_thread.call_count == 2
        assert result.count == 2
        assert len(result.parameters) == 2

        # Check we have one of each type
        engine_default_params = [p for p in result.parameters if p.source == 'engine-default']
        custom_params = [p for p in result.parameters if p.source == 'user']

        assert len(engine_default_params) == 1
        assert len(custom_params) == 1
