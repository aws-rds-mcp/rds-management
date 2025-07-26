# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for describe_cluster_detail resource."""

import pytest
from awslabs.rds_management_mcp_server.resources.db_cluster.describe_cluster_detail import (
    describe_cluster_detail,
)
from botocore.exceptions import ClientError


class TestDescribeClusterDetail:
    """Test cases for describe_cluster_detail resource."""

    @pytest.mark.asyncio
    async def test_describe_cluster_detail_success(self, mock_rds_client, sample_db_cluster):
        """Test successful cluster detail retrieval."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [sample_db_cluster]}

        cluster_id = 'test-cluster'
        result = await describe_cluster_detail(cluster_id)

        assert result.cluster_id == 'test-db-cluster'
        assert result.status == 'available'
        assert result.engine == 'aurora-mysql'
        assert result.endpoint == 'test-db-cluster.cluster-abc123.us-east-1.rds.amazonaws.com'
        assert (
            result.reader_endpoint
            == 'test-db-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com'
        )
        assert result.multi_az is True
        assert result.backup_retention == 7
        assert result.preferred_backup_window == '07:00-09:00'
        assert result.preferred_maintenance_window == 'sun:04:00-sun:05:00'
        assert len(result.members) == 2
        assert len(result.vpc_security_groups) == 1
        assert result.resource_uri == 'aws-rds://db-cluster/test-db-cluster'

        mock_rds_client.describe_db_clusters.assert_called_once_with(
            DBClusterIdentifier='test-cluster'
        )

    @pytest.mark.asyncio
    async def test_describe_cluster_detail_not_found(self, mock_rds_client):
        """Test cluster detail retrieval with cluster not found."""
        mock_rds_client.describe_db_clusters.side_effect = ClientError(
            {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'Cluster not found'}},
            'DescribeDBClusters',
        )

        cluster_id = 'nonexistent-cluster'

        result = await describe_cluster_detail(cluster_id)
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_code'] == 'DBClusterNotFoundFault'

    @pytest.mark.asyncio
    async def test_describe_cluster_detail_empty_cluster_id(self, mock_rds_client):
        """Test cluster detail retrieval with empty cluster ID."""
        cluster_id = ''

        result = await describe_cluster_detail(cluster_id)
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_type'] == 'ValueError'
        assert 'Cluster identifier cannot be empty' in result['error_message']

    @pytest.mark.asyncio
    async def test_describe_cluster_detail_empty_response(self, mock_rds_client):
        """Test cluster detail retrieval with empty response."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': []}

        cluster_id = 'empty-cluster'

        result = await describe_cluster_detail(cluster_id)
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_type'] == 'ValueError'
        assert 'not found' in result['error_message']

    @pytest.mark.asyncio
    async def test_describe_cluster_detail_minimal_cluster(self, mock_rds_client):
        """Test cluster detail retrieval with minimal cluster data."""
        minimal_cluster = {
            'DBClusterIdentifier': 'minimal-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'MasterUsername': 'admin',
            'Port': 3306,
            'AvailabilityZones': ['us-east-1a'],
        }

        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [minimal_cluster]}

        cluster_id = 'minimal-cluster'
        result = await describe_cluster_detail(cluster_id)

        assert result.cluster_id == 'minimal-cluster'
        assert result.status == 'available'
        assert result.engine == 'aurora-mysql'
        # Optional fields should have default values
        assert result.endpoint is None
        assert result.reader_endpoint is None
        assert result.multi_az is False
        assert result.resource_uri == 'aws-rds://db-cluster/minimal-cluster'
        assert result.backup_retention == 0
        assert result.members == []
        assert result.vpc_security_groups == []

    @pytest.mark.asyncio
    async def test_describe_cluster_detail_with_tags(self, mock_rds_client):
        """Test cluster detail retrieval with tags."""
        cluster_with_tags = {
            'DBClusterIdentifier': 'tagged-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'MasterUsername': 'admin',
            'Port': 3306,
            'AvailabilityZones': ['us-east-1a'],
            'TagList': [
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Team', 'Value': 'DataEngineering'},
            ],
        }

        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [cluster_with_tags]}

        cluster_id = 'tagged-cluster'
        result = await describe_cluster_detail(cluster_id)

        assert result.cluster_id == 'tagged-cluster'
        assert len(result.tags) == 2
        assert result.tags['Environment'] == 'Production'
        assert result.tags['Team'] == 'DataEngineering'

    @pytest.mark.asyncio
    async def test_describe_cluster_detail_exception_handling(self, mock_rds_client):
        """Test cluster detail retrieval with general exception."""
        mock_rds_client.describe_db_clusters.side_effect = Exception('General error')

        cluster_id = 'test-cluster'

        result = await describe_cluster_detail(cluster_id)
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_type'] == 'Exception'
        assert 'General error' in result['error_message']

    @pytest.mark.asyncio
    async def test_cluster_model_attributes(self, mock_rds_client, sample_db_cluster):
        """Test that ClusterModel attributes are accessible."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': [sample_db_cluster]}

        cluster_id = 'test-cluster'
        result = await describe_cluster_detail(cluster_id)

        assert result.cluster_id == 'test-db-cluster'
        assert result.status == 'available'
        assert result.engine == 'aurora-mysql'

        # Test accessing nested attributes
        assert result.members[0].instance_id == 'test-db-instance-1'
        assert result.vpc_security_groups[0]['id'] == 'sg-12345678'
