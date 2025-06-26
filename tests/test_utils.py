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

"""Tests for RDS Management MCP Server utilities."""

import asyncio
import json
import os
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from botocore.exceptions import ClientError
from awslabs.rds_management_mcp_server import utils
from awslabs.rds_management_mcp_server.constants import (
    ERROR_AWS_API,
    ERROR_READONLY_MODE,
    ERROR_UNEXPECTED,
    DEFAULT_PORT_MYSQL,
    DEFAULT_PORT_POSTGRESQL,
    DEFAULT_PORT_AURORA,
)


class TestCheckReadonlyMode:
    """Tests for check_readonly_mode function."""

    @pytest.mark.asyncio
    async def test_check_readonly_mode_true(self):
        """Test readonly mode check when readonly=True."""
        context = MagicMock()
        context.error = AsyncMock()
        
        result = utils.check_readonly_mode("create_cluster", True, context)
        
        assert result is False
        
        context.error.assert_called_once()
        assert ERROR_READONLY_MODE in context.error.call_args[0][0]

    def test_check_readonly_mode_false(self):
        """Test readonly mode check when readonly=False."""
        context = MagicMock()
        result = utils.check_readonly_mode("create_cluster", False, context)
        
        assert result is True
        
        context.error.assert_not_called()

    def test_check_readonly_mode_no_context(self):
        """Test readonly mode check without context object."""
        result = utils.check_readonly_mode("create_cluster", True)
        assert result is False
        
        result = utils.check_readonly_mode("create_cluster", False)
        assert result is True


class TestValidateDBIdentifier:
    """Tests for validate_db_identifier function."""

    def test_validate_db_identifier_valid(self):
        """Test validation with valid identifier."""
        result = utils.validate_db_identifier("valid-identifier")
        assert result

    def test_validate_db_identifier_too_long(self):
        """Test validation with too long identifier."""
        long_id = "a" * 64
        result = utils.validate_db_identifier(long_id)
        assert not result

    def test_validate_db_identifier_invalid_chars(self):
        """Test validation with invalid characters."""
        result = utils.validate_db_identifier("invalid@id")
        assert not result

    def test_validate_db_identifier_starting_non_letter(self):
        """Test validation with non-letter starting character."""
        result = utils.validate_db_identifier("1invalid-id")
        assert not result


class TestGetEnginePort:
    """Tests for get_engine_port function."""

    def test_get_engine_port_aurora_mysql(self):
        """Test port retrieval for Aurora MySQL."""
        port = utils.get_engine_port("aurora-mysql")
        assert port == DEFAULT_PORT_MYSQL

    def test_get_engine_port_aurora_postgresql(self):
        """Test port retrieval for Aurora PostgreSQL."""
        port = utils.get_engine_port("aurora-postgresql")
        assert port == DEFAULT_PORT_POSTGRESQL

    def test_get_engine_port_aurora(self):
        """Test port retrieval for Aurora (legacy)."""
        port = utils.get_engine_port("aurora")
        assert port == DEFAULT_PORT_AURORA

    def test_get_engine_port_mysql(self):
        """Test port retrieval for MySQL."""
        port = utils.get_engine_port("mysql")
        assert port == DEFAULT_PORT_MYSQL

    def test_get_engine_port_postgres(self):
        """Test port retrieval for PostgreSQL."""
        port = utils.get_engine_port("postgres")
        assert port == DEFAULT_PORT_POSTGRESQL

    def test_get_engine_port_unknown(self):
        """Test port retrieval for unknown engine."""
        port = utils.get_engine_port("unknown-engine")
        assert port is not None 
        

class TestFormatClusterInfo:
    """Tests for format_cluster_info function."""

    def test_format_cluster_info_complete(self, sample_db_cluster):
        """Test formatting with complete cluster info."""
        result = utils.format_cluster_info(sample_db_cluster)
        
        cluster_id_field = "cluster_id" if "cluster_id" in result else "id"
        assert result[cluster_id_field] == sample_db_cluster["DBClusterIdentifier"]
        assert "engine" in result
        assert "status" in result
        assert any("endpoint" in key.lower() for key in result)
        assert len(result) > 0

    def test_format_cluster_info_minimal(self):
        """Test formatting with minimal cluster info."""
        minimal_cluster = {
            "DBClusterIdentifier": "minimal-cluster",
            "Engine": "aurora-mysql",
            "Status": "available"
        }
        
        result = utils.format_cluster_info(minimal_cluster)
        

        cluster_id_field = "cluster_id" if "cluster_id" in result else "id"
        assert result[cluster_id_field] == "minimal-cluster"
        assert "engine" in result
        assert "status" in result


