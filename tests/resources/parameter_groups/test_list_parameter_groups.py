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

"""Tests for list_parameter_groups resource."""

import asyncio
import pytest
from awslabs.rds_management_mcp_server.resources.parameter_groups.list_parameter_groups import (
    ParameterGroupModel,
    list_cluster_parameter_groups,
    list_instance_parameter_groups,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_rds_client():
    """Mock RDS client with proper asyncio.to_thread and asyncio.wait_for support."""
    with patch(
        'awslabs.rds_management_mcp_server.common.connection.RDSConnectionManager.get_connection'
    ) as mock_get_connection:
        mock_client = MagicMock()
        mock_get_connection.return_value = mock_client

        # Mock both asyncio.to_thread and asyncio.wait_for to handle the async operations
        def mock_to_thread(func, *args, **kwargs):
            """Mock asyncio.to_thread to return the result of the function call."""
            return func(*args, **kwargs)

        async def mock_wait_for(coro, timeout):
            """Mock asyncio.wait_for to handle both coroutines and regular values."""
            # If it's already a coroutine, await it
            if asyncio.iscoroutine(coro):
                return await coro
            # If it's a regular value (from our mock), just return it
            return coro

        with patch('asyncio.to_thread', side_effect=mock_to_thread):
            with patch('asyncio.wait_for', side_effect=mock_wait_for):
                yield mock_client


class TestListClusterParameterGroups:
    """Test list_cluster_parameter_groups function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_rds_client):
        """Test successful cluster parameter groups list retrieval."""
        # Mock describe_db_cluster_parameter_groups with no pagination
        mock_rds_client.describe_db_cluster_parameter_groups.return_value = {
            'DBClusterParameterGroups': [
                {
                    'DBClusterParameterGroupName': 'test-cluster-param-group-1',
                    'DBParameterGroupFamily': 'aurora-mysql5.7',
                    'Description': 'Test cluster parameter group 1',
                    'DBClusterParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:cluster-pg:test-cluster-param-group-1',
                    'Tags': [{'Key': 'Environment', 'Value': 'Test'}],
                },
                {
                    'DBClusterParameterGroupName': 'test-cluster-param-group-2',
                    'DBParameterGroupFamily': 'aurora-postgresql13',
                    'Description': 'Test cluster parameter group 2',
                    'DBClusterParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:cluster-pg:test-cluster-param-group-2',
                    'Tags': [],
                },
            ]
        }

        # Mock describe_db_cluster_parameters for each group
        mock_rds_client.describe_db_cluster_parameters.return_value = {
            'Parameters': [
                {
                    'ParameterName': 'test_param',
                    'ParameterValue': 'test_value',
                    'Description': 'Test parameter',
                    'IsModifiable': True,
                    'AllowedValues': '0,1',
                    'Source': 'user',
                    'ApplyType': 'dynamic',
                    'DataType': 'boolean',
                }
            ]
        }

        result = await list_cluster_parameter_groups()

        assert result.count == 2
        assert len(result.parameter_groups) == 2
        assert result.parameter_groups[0].name == 'test-cluster-param-group-1'
        assert result.parameter_groups[0].family == 'aurora-mysql5.7'
        assert result.parameter_groups[0].type == 'cluster'
        assert result.parameter_groups[0].tags == {'Environment': 'Test'}
        assert result.parameter_groups[1].name == 'test-cluster-param-group-2'

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_rds_client):
        """Test handling of empty cluster parameter groups response."""
        mock_rds_client.describe_db_cluster_parameter_groups.return_value = {
            'DBClusterParameterGroups': []
        }

        result = await list_cluster_parameter_groups()

        assert result.count == 0
        assert len(result.parameter_groups) == 0

    @pytest.mark.asyncio
    async def test_pagination(self, mock_rds_client):
        """Test handling of paginated responses."""
        # First call returns with marker
        mock_rds_client.describe_db_cluster_parameter_groups.side_effect = [
            {
                'DBClusterParameterGroups': [
                    {
                        'DBClusterParameterGroupName': 'test-cluster-param-group-1',
                        'DBParameterGroupFamily': 'aurora-mysql5.7',
                        'Description': 'Test cluster parameter group 1',
                    }
                ],
                'Marker': 'next-page',
            },
            # Second call returns without marker
            {
                'DBClusterParameterGroups': [
                    {
                        'DBClusterParameterGroupName': 'test-cluster-param-group-2',
                        'DBParameterGroupFamily': 'aurora-postgresql13',
                        'Description': 'Test cluster parameter group 2',
                    }
                ]
            },
        ]

        mock_rds_client.describe_db_cluster_parameters.return_value = {'Parameters': []}

        result = await list_cluster_parameter_groups()

        assert result.count == 2
        assert len(result.parameter_groups) == 2
        # Verify pagination was used correctly
        assert mock_rds_client.describe_db_cluster_parameter_groups.call_count == 2
        # First call doesn't have Marker parameter
        mock_rds_client.describe_db_cluster_parameter_groups.assert_any_call()
        mock_rds_client.describe_db_cluster_parameter_groups.assert_any_call(Marker='next-page')

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_rds_client):
        """Test error handling when API call fails."""
        mock_rds_client.describe_db_cluster_parameter_groups.side_effect = ClientError(
            {'Error': {'Code': 'SomeError', 'Message': 'API call failed'}},
            'describe_db_cluster_parameter_groups',
        )

        # The @handle_exceptions decorator returns a dictionary with error information
        result = await list_cluster_parameter_groups()
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_code'] == 'SomeError'

    @pytest.mark.asyncio
    async def test_parameter_error_handling(self, mock_rds_client):
        """Test graceful handling when parameter description fails."""
        mock_rds_client.describe_db_cluster_parameter_groups.return_value = {
            'DBClusterParameterGroups': [
                {
                    'DBClusterParameterGroupName': 'test-cluster-param-group-1',
                    'DBParameterGroupFamily': 'aurora-mysql5.7',
                    'Description': 'Test cluster parameter group 1',
                }
            ]
        }

        # Make describe_db_cluster_parameters fail
        mock_rds_client.describe_db_cluster_parameters.side_effect = ClientError(
            {'Error': {'Code': 'SomeError', 'Message': 'Parameter API failed'}},
            'describe_db_cluster_parameters',
        )

        result = await list_cluster_parameter_groups()

        # Should still return the parameter group but with empty parameters
        assert result.count == 1
        assert len(result.parameter_groups) == 1
        assert result.parameter_groups[0].parameters == []

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_rds_client):
        """Test handling of timeout during parameter group listing."""
        # Make the describe_db_cluster_parameter_groups timeout
        mock_rds_client.describe_db_cluster_parameter_groups.side_effect = asyncio.TimeoutError()

        # The @handle_exceptions decorator returns a dictionary with error information
        result = await list_cluster_parameter_groups()
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_type'] == 'TimeoutError'


class TestListInstanceParameterGroups:
    """Test list_instance_parameter_groups function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_rds_client):
        """Test successful instance parameter groups list retrieval."""
        # Mock describe_db_parameter_groups with no pagination
        mock_rds_client.describe_db_parameter_groups.return_value = {
            'DBParameterGroups': [
                {
                    'DBParameterGroupName': 'test-instance-param-group-1',
                    'DBParameterGroupFamily': 'mysql8.0',
                    'Description': 'Test instance parameter group 1',
                    'DBParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:pg:test-instance-param-group-1',
                    'Tags': [{'Key': 'Owner', 'Value': 'Team'}],
                },
                {
                    'DBParameterGroupName': 'test-instance-param-group-2',
                    'DBParameterGroupFamily': 'postgres13',
                    'Description': 'Test instance parameter group 2',
                    'DBParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:pg:test-instance-param-group-2',
                    'Tags': [],
                },
            ]
        }

        # Mock describe_db_parameters for each group
        mock_rds_client.describe_db_parameters.return_value = {
            'Parameters': [
                {
                    'ParameterName': 'max_connections',
                    'ParameterValue': '100',
                    'Description': 'Maximum number of connections',
                    'IsModifiable': True,
                    'AllowedValues': '1-8388607',
                    'Source': 'user',
                    'ApplyType': 'static',
                    'DataType': 'integer',
                }
            ]
        }

        result = await list_instance_parameter_groups()

        assert result.count == 2
        assert len(result.parameter_groups) == 2
        assert result.parameter_groups[0].name == 'test-instance-param-group-1'
        assert result.parameter_groups[0].family == 'mysql8.0'
        assert result.parameter_groups[0].type == 'instance'
        assert result.parameter_groups[0].tags == {'Owner': 'Team'}
        assert result.parameter_groups[1].name == 'test-instance-param-group-2'

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_rds_client):
        """Test handling of empty instance parameter groups response."""
        mock_rds_client.describe_db_parameter_groups.return_value = {'DBParameterGroups': []}

        result = await list_instance_parameter_groups()

        assert result.count == 0
        assert len(result.parameter_groups) == 0

    @pytest.mark.asyncio
    async def test_pagination(self, mock_rds_client):
        """Test handling of paginated responses."""
        # First call returns with marker
        mock_rds_client.describe_db_parameter_groups.side_effect = [
            {
                'DBParameterGroups': [
                    {
                        'DBParameterGroupName': 'test-instance-param-group-1',
                        'DBParameterGroupFamily': 'mysql8.0',
                        'Description': 'Test instance parameter group 1',
                    }
                ],
                'Marker': 'next-page',
            },
            # Second call returns without marker
            {
                'DBParameterGroups': [
                    {
                        'DBParameterGroupName': 'test-instance-param-group-2',
                        'DBParameterGroupFamily': 'postgres13',
                        'Description': 'Test instance parameter group 2',
                    }
                ]
            },
        ]

        mock_rds_client.describe_db_parameters.return_value = {'Parameters': []}

        result = await list_instance_parameter_groups()

        assert result.count == 2
        assert len(result.parameter_groups) == 2
        # Verify pagination was used correctly
        assert mock_rds_client.describe_db_parameter_groups.call_count == 2
        # First call doesn't have Marker parameter
        mock_rds_client.describe_db_parameter_groups.assert_any_call()
        mock_rds_client.describe_db_parameter_groups.assert_any_call(Marker='next-page')

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_rds_client):
        """Test error handling when API call fails."""
        mock_rds_client.describe_db_parameter_groups.side_effect = ClientError(
            {'Error': {'Code': 'SomeError', 'Message': 'API call failed'}},
            'describe_db_parameter_groups',
        )

        # The @handle_exceptions decorator returns a dictionary with error information
        result = await list_instance_parameter_groups()
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_code'] == 'SomeError'

    @pytest.mark.asyncio
    async def test_parameter_error_handling(self, mock_rds_client):
        """Test graceful handling when parameter description fails."""
        mock_rds_client.describe_db_parameter_groups.return_value = {
            'DBParameterGroups': [
                {
                    'DBParameterGroupName': 'test-instance-param-group-1',
                    'DBParameterGroupFamily': 'mysql8.0',
                    'Description': 'Test instance parameter group 1',
                }
            ]
        }

        # Make describe_db_parameters fail
        mock_rds_client.describe_db_parameters.side_effect = ClientError(
            {'Error': {'Code': 'SomeError', 'Message': 'Parameter API failed'}},
            'describe_db_parameters',
        )

        result = await list_instance_parameter_groups()

        # Should still return the parameter group but with empty parameters
        assert result.count == 1
        assert len(result.parameter_groups) == 1
        assert result.parameter_groups[0].parameters == []

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_rds_client):
        """Test handling of timeout during parameter group listing."""
        # Make the describe_db_parameter_groups timeout
        mock_rds_client.describe_db_parameter_groups.side_effect = asyncio.TimeoutError()

        # The @handle_exceptions decorator returns a dictionary with error information
        result = await list_instance_parameter_groups()
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error_type'] == 'TimeoutError'


