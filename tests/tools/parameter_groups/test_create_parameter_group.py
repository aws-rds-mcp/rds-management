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

"""Tests for create_parameter_group tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.parameter_groups.create_parameter_group import (
    create_db_cluster_parameter_group,
    create_db_instance_parameter_group,
)
from botocore.exceptions import ClientError


class TestCreateDBClusterParameterGroup:
    """Test cases for create_db_cluster_parameter_group function."""

    @pytest.mark.asyncio
    async def test_create_cluster_parameter_group_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster parameter group creation."""
        mock_rds_client.create_db_cluster_parameter_group.return_value = {
            'DBClusterParameterGroup': {
                'DBClusterParameterGroupName': 'test-cluster-param-group',
                'DBParameterGroupFamily': 'aurora-mysql5.7',
                'Description': 'Test cluster parameter group',
                'DBClusterParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:cluster-pg:test-cluster-param-group',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-param-group',
            db_parameter_group_family='aurora-mysql5.7',
            description='Test cluster parameter group',
        )

        assert (
            result['message']
            == 'Successfully created DB cluster parameter group test-cluster-param-group'
        )
        assert result['formatted_parameter_group']['name'] == 'test-cluster-param-group'
        assert 'DBClusterParameterGroup' in result
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_cluster_parameter_group_with_tags(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster parameter group creation with tags."""
        mock_rds_client.create_db_cluster_parameter_group.return_value = {
            'DBClusterParameterGroup': {
                'DBClusterParameterGroupName': 'test-cluster-param-group',
                'DBParameterGroupFamily': 'aurora-mysql5.7',
                'Description': 'Test cluster parameter group with tags',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-param-group',
            db_parameter_group_family='aurora-mysql5.7',
            description='Test cluster parameter group with tags',
            tags=[{'Environment': 'Production'}, {'Team': 'DatabaseTeam'}],
        )

        assert (
            result['message']
            == 'Successfully created DB cluster parameter group test-cluster-param-group'
        )
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['Tags'] == [
            {'Key': 'Environment', 'Value': 'Production'},
            {'Key': 'Team', 'Value': 'DatabaseTeam'},
            {'Key': 'mcp_server_version', 'Value': '0.1.0'},
            {'Key': 'created_by', 'Value': 'rds-management-mcp-server'},
        ]

    @pytest.mark.asyncio
    async def test_create_cluster_parameter_group_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster parameter group creation in readonly mode."""
        result = await create_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-param-group',
            db_parameter_group_family='aurora-mysql5.7',
            description='Test cluster parameter group',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_create_cluster_parameter_group_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster parameter group creation with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'DBParameterGroupAlreadyExistsFault',
                        'Message': 'Parameter group already exists',
                    }
                },
                'CreateDBClusterParameterGroup',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster_parameter_group(
            db_cluster_parameter_group_name='existing-param-group',
            db_parameter_group_family='aurora-mysql5.7',
            description='Test cluster parameter group',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['error_code'] == 'DBParameterGroupAlreadyExistsFault'
        assert result['operation'] == 'create_db_cluster_parameter_group'

    @pytest.mark.asyncio
    async def test_create_cluster_parameter_group_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster_parameter_group(
            db_cluster_parameter_group_name='test-cluster-param-group',
            db_parameter_group_family='aurora-mysql5.7',
            description='Test cluster parameter group',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['operation'] == 'create_db_cluster_parameter_group'


class TestCreateDBInstanceParameterGroup:
    """Test cases for create_db_instance_parameter_group function."""

    @pytest.mark.asyncio
    async def test_create_instance_parameter_group_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful instance parameter group creation."""
        mock_rds_client.create_db_parameter_group.return_value = {
            'DBParameterGroup': {
                'DBParameterGroupName': 'test-instance-param-group',
                'DBParameterGroupFamily': 'mysql8.0',
                'Description': 'Test instance parameter group',
                'DBParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:pg:test-instance-param-group',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_instance_parameter_group(
            db_parameter_group_name='test-instance-param-group',
            db_parameter_group_family='mysql8.0',
            description='Test instance parameter group',
        )

        assert (
            result['message']
            == 'Successfully created DB instance parameter group test-instance-param-group'
        )
        assert result['formatted_parameter_group']['name'] == 'test-instance-param-group'
        assert 'DBParameterGroup' in result
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_parameter_group_with_tags(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test instance parameter group creation with tags."""
        mock_rds_client.create_db_parameter_group.return_value = {
            'DBParameterGroup': {
                'DBParameterGroupName': 'test-instance-param-group',
                'DBParameterGroupFamily': 'mysql8.0',
                'Description': 'Test instance parameter group with tags',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_instance_parameter_group(
            db_parameter_group_name='test-instance-param-group',
            db_parameter_group_family='mysql8.0',
            description='Test instance parameter group with tags',
            tags=[{'Environment': 'Development'}, {'Purpose': 'Testing'}],
        )

        assert (
            result['message']
            == 'Successfully created DB instance parameter group test-instance-param-group'
        )
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['Tags'] == [
            {'Key': 'Environment', 'Value': 'Development'},
            {'Key': 'Purpose', 'Value': 'Testing'},
            {'Key': 'mcp_server_version', 'Value': '0.1.0'},
            {'Key': 'created_by', 'Value': 'rds-management-mcp-server'},
        ]

    @pytest.mark.asyncio
    async def test_create_instance_parameter_group_readonly_mode(self, mock_rds_context_readonly):
        """Test instance parameter group creation in readonly mode."""
        result = await create_db_instance_parameter_group(
            db_parameter_group_name='test-instance-param-group',
            db_parameter_group_family='mysql8.0',
            description='Test instance parameter group',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_create_instance_parameter_group_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test instance parameter group creation with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'DBParameterGroupAlreadyExistsFault',
                        'Message': 'Parameter group already exists',
                    }
                },
                'CreateDBParameterGroup',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_instance_parameter_group(
            db_parameter_group_name='existing-param-group',
            db_parameter_group_family='mysql8.0',
            description='Test instance parameter group',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['error_code'] == 'DBParameterGroupAlreadyExistsFault'
        assert result['operation'] == 'create_db_instance_parameter_group'

    @pytest.mark.asyncio
    async def test_create_instance_parameter_group_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_instance_parameter_group(
            db_parameter_group_name='test-instance-param-group',
            db_parameter_group_family='mysql8.0',
            description='Test instance parameter group',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['operation'] == 'create_db_instance_parameter_group'
