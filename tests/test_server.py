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

"""Tests for RDS Management MCP Server main module."""

import asyncio
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from awslabs.rds_management_mcp_server import server
from awslabs.rds_management_mcp_server.constants import MCP_SERVER_VERSION


class TestServerConfiguration:
    """Tests for server configuration and startup."""

    def test_version_constant(self):
        """Test that the version constant is set."""
        assert MCP_SERVER_VERSION is not None
        assert isinstance(MCP_SERVER_VERSION, str)
        assert len(MCP_SERVER_VERSION) > 0

    def test_mcp_object_configuration(self):
        """Test that the MCP object is configured correctly."""
        
        assert server.mcp.name == 'awslabs.rds-management-mcp-server'
        
        assert MCP_SERVER_VERSION is not None
        
        assert server.mcp.instructions is not None
        assert len(server.mcp.instructions) > 0

    def test_get_rds_client(self):
        """Test the get_rds_client function."""
        with patch('boto3.client') as mock_boto_client:
            
            mock_client = MagicMock()
            mock_boto_client.return_value = mock_client
            
            # global region
            server._region = 'us-west-2'
            
            # global client
            server._rds_client = None
            
            client = server.get_rds_client()
            
            mock_boto_client.assert_called_once()
            call_args = mock_boto_client.call_args
            assert call_args[0][0] == 'rds'
            assert call_args[1]['config'].region_name == 'us-west-2'
            
            server.get_rds_client()
            assert mock_boto_client.call_count == 1
    
    @patch('awslabs.rds_management_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.rds-management-mcp-server', '--region', 'us-east-1'])
    def test_main_default_args(self, mock_run):
        """Test main function with default arguments."""
        server.main()
        mock_run.assert_called_once()
        assert server._readonly is True
        assert server._region == 'us-east-1'

    @patch('awslabs.rds_management_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.rds-management-mcp-server', '--region', 'us-west-2', '--readonly', 'false', '--sse'])
    def test_main_custom_args(self, mock_run):
        """Test main function with custom arguments."""
        server._readonly = True
        server._region = None
        
        server.main()
        
        mock_run.assert_called_once_with(transport='sse')
        assert server._readonly is False
        assert server._region == 'us-west-2'

    @patch('awslabs.rds_management_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.rds-management-mcp-server', '--region', 'us-east-1', '--profile', 'test-profile'])
    def test_main_with_profile(self, mock_run):
        """Test main function with AWS profile argument."""
        with patch.dict('os.environ', {}, clear=True):
            server.main()
            mock_run.assert_called_once()
            assert 'AWS_PROFILE' in os.environ
            assert os.environ['AWS_PROFILE'] == 'test-profile'


@pytest.mark.asyncio
class TestServerResources:
    """Tests for server resources."""

    async def test_list_clusters_resource(self, mock_rds_client):
        """Test list_clusters_resource."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'cluster-1',
                    'Engine': 'aurora-mysql',
                    'Status': 'available',
                }
            ]
        }
        
        with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
            result = await server.list_clusters_resource()
            
            assert isinstance(result, str)
            assert "cluster-1" in result
            assert "aurora-mysql" in result
            
            mock_rds_client.describe_db_clusters.assert_called_once()
    
    async def test_get_cluster_resource(self, mock_rds_client, sample_db_cluster):
        """Test get_cluster_resource."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [sample_db_cluster]
        }
        
        with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
            result = await server.get_cluster_resource('test-db-cluster')
            
            assert isinstance(result, str)
            assert "test-db-cluster" in result
            assert "aurora-mysql" in result
            
            mock_rds_client.describe_db_clusters.assert_called_once_with(
                DBClusterIdentifier='test-db-cluster'
            )
    
    async def test_get_cluster_resource_not_found(self, mock_rds_client):
        """Test get_cluster_resource when cluster is not found."""
        mock_rds_client.describe_db_clusters.return_value = {'DBClusters': []}
        
        with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
            result = await server.get_cluster_resource('non-existent-cluster')
            
            assert isinstance(result, str)
            assert "error" in result
            assert "not found" in result


