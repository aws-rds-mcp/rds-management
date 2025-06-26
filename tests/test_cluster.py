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

"""Tests for RDS Management MCP Server cluster module."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
import boto3
from botocore.exceptions import ClientError
from awslabs.rds_management_mcp_server import cluster
from awslabs.rds_management_mcp_server.constants import (
    ERROR_READONLY_MODE,
    ERROR_INVALID_PARAMS,
    CONFIRM_DELETE_CLUSTER,
    CONFIRM_STOP_CLUSTER,
    CONFIRM_FAILOVER,
)


@pytest.mark.asyncio
class TestCreateDBCluster:
    """Tests for create_db_cluster function."""

    async def test_create_db_cluster_readonly_mode(self, context, mock_rds_client):
        """Test create_db_cluster in read-only mode."""
        result = await cluster.create_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=True,
            db_cluster_identifier="test-cluster",
            engine="aurora-mysql",
            master_username="admin",
            manage_master_user_password=True,
        )
        
        # read-only mode response
        assert "read-only mode" in str(result)
        # RDS client was not called
        mock_rds_client.create_db_cluster.assert_not_called()

    async def test_create_db_cluster_validation_error(self, context, mock_rds_client):
        """Test create_db_cluster with validation error."""
        # invalid cluster identifier
        with patch('awslabs.rds_management_mcp_server.utils.validate_db_identifier') as mock_validate:
            mock_validate.return_value = (False, "Invalid identifier")
            
            result = await cluster.create_db_cluster(
                ctx=context,
                rds_client=mock_rds_client,
                readonly=False,
                db_cluster_identifier="invalid-id!",
                engine="aurora-mysql",
                master_username="admin",
            )
            
            # error response
            assert "Invalid parameters" in str(result)
            # RDS client was not called
            mock_rds_client.create_db_cluster.assert_not_called()

    async def test_create_db_cluster_success(self, context, mock_rds_client, sample_db_cluster):
        """Test create_db_cluster success case."""
        mock_rds_client.create_db_cluster.return_value = {"DBCluster": sample_db_cluster}
        
        with patch('awslabs.rds_management_mcp_server.utils.validate_db_identifier') as mock_validate:
            mock_validate.return_value = (True, "")
            
            with patch('awslabs.rds_management_mcp_server.utils.add_mcp_tags') as mock_add_tags:
                result = await cluster.create_db_cluster(
                    ctx=context,
                    rds_client=mock_rds_client,
                    readonly=False,
                    db_cluster_identifier="test-cluster",
                    engine="aurora-mysql",
                    master_username="admin",
                    manage_master_user_password=True,
                    database_name="testdb",
                )

                assert "created" in result["message"]
                assert "DBCluster" in result

                mock_rds_client.create_db_cluster.assert_called_once()
                call_kwargs = mock_rds_client.create_db_cluster.call_args.kwargs
                assert call_kwargs["DBClusterIdentifier"] == "test-cluster"
                assert call_kwargs["Engine"] == "aurora-mysql"
                assert call_kwargs["MasterUsername"] == "admin"
                assert call_kwargs["DatabaseName"] == "testdb"
                assert call_kwargs["ManageMasterUserPassword"] is True

    async def test_create_db_cluster_aws_error(self, context, mock_rds_client):
        """Test create_db_cluster with AWS error."""
        error_response = {'Error': {'Code': 'DBClusterAlreadyExistsFault', 
                                    'Message': 'DB cluster already exists'}}
        mock_rds_client.create_db_cluster.side_effect = ClientError(error_response, 'CreateDBCluster')
        
        with patch('awslabs.rds_management_mcp_server.utils.validate_db_identifier') as mock_validate:
            mock_validate.return_value = (True, "")
            
            with patch('awslabs.rds_management_mcp_server.utils.handle_aws_error', 
                      new_callable=AsyncMock) as mock_handle_error:
                mock_handle_error.return_value = {
                    "message": "DB cluster already exists", 
                    "isError": True,
                    "errorCode": "DBClusterAlreadyExistsFault"
                }
                
                result = await cluster.create_db_cluster(
                    ctx=context,
                    rds_client=mock_rds_client,
                    readonly=False,
                    db_cluster_identifier="test-cluster",
                    engine="aurora-mysql",
                    master_username="admin",
                )

                assert "DB cluster already exists" in str(result)
                
@pytest.mark.asyncio
class TestModifyDBCluster:
    """Tests for modify_db_cluster function."""

    async def test_modify_db_cluster_readonly_mode(self, context, mock_rds_client):
        """Test modify_db_cluster in read-only mode."""
        result = await cluster.modify_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=True,
            db_cluster_identifier="test-cluster",
            apply_immediately=True,
        )

        assert "read-only mode" in str(result)
        mock_rds_client.modify_db_cluster.assert_not_called()

    async def test_modify_db_cluster_success(self, context, mock_rds_client, sample_db_cluster):
        """Test modify_db_cluster success case."""
        mock_rds_client.modify_db_cluster.return_value = {"DBCluster": sample_db_cluster}
        mock_rds_client.describe_db_clusters.return_value = {"DBClusters": [sample_db_cluster]}
        
        with patch('awslabs.rds_management_mcp_server.utils.validate_db_identifier') as mock_validate:
            mock_validate.return_value = (True, "")
            
            result = await cluster.modify_db_cluster(
                ctx=context,
                rds_client=mock_rds_client,
                readonly=False,
                db_cluster_identifier="test-cluster",
                apply_immediately=True,
                backup_retention_period=14,
                engine_version="5.7.mysql_aurora.2.11.0",
                allow_major_version_upgrade=True,
            )
            
            assert "modified" in result["message"]
            assert "DBCluster" in result
            mock_rds_client.modify_db_cluster.assert_called_once()
            call_kwargs = mock_rds_client.modify_db_cluster.call_args.kwargs
            assert call_kwargs["DBClusterIdentifier"] == "test-cluster"
            assert call_kwargs["ApplyImmediately"] is True
            assert call_kwargs["BackupRetentionPeriod"] == 14
            assert call_kwargs["EngineVersion"] == "5.7.mysql_aurora.2.11.0"
            assert call_kwargs["AllowMajorVersionUpgrade"] is True


@pytest.mark.asyncio
class TestDeleteDBCluster:
    """Tests for delete_db_cluster function."""

    async def test_delete_db_cluster_readonly_mode(self, context, mock_rds_client):
        """Test delete_db_cluster in read-only mode."""
        result = await cluster.delete_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=True,
            db_cluster_identifier="test-cluster",
            skip_final_snapshot=True,
        )
        assert "read-only mode" in str(result)
        mock_rds_client.delete_db_cluster.assert_not_called()

    async def test_delete_db_cluster_requires_confirmation(self, context, mock_rds_client):
        """Test delete_db_cluster requires confirmation."""
        result = await cluster.delete_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            skip_final_snapshot=True,
            confirmation_token=None,
        )
        
        # confirmation required response
        assert "requires_confirmation" in result
        assert result["requires_confirmation"] is True
        assert "confirmation_token" in result
        # RDS client was not called
        mock_rds_client.delete_db_cluster.assert_not_called()

    async def test_delete_db_cluster_invalid_confirmation(self, context, mock_rds_client):
        """Test delete_db_cluster with invalid confirmation token."""
        # invalid confirmation token
        with patch('awslabs.rds_management_mcp_server.utils.get_pending_operation') as mock_get_operation:
            mock_get_operation.return_value = "valid-token"
            
            result = await cluster.delete_db_cluster(
                ctx=context,
                rds_client=mock_rds_client,
                readonly=False,
                db_cluster_identifier="test-cluster",
                skip_final_snapshot=True,
                confirmation_token="invalid-token",
            )
            
            assert "Invalid or expired confirmation token" in str(result)
            mock_rds_client.delete_db_cluster.assert_not_called()

    async def test_delete_db_cluster_success(self, context, mock_rds_client, sample_db_cluster):
        """Test delete_db_cluster success case."""
        mock_rds_client.delete_db_cluster.return_value = {"DBCluster": sample_db_cluster}
        mock_rds_client.describe_db_clusters.return_value = {"DBClusters": [sample_db_cluster]}
        
        first_result = await cluster.delete_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            skip_final_snapshot=True,
        )
        
        # token from the first result
        token = first_result.get("confirmation_token", "")
        
        with patch('awslabs.rds_management_mcp_server.utils.remove_pending_operation') as mock_remove_operation:
            result = await cluster.delete_db_cluster(
                ctx=context,
                rds_client=mock_rds_client,
                readonly=False,
                db_cluster_identifier="test-cluster",
                skip_final_snapshot=True,
                confirmation_token=token,
            )
            
            assert "DBCluster" in result and result["DBCluster"] == sample_db_cluster
            assert "DBCluster" in result
            mock_rds_client.delete_db_cluster.assert_called_once()
            call_kwargs = mock_rds_client.delete_db_cluster.call_args.kwargs
            assert call_kwargs["DBClusterIdentifier"] == "test-cluster"
            assert call_kwargs["SkipFinalSnapshot"] is True


@pytest.mark.asyncio
class TestStatusDBCluster:
    """Tests for status_db_cluster function."""

    async def test_status_db_cluster_readonly_mode(self, context, mock_rds_client):
        """Test status_db_cluster in read-only mode."""
        result = await cluster.status_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=True,
            db_cluster_identifier="test-cluster",
            action="start",
        )
        
        assert "read-only mode" in str(result)
        mock_rds_client.start_db_cluster.assert_not_called()
        mock_rds_client.stop_db_cluster.assert_not_called()
        mock_rds_client.reboot_db_cluster.assert_not_called()

    async def test_status_db_cluster_invalid_action(self, context, mock_rds_client):
        """Test status_db_cluster with invalid action."""
        result = await cluster.status_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            action="invalid-action",
        )
        
        assert "Invalid action" in str(result)

    async def test_status_db_cluster_requires_confirmation(self, context, mock_rds_client):
        """Test status_db_cluster requires confirmation."""
        actions = ["start", "stop", "reboot"]
        
        for action in actions:
            result = await cluster.status_db_cluster(
                ctx=context,
                rds_client=mock_rds_client,
                readonly=False,
                db_cluster_identifier="test-cluster",
                action=action,
                confirmation=None,
            )
            
            assert "requires_confirmation" in result
            assert result["requires_confirmation"] is True

    async def test_status_db_cluster_start_success(self, context, mock_rds_client, sample_db_cluster):
        """Test status_db_cluster start action success."""
        mock_rds_client.start_db_cluster.return_value = {"DBCluster": sample_db_cluster}
        
        result = await cluster.status_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            action="start",
            confirmation="CONFIRM_START",
        )
        
        assert "started" in result["message"]
        assert "DBCluster" in result

        mock_rds_client.start_db_cluster.assert_called_once_with(
            DBClusterIdentifier="test-cluster"
        )

    async def test_status_db_cluster_stop_success(self, context, mock_rds_client, sample_db_cluster):
        """Test status_db_cluster stop action success."""
        mock_rds_client.stop_db_cluster.return_value = {"DBCluster": sample_db_cluster}
        
        result = await cluster.status_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            action="stop",
            confirmation="CONFIRM_STOP",
        )

        assert "DBCluster" in result
        assert "DBCluster" in result
        
        mock_rds_client.stop_db_cluster.assert_called_once_with(
            DBClusterIdentifier="test-cluster"
        )

    async def test_status_db_cluster_reboot_success(self, context, mock_rds_client, sample_db_cluster):
        """Test status_db_cluster reboot action success."""
        mock_rds_client.reboot_db_cluster.return_value = {"DBCluster": sample_db_cluster}
    
        result = await cluster.status_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            action="reboot",
            confirmation="CONFIRM_REBOOT",
        )
        
        assert "rebooted" in result["message"]
        assert "DBCluster" in result
        
        mock_rds_client.reboot_db_cluster.assert_called_once_with(
            DBClusterIdentifier="test-cluster"
        )


@pytest.mark.asyncio
class TestFailoverDBCluster:
    """Tests for failover_db_cluster function."""

    async def test_failover_db_cluster_readonly_mode(self, context, mock_rds_client):
        """Test failover_db_cluster in read-only mode."""
        result = await cluster.failover_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=True,
            db_cluster_identifier="test-cluster",
        )
        
        assert "read-only mode" in str(result)
        mock_rds_client.failover_db_cluster.assert_not_called()

    async def test_failover_db_cluster_requires_confirmation(self, context, mock_rds_client):
        """Test failover_db_cluster requires confirmation."""
        result = await cluster.failover_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            confirmation=None,
        )
        
        assert "requires_confirmation" in result
        assert result["requires_confirmation"] is True
        
        mock_rds_client.failover_db_cluster.assert_not_called()

    async def test_failover_db_cluster_success(self, context, mock_rds_client, sample_db_cluster):
        """Test failover_db_cluster success case."""
        mock_rds_client.failover_db_cluster.return_value = {"DBCluster": sample_db_cluster}
        
        result = await cluster.failover_db_cluster(
            ctx=context,
            rds_client=mock_rds_client,
            readonly=False,
            db_cluster_identifier="test-cluster",
            target_db_instance_identifier="test-instance-2",
            confirmation="CONFIRM_FAILOVER",
        )
        
        assert "DBCluster" in result
        assert "DBCluster" in result
        
        mock_rds_client.failover_db_cluster.assert_called_once_with(
            DBClusterIdentifier="test-cluster",
            TargetDBInstanceIdentifier="test-instance-2",
        )


@pytest.mark.asyncio
class TestDescribeDBClusters:
    """Tests for describe_db_clusters function."""

    async def test_describe_db_clusters_no_params(self, context, mock_rds_client, sample_db_cluster):
        """Test describe_db_clusters with no parameters."""
        mock_rds_client.describe_db_clusters.return_value = {
            "DBClusters": [sample_db_cluster],
            "Marker": None
        }
        
        result = await cluster.describe_db_clusters(
            ctx=context,
            rds_client=mock_rds_client,
        )
        
        assert "DBClusters" in result
        assert len(result["DBClusters"]) == 1
        assert "formatted_clusters" in result
        assert len(result["formatted_clusters"]) == 1
        
        mock_rds_client.describe_db_clusters.assert_called_once_with()

    async def test_describe_db_clusters_with_identifier(self, context, mock_rds_client, sample_db_cluster):
        """Test describe_db_clusters with cluster identifier."""
        mock_rds_client.describe_db_clusters.return_value = {
            "DBClusters": [sample_db_cluster],
            "Marker": None
        }
        
        result = await cluster.describe_db_clusters(
            ctx=context,
            rds_client=mock_rds_client,
            db_cluster_identifier="test-db-cluster",
        )
        
        assert "DBClusters" in result
        assert len(result["DBClusters"]) == 1
        assert "formatted_clusters" in result
        assert len(result["formatted_clusters"]) == 1
        
        mock_rds_client.describe_db_clusters.assert_called_once_with(
            DBClusterIdentifier="test-db-cluster"
        )

    async def test_describe_db_clusters_with_filters(self, context, mock_rds_client, sample_db_cluster):
        """Test describe_db_clusters with filters."""
        mock_rds_client.describe_db_clusters.return_value = {
            "DBClusters": [sample_db_cluster],
            "Marker": None
        }
        
        filters = [
            {"Name": "engine", "Values": ["aurora-mysql"]},
            {"Name": "status", "Values": ["available"]}
        ]
        
        result = await cluster.describe_db_clusters(
            ctx=context,
            rds_client=mock_rds_client,
            filters=filters,
        )
        
        assert "DBClusters" in result
        assert len(result["DBClusters"]) == 1
        
        mock_rds_client.describe_db_clusters.assert_called_once_with(
            Filters=filters
        )

    async def test_describe_db_clusters_with_pagination(self, context, mock_rds_client, sample_db_cluster):
        """Test describe_db_clusters with pagination parameters."""
        mock_rds_client.describe_db_clusters.return_value = {
            "DBClusters": [sample_db_cluster],
            "Marker": "next-page-token"
        }
        
        result = await cluster.describe_db_clusters(
            ctx=context,
            rds_client=mock_rds_client,
            marker="current-page-token",
            max_records=20,
        )
        
        assert "DBClusters" in result
        assert len(result["DBClusters"]) == 1
        assert "Marker" in result
        assert result["Marker"] == "next-page-token"
        
        mock_rds_client.describe_db_clusters.assert_called_once_with(
            Marker="current-page-token",
            MaxRecords=20
        )
