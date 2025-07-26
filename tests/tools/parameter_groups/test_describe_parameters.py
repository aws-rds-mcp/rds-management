"""Tests for describe_parameters tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.parameter_groups.describe_cluster_parameter_groups import (
    describe_db_cluster_parameter_groups,
)
from awslabs.rds_management_mcp_server.tools.parameter_groups.describe_instance_parameter_groups import (
    describe_db_instance_parameter_groups,
)


class TestDescribeParameterGroups:
    """Test cases for describe parameter group functions."""

    @pytest.mark.asyncio
    async def test_describe_cluster_parameter_group_success(
        self, mock_rds_client, sample_cluster_parameter_group
    ):
        """Test successful description of cluster parameter group."""
        mock_rds_client.describe_db_cluster_parameter_groups.return_value = {
            'DBClusterParameterGroups': [sample_cluster_parameter_group]
        }

        result = await describe_db_cluster_parameter_groups(
            db_cluster_parameter_group_name='test-cluster-parameter-group'
        )

        assert result['formatted_parameter_groups'][0]['name'] == 'test-cluster-parameter-group'
        assert result['formatted_parameter_groups'][0]['family'] == 'aurora-mysql5.7'
        assert (
            result['formatted_parameter_groups'][0]['description']
            == 'Test cluster parameter group'
        )

    @pytest.mark.asyncio
    async def test_describe_instance_parameter_group_success(
        self, mock_rds_client, sample_parameter_group
    ):
        """Test successful description of instance parameter group."""
        mock_rds_client.describe_db_parameter_groups.return_value = {
            'DBParameterGroups': [sample_parameter_group]
        }

        result = await describe_db_instance_parameter_groups(
            db_parameter_group_name='test-parameter-group'
        )

        assert result['formatted_parameter_groups'][0]['name'] == 'test-parameter-group'
        assert result['formatted_parameter_groups'][0]['family'] == 'mysql8.0'
        assert result['formatted_parameter_groups'][0]['description'] == 'Test parameter group'

    @pytest.mark.asyncio
    async def test_describe_cluster_parameter_group_not_found(self, mock_rds_client):
        """Test when cluster parameter group is not found."""
        mock_rds_client.describe_db_cluster_parameter_groups.return_value = {
            'DBClusterParameterGroups': []
        }

        result = await describe_db_cluster_parameter_groups(
            db_cluster_parameter_group_name='non-existent'
        )

        assert result['formatted_parameter_groups'] == []

    @pytest.mark.asyncio
    async def test_describe_instance_parameter_group_not_found(self, mock_rds_client):
        """Test when instance parameter group is not found."""
        mock_rds_client.describe_db_parameter_groups.return_value = {'DBParameterGroups': []}

        result = await describe_db_instance_parameter_groups(
            db_parameter_group_name='non-existent'
        )

        assert result['formatted_parameter_groups'] == []

    @pytest.mark.asyncio
    async def test_describe_cluster_parameter_group_error(self, mock_rds_client):
        """Test error handling in describe cluster parameter group."""
        mock_rds_client.describe_db_cluster_parameter_groups.side_effect = Exception('Test error')

        result = await describe_db_cluster_parameter_groups(
            db_cluster_parameter_group_name='test-group'
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'Test error' in result['error_message']

    @pytest.mark.asyncio
    async def test_describe_instance_parameter_group_error(self, mock_rds_client):
        """Test error handling in describe instance parameter group."""
        mock_rds_client.describe_db_parameter_groups.side_effect = Exception('Test error')

        result = await describe_db_instance_parameter_groups(db_parameter_group_name='test-group')

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'Test error' in result['error_message']
