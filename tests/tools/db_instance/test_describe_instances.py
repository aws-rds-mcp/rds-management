"""Tests for describe_instances tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_instance.describe_instances import (
    describe_db_instances,
)


class TestDescribeInstances:
    """Test cases for describe_db_instances function."""

    @pytest.mark.asyncio
    async def test_describe_instances_all_success(
        self, mock_rds_client, mock_asyncio_thread, sample_db_instance
    ):
        """Test successful description of all instances."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': [sample_db_instance]}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_instances()

        assert result['message'] == 'Successfully retrieved information for 1 DB instances'
        assert len(result['formatted_instances']) == 1
        assert result['formatted_instances'][0]['instance_id'] == 'test-db-instance'
        assert 'DBInstances' in result

    @pytest.mark.asyncio
    async def test_describe_instances_specific_instance(
        self, mock_rds_client, mock_asyncio_thread, sample_db_instance
    ):
        """Test description of a specific instance."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': [sample_db_instance]}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_instances(db_instance_identifier='test-instance')

        assert (
            result['message'] == 'Successfully retrieved information for DB instance test-instance'
        )
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBInstanceIdentifier'] == 'test-instance'

    @pytest.mark.asyncio
    async def test_describe_instances_with_filters(
        self, mock_rds_client, mock_asyncio_thread, sample_db_instance
    ):
        """Test description of instances with filters."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': [sample_db_instance]}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_instances(
            filters=[{'Name': 'engine', 'Values': ['mysql']}], max_records=50
        )

        assert result['message'] == 'Successfully retrieved information for 1 DB instances'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['Filters'] == [{'Name': 'engine', 'Values': ['mysql']}]
        assert call_args['MaxRecords'] == 50

    @pytest.mark.asyncio
    async def test_describe_instances_empty_result(self, mock_rds_client, mock_asyncio_thread):
        """Test description when no instances are found."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': []}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_instances()

        assert result['message'] == 'Successfully retrieved information for 0 DB instances'
        assert len(result['formatted_instances']) == 0

    @pytest.mark.asyncio
    async def test_describe_instances_with_pagination(
        self, mock_rds_client, mock_asyncio_thread, sample_db_instance
    ):
        """Test description with pagination."""
        mock_rds_client.describe_db_instances.return_value = {
            'DBInstances': [sample_db_instance],
            'Marker': 'next-page-marker',
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_instances(marker='start-marker', max_records=10)

        assert result['message'] == 'Successfully retrieved information for 1 DB instances'
        assert 'Marker' in result  # AWS returns 'Marker' not 'marker'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['Marker'] == 'start-marker'
        assert call_args['MaxRecords'] == 10
