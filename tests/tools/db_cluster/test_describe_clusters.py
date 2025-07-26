"""Tests for describe_clusters tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_cluster.describe_clusters import (
    describe_db_clusters,
)


class TestDescribeClusters:
    """Test cases for describe_db_clusters function."""

    @pytest.mark.asyncio
    async def test_describe_clusters_all_success(
        self, mock_rds_client, mock_asyncio_thread, sample_db_cluster
    ):
        """Test successful description of all clusters."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [sample_db_cluster]}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_clusters()

        assert result['message'] == 'Successfully retrieved information for 1 DB clusters'
        assert len(result['formatted_clusters']) == 1
        assert result['formatted_clusters'][0]['cluster_id'] == 'test-db-cluster'
        assert result['formatted_clusters'][0]['status'] == sample_db_cluster['Status']
        assert result['formatted_clusters'][0]['engine'] == sample_db_cluster['Engine']
        assert (
            result['formatted_clusters'][0]['engine_version'] == sample_db_cluster['EngineVersion']
        )
        assert 'DBClusters' in result

    @pytest.mark.asyncio
    async def test_describe_clusters_specific_cluster(
        self, mock_rds_client, mock_asyncio_thread, sample_db_cluster
    ):
        """Test description of a specific cluster."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [sample_db_cluster]}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_clusters(db_cluster_identifier='test-cluster')

        assert (
            result['message'] == 'Successfully retrieved information for DB cluster test-cluster'
        )
        assert len(result['formatted_clusters']) == 1
        assert (
            result['formatted_clusters'][0]['cluster_id']
            == sample_db_cluster['DBClusterIdentifier']
        )
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterIdentifier'] == 'test-cluster'

    @pytest.mark.asyncio
    async def test_describe_clusters_with_filters(
        self, mock_rds_client, mock_asyncio_thread, sample_db_cluster
    ):
        """Test description of clusters with filters."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [sample_db_cluster]}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_clusters(
            filters=[{'Name': 'engine', 'Values': ['aurora-mysql']}], max_records=50
        )

        assert result['message'] == 'Successfully retrieved information for 1 DB clusters'
        assert len(result['formatted_clusters']) == 1
        assert result['formatted_clusters'][0]['engine'] == 'aurora-mysql'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['Filters'] == [{'Name': 'engine', 'Values': ['aurora-mysql']}]
        assert call_args['MaxRecords'] == 50

    @pytest.mark.asyncio
    async def test_describe_clusters_empty_result(self, mock_rds_client, mock_asyncio_thread):
        """Test description when no clusters are found."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': []}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_clusters()

        assert result['message'] == 'Successfully retrieved information for 0 DB clusters'
        assert len(result['formatted_clusters']) == 0
        assert 'DBClusters' in result

    @pytest.mark.asyncio
    async def test_describe_clusters_with_pagination(
        self, mock_rds_client, mock_asyncio_thread, sample_db_cluster
    ):
        """Test description with pagination."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [sample_db_cluster],
            'Marker': 'next-page-marker',
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_clusters(marker='start-marker', max_records=10)

        assert result['message'] == 'Successfully retrieved information for 1 DB clusters'
        assert len(result['formatted_clusters']) == 1
        assert 'Marker' in result
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['Marker'] == 'start-marker'
        assert call_args['MaxRecords'] == 10

    @pytest.mark.asyncio
    async def test_describe_clusters_invalid_identifier(
        self, mock_rds_client, mock_asyncio_thread
    ):
        """Test error handling when an invalid cluster identifier is provided."""
        from botocore.exceptions import ClientError

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'DBClusterNotFoundFault',
                        'Message': 'DBCluster not-a-cluster not found',
                    }
                },
                'DescribeDBClusters',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await describe_db_clusters(db_cluster_identifier='not-a-cluster')

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'DBClusterNotFoundFault'

    @pytest.mark.asyncio
    async def test_describe_clusters_general_exception(self, mock_rds_client, mock_asyncio_thread):
        """Test error handling for general exceptions."""

        async def async_error(func, **kwargs):
            raise Exception('Unexpected error occurred')

        mock_asyncio_thread.side_effect = async_error

        result = await describe_db_clusters()

        assert isinstance(result, dict) and 'error' in result
        assert 'Unexpected error occurred' in result['error']

    @pytest.mark.asyncio
    async def test_describe_clusters_formatting(
        self, mock_rds_client, mock_asyncio_thread, sample_db_cluster
    ):
        """Test the formatting of the cluster information in the result."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [sample_db_cluster]}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await describe_db_clusters()

        assert result['message'] == 'Successfully retrieved information for 1 DB clusters'
        formatted_cluster = result['formatted_clusters'][0]
        assert formatted_cluster['cluster_id'] == sample_db_cluster['DBClusterIdentifier']
        assert formatted_cluster['status'] == sample_db_cluster['Status']
        assert formatted_cluster['engine'] == sample_db_cluster['Engine']
        assert formatted_cluster['engine_version'] == sample_db_cluster['EngineVersion']
        assert formatted_cluster['endpoint'] == sample_db_cluster['Endpoint']
        assert formatted_cluster['reader_endpoint'] == sample_db_cluster['ReaderEndpoint']
        assert formatted_cluster['multi_az'] == sample_db_cluster['MultiAZ']
        assert formatted_cluster['backup_retention'] == sample_db_cluster['BackupRetentionPeriod']
        assert (
            formatted_cluster['preferred_backup_window']
            == sample_db_cluster['PreferredBackupWindow']
        )
        assert (
            formatted_cluster['preferred_maintenance_window']
            == sample_db_cluster['PreferredMaintenanceWindow']
        )
        assert 'members' in formatted_cluster
        assert 'vpc_security_groups' in formatted_cluster
        assert 'tags' in formatted_cluster
        assert 'DBClusters' in result

    @pytest.mark.asyncio
    async def test_describe_clusters_invalid_filter(self, mock_rds_client, mock_asyncio_thread):
        """Test error handling with invalid filter parameters."""
        from botocore.exceptions import ClientError

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidParameterValue',
                        'Message': 'Invalid filter key: invalid-key',
                    }
                },
                'DescribeDBClusters',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await describe_db_clusters(
            filters=[{'Name': 'invalid-key', 'Values': ['some-value']}]
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'InvalidParameterValue'