class TestParameterGroupModel:
    """Test ParameterGroupModel model."""

    def test_model_creation(self):
        """Test model creation with all fields."""
        param_group = ParameterGroupModel(
            name='test-param-group',
            description='Test parameter group',
            family='mysql8.0',
            type='instance',
            parameters=[],
            arn='arn:aws:rds:us-east-1:123456789012:pg:test-param-group',
            tags={'Environment': 'Production'},
            resource_uri='aws-rds://db-instance/parameter-groups/test-param-group',
        )

        assert param_group.name == 'test-param-group'
        assert param_group.description == 'Test parameter group'
        assert param_group.family == 'mysql8.0'
        assert param_group.type == 'instance'
        assert param_group.arn == 'arn:aws:rds:us-east-1:123456789012:pg:test-param-group'
        assert param_group.tags['Environment'] == 'Production'
        assert (
            param_group.resource_uri == 'aws-rds://db-instance/parameter-groups/test-param-group'
        )

    def test_model_creation_minimal(self):
        """Test model creation with minimal fields."""
        param_group = ParameterGroupModel(
            name='test-param-group',
            type='cluster',
            description='Minimal test parameter group',
            family='default',
            resource_uri='aws-rds://db-cluster/parameter-groups/test-param-group',
        )

        assert param_group.name == 'test-param-group'
        assert param_group.type == 'cluster'
        assert param_group.description == 'Minimal test parameter group'
        assert param_group.family == 'default'
        assert param_group.arn is None
        assert param_group.tags == {}
        assert param_group.parameters == []