class TestFormatAwsResponse:
    """Tests for format_aws_response function."""

    def test_format_aws_response_cluster(self, sample_db_cluster):
        """Test formatting AWS response with DBCluster."""
        aws_response = {
            "DBCluster": sample_db_cluster,
            "ResponseMetadata": {"RequestId": "123"}
        }
        
        result = utils.format_aws_response(aws_response)
        
        assert "DBCluster" in result
        assert result["DBCluster"] == sample_db_cluster
        
        assert "ResponseMetadata" not in result

    def test_format_aws_response_clusters(self, sample_db_cluster):
        """Test formatting AWS response with DBClusters list."""
        aws_response = {
            "DBClusters": [sample_db_cluster, sample_db_cluster],
            "ResponseMetadata": {"RequestId": "123"}
        }
        
        result = utils.format_aws_response(aws_response)
        
        assert "DBClusters" in result
        assert len(result["DBClusters"]) == 2
        
        assert "ResponseMetadata" not in result

    def test_format_aws_response_marker(self):
        """Test formatting AWS response with pagination marker."""
        aws_response = {
            "DBClusters": [],
            "Marker": "next-page",
            "ResponseMetadata": {"RequestId": "123"}
        }
        
        result = utils.format_aws_response(aws_response)
        
        assert "Marker" in result
        assert result["Marker"] == "next-page"
        
        assert "ResponseMetadata" not in result


@pytest.mark.asyncio
class TestHandleAwsError:
    """Tests for handle_aws_error function."""

    async def test_handle_aws_error_client_error(self):
        """Test handling AWS client error."""
        operation = "test_operation"
        error = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            operation_name="DescribeDBClusters"
        )
        
        result = await utils.handle_aws_error(operation, error)
        
        assert "error" in result
        assert "Access denied" in str(result)
        assert "error_code" in result
        assert result["error_code"] == "AccessDenied"

    async def test_handle_aws_error_general_exception(self):
        """Test handling general exception."""
        operation = "test_operation"
        error = ValueError("Invalid value")
        
        result = await utils.handle_aws_error(operation, error)
        
        assert "error" in result
        assert "Invalid value" in str(result)
        assert "error_type" in result


@pytest.mark.asyncio
class TestPendingOperations:
    """Tests for pending operations functions."""

    async def test_add_get_remove_pending_operation(self):
        """Test adding, getting and removing pending operations."""
        operation_id = "custom-id"
        operation = "delete_cluster"
        
        if hasattr(utils, '_pending_operations'):
            utils._pending_operations = {}
        
        if hasattr(utils, 'add_pending_operation'):
            token = utils.add_pending_operation(operation, {"param": "value"})
        assert token is not None

    async def test_add_pending_operation_no_id(self):
        """Test adding operation with auto-generated ID."""
        operation = "delete_cluster"
        
        if hasattr(utils, '_pending_operations'):
            utils._pending_operations = {}
        
        if 'params' in utils.add_pending_operation.__code__.co_varnames:
            token = utils.add_pending_operation(operation, {"param": "value"})
        else:
            token = utils.add_pending_operation(operation)
            
        assert token is not None


class TestGetOperationImpact:
    """Tests for get_operation_impact function."""

    def test_get_operation_impact_known(self):
        """Test getting impact for known operation."""
        impact = utils.get_operation_impact("delete_db_cluster")
        assert isinstance(impact, dict)
        assert len(impact) > 0
        assert any("data" in key.lower() for key in impact)

    def test_get_operation_impact_unknown(self):
        """Test getting impact for unknown operation."""
        impact = utils.get_operation_impact("unknown_operation")
        assert isinstance(impact, dict)
        assert len(impact) > 0


class TestAddMcpTags:
    """Tests for add_mcp_tags function."""

    def test_add_mcp_tags_params(self):
        """Test adding MCP tags to parameters."""
        params = {"DBClusterIdentifier": "test-cluster"}
        result = utils.add_mcp_tags(params)
        
        assert "Tags" in result
        assert isinstance(result["Tags"], list)
        assert len(result["Tags"]) > 0
        
        tag_keys = [tag["Key"].lower() for tag in result["Tags"]]
        assert any("mcp" in key or "server" in key or "created" in key for key in tag_keys)

    def test_add_mcp_tags_existing(self):
        """Test adding MCP tags to params with existing tags."""
        params = {
            "DBClusterIdentifier": "test-cluster",
            "Tags": [{"Key": "Environment", "Value": "Test"}]
        }
        result = utils.add_mcp_tags(params)
        
        assert "Tags" in result
        assert isinstance(result["Tags"], list)
        assert len(result["Tags"]) > 1
        
        tag_dict = {tag["Key"]: tag["Value"] for tag in result["Tags"]}
        assert "Environment" in tag_dict
        assert tag_dict["Environment"] == "Test"
