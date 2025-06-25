# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

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

"""Tests for RDS Management MCP Server resources module."""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from botocore.exceptions import ClientError
from awslabs.rds_management_mcp_server import resources
from awslabs.rds_management_mcp_server.constants import RESOURCE_PREFIX_CLUSTER


@pytest.mark.asyncio
class TestGetClusterListResource:
    """Tests for get_cluster_list_resource function."""

    async def test_get_cluster_list_resource_success(self, mock_rds_client, sample_db_cluster):
        """Test successful retrieval of cluster list."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [sample_db_cluster]
        }
        
        with patch('awslabs.rds_management_mcp_server.utils.format_cluster_info') as mock_format:
            mock_format.return_value = {
                'id': 'test-db-cluster',
                'engine': 'aurora-mysql',
                'status': 'available'
            }
            
            result = await resources.get_cluster_list_resource(mock_rds_client)
            
            assert isinstance(result, str)
            
            parsed_result = json.loads(result)
            assert 'clusters' in parsed_result
            assert isinstance(parsed_result['clusters'], list)
            assert len(parsed_result['clusters']) == 1
            assert 'count' in parsed_result
            assert parsed_result['count'] == 1
            assert 'resource_uri' in parsed_result
            assert parsed_result['resource_uri'] == RESOURCE_PREFIX_CLUSTER
            
            mock_rds_client.describe_db_clusters.assert_called_once_with()


    async def test_get_cluster_list_resource_empty(self, mock_rds_client):
        """Test retrieval of empty cluster list."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': []
        }
        
        result = await resources.get_cluster_list_resource(mock_rds_client)
        
        parsed_result = json.loads(result)
        assert 'clusters' in parsed_result
        assert isinstance(parsed_result['clusters'], list)
        assert len(parsed_result['clusters']) == 0
        assert 'count' in parsed_result
        assert parsed_result['count'] == 0


    async def test_get_cluster_list_resource_error(self, mock_rds_client):
        """Test error handling for cluster list retrieval."""
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_rds_client.describe_db_clusters.side_effect = ClientError(error_response, 'DescribeDBClusters')
        
        with patch('awslabs.rds_management_mcp_server.utils.handle_aws_error', 
                  new_callable=AsyncMock) as mock_handle_error:
            mock_handle_error.return_value = {
                "message": "Access denied", 
                "isError": True,
                "errorCode": "AccessDenied"
            }
            
            result = await resources.get_cluster_list_resource(mock_rds_client)
            
            parsed_result = json.loads(result)
            assert 'error' in parsed_result or 'message' in parsed_result
            

@pytest.mark.asyncio
class TestGetClusterDetailResource:
    """Tests for get_cluster_detail_resource function."""

    async def test_get_cluster_detail_resource_success(self, mock_rds_client, sample_db_cluster):
        """Test successful retrieval of cluster details."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [sample_db_cluster]
        }
        cluster_id = 'test-db-cluster'
        
        with patch('awslabs.rds_management_mcp_server.utils.format_cluster_info') as mock_format:
            formatted_cluster = {
                'id': 'test-db-cluster',
                'engine': 'aurora-mysql',
                'status': 'available'
            }
            mock_format.return_value = formatted_cluster
            
            result = await resources.get_cluster_detail_resource(cluster_id, mock_rds_client)
            
            assert isinstance(result, str)
            
            parsed_result = json.loads(result)
            
            assert 'resource_uri' in parsed_result
            assert parsed_result['resource_uri'] == f'{RESOURCE_PREFIX_CLUSTER}/{cluster_id}'
            
            cluster_id_present = False
            for key, value in parsed_result.items():
                if value == cluster_id and ('id' in key.lower() or 'identifier' in key.lower()):
                    cluster_id_present = True
                    break
            assert cluster_id_present, f"Cluster ID not found in response: {parsed_result}"
            
            mock_rds_client.describe_db_clusters.assert_called_once_with(
                DBClusterIdentifier=cluster_id
            )


    async def test_get_cluster_detail_resource_not_found(self, mock_rds_client):
        """Test retrieval of non-existent cluster."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': []
        }
        cluster_id = 'non-existent-cluster'
        
        result = await resources.get_cluster_detail_resource(cluster_id, mock_rds_client)
        
        parsed_result = json.loads(result)
        assert 'error' in parsed_result
        assert f'Cluster {cluster_id} not found' in parsed_result['error']


    async def test_get_cluster_detail_resource_error(self, mock_rds_client):
        """Test error handling for cluster detail retrieval."""
        cluster_id = 'test-cluster'
        error_response = {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'DB cluster not found'}}
        mock_rds_client.describe_db_clusters.side_effect = ClientError(error_response, 'DescribeDBClusters')
        
        with patch('awslabs.rds_management_mcp_server.utils.handle_aws_error', 
                  new_callable=AsyncMock) as mock_handle_error:
            mock_handle_error.return_value = {
                "message": "DB cluster not found", 
                "isError": True,
                "errorCode": "DBClusterNotFoundFault"
            }
            
            result = await resources.get_cluster_detail_resource(cluster_id, mock_rds_client)
            
            parsed_result = json.loads(result)
            assert 'error' in parsed_result or 'message' in parsed_result
            