@pytest.mark.asyncio
class TestCreateDBClusterTool:
    """Tests for create_db_cluster_tool."""

    async def test_create_db_cluster_readonly_mode(self, context, mock_rds_client):
        """Test create_db_cluster_tool in readonly mode."""
        # readonly flag
        server._readonly = True
        
        with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
            with patch('awslabs.rds_management_mcp_server.cluster.create_db_cluster', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = {"message": "Read-only mode simulation"}
                
                result = await server.create_db_cluster_tool(
                    ctx=context,
                    db_cluster_identifier="test-cluster",
                    engine="aurora-mysql",
                    master_username="admin",
                )
                
                assert "Read-only mode" in result["message"]
            
                assert mock_create.call_count == 1
                
                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["ctx"] == context
                assert call_kwargs["rds_client"] == mock_rds_client
                assert call_kwargs["readonly"] is True
                assert call_kwargs["db_cluster_identifier"] == "test-cluster"
                assert call_kwargs["engine"] == "aurora-mysql"
                assert call_kwargs["master_username"] == "admin"

    async def test_create_db_cluster_write_mode(self, context, mock_rds_client, sample_db_cluster):
        """Test create_db_cluster_tool in write mode."""
        server._readonly = False
        
        with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
            with patch('awslabs.rds_management_mcp_server.cluster.create_db_cluster', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = {"message": "Cluster created", "DBCluster": sample_db_cluster}
                
                result = await server.create_db_cluster_tool(
                    ctx=context,
                    db_cluster_identifier="test-cluster",
                    engine="aurora-mysql",
                    master_username="admin",
                    database_name="testdb",
                )
                
                assert "created" in result["message"]
                
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["readonly"] is False
                assert call_kwargs["db_cluster_identifier"] == "test-cluster"
                assert call_kwargs["database_name"] == "testdb"


@pytest.mark.asyncio
class TestModifyDBClusterTool:
    """Tests for modify_db_cluster_tool."""

    async def test_modify_db_cluster(self, context, mock_rds_client):
        """Test modify_db_cluster_tool."""
        with patch('awslabs.rds_management_mcp_server.cluster.modify_db_cluster', new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = {"message": "Cluster modified"}
            
            with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
                result = await server.modify_db_cluster_tool(
                    ctx=context,
                    db_cluster_identifier="test-cluster",
                    apply_immediately=True,
                    backup_retention_period=14,
                )
                assert "modified" in result["message"]
                
                mock_modify.assert_called_once()
                call_kwargs = mock_modify.call_args.kwargs
                assert call_kwargs["db_cluster_identifier"] == "test-cluster"
                assert call_kwargs["apply_immediately"] is True
                assert call_kwargs["backup_retention_period"] == 14


@pytest.mark.asyncio
class TestDeleteDBClusterTool:
    """Tests for delete_db_cluster_tool."""

    async def test_delete_db_cluster_confirmation_token(self, context, mock_rds_client):
        """Test delete_db_cluster_tool with confirmation token."""
        with patch('awslabs.rds_management_mcp_server.cluster.delete_db_cluster', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"message": "Cluster deleted"}
            
            with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
                result = await server.delete_db_cluster_tool(
                    ctx=context,
                    db_cluster_identifier="test-cluster",
                    skip_final_snapshot=True,
                    confirmation_token="test-token",
                )
                
                assert "deleted" in result["message"]
                
                mock_delete.assert_called_once()
                call_kwargs = mock_delete.call_args.kwargs
                assert call_kwargs["db_cluster_identifier"] == "test-cluster"
                assert call_kwargs["skip_final_snapshot"] is True
                assert call_kwargs["confirmation_token"] == "test-token"


@pytest.mark.asyncio
class TestStatusDBClusterTool:
    """Tests for status_db_cluster_tool."""

    async def test_status_db_cluster_start(self, context, mock_rds_client):
        """Test status_db_cluster_tool with start action."""
        with patch('awslabs.rds_management_mcp_server.cluster.status_db_cluster', new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {"message": "Cluster started"}
            
            with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
                result = await server.status_db_cluster_tool(
                    ctx=context,
                    db_cluster_identifier="test-cluster",
                    action="start",
                    confirmation="CONFIRM_START",
                )
                assert "started" in result["message"]
                
                mock_status.assert_called_once()
                call_kwargs = mock_status.call_args.kwargs
                assert call_kwargs["db_cluster_identifier"] == "test-cluster"
                assert call_kwargs["action"] == "start"


@pytest.mark.asyncio
class TestFailoverDBClusterTool:
    """Tests for failover_db_cluster_tool."""

    async def test_failover_db_cluster(self, context, mock_rds_client):
        """Test failover_db_cluster_tool."""
        with patch('awslabs.rds_management_mcp_server.cluster.failover_db_cluster', new_callable=AsyncMock) as mock_failover:
            mock_failover.return_value = {"message": "Cluster failed over"}
            
            with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
                result = await server.failover_db_cluster_tool(
                    ctx=context,
                    db_cluster_identifier="test-cluster",
                    target_db_instance_identifier="test-instance",
                    confirmation="CONFIRM_FAILOVER",
                )
                assert "failed over" in result["message"]
                
                mock_failover.assert_called_once()
                call_kwargs = mock_failover.call_args.kwargs
                assert call_kwargs["db_cluster_identifier"] == "test-cluster"
                assert call_kwargs["target_db_instance_identifier"] == "test-instance"


@pytest.mark.asyncio
class TestDescribeDBClustersTool:
    """Tests for describe_db_clusters_tool."""

    async def test_describe_db_clusters(self, context, mock_rds_client):
        """Test describe_db_clusters_tool."""
        with patch('awslabs.rds_management_mcp_server.cluster.describe_db_clusters', new_callable=AsyncMock) as mock_describe:
            mock_describe.return_value = {"DBClusters": []}
            
            with patch('awslabs.rds_management_mcp_server.server.get_rds_client', return_value=mock_rds_client):
                result = await server.describe_db_clusters_tool(
                    ctx=context,
                    db_cluster_identifier="test-cluster",
                )
                assert "DBClusters" in result
                
                mock_describe.assert_called_once()
                call_kwargs = mock_describe.call_args.kwargs
                assert call_kwargs["db_cluster_identifier"] == "test-cluster"
