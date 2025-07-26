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

"""Tests for change_cluster_status tool."""

import pytest
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    _pending_operations,
)
from awslabs.rds_management_mcp_server.tools.db_cluster.change_cluster_status import (
    status_db_cluster,
)
from botocore.exceptions import ClientError


class TestChangeDBClusterStatus:
    """Test cases for change_db_cluster_status function."""

    def setup_method(self):
        """Clear pending operations before each test."""
        _pending_operations.clear()

    @pytest.mark.asyncio
    async def test_stop_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster stop."""
        mock_rds_client.stop_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'stopping',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # First call without confirmation token
        result = await status_db_cluster(db_cluster_identifier='test-cluster', action='stop')

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result
        assert 'WARNING' in result['warning']

        # Second call with confirmation token
        token = result['confirmation_token']
        result = await status_db_cluster(
            db_cluster_identifier='test-cluster', action='stop', confirmation_token=token
        )

        assert 'stopped successfully' in result['message'] or 'Successfully' in result['message']
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'stopping'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterIdentifier'] == 'test-cluster'

    @pytest.mark.asyncio
    async def test_start_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster start."""
        mock_rds_client.start_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'starting',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # First call without confirmation token
        result = await status_db_cluster(db_cluster_identifier='test-cluster', action='start')

        assert result['requires_confirmation'] is True
        token = result['confirmation_token']

        # Second call with confirmation token
        result = await status_db_cluster(
            db_cluster_identifier='test-cluster', action='start', confirmation_token=token
        )

        assert 'started successfully' in result['message'] or 'Successfully' in result['message']
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'starting'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterIdentifier'] == 'test-cluster'

    @pytest.mark.asyncio
    async def test_reboot_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster reboot."""
        mock_rds_client.reboot_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'rebooting',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # First call without confirmation token
        result = await status_db_cluster(db_cluster_identifier='test-cluster', action='reboot')

        assert result['requires_confirmation'] is True
        token = result['confirmation_token']

        # Second call with confirmation token
        result = await status_db_cluster(
            db_cluster_identifier='test-cluster', action='reboot', confirmation_token=token
        )

        assert 'reboot' in result['message'].lower() or 'Successfully' in result['message']
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'rebooting'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterIdentifier'] == 'test-cluster'

    @pytest.mark.asyncio
    async def test_invalid_action(self, mock_rds_context_allowed):
        """Test with invalid action."""
        # First get confirmation token
        result1 = await status_db_cluster(
            db_cluster_identifier='test-cluster', action='invalid-action'
        )
        token = result1['confirmation_token']

        # Then call with invalid action and token
        result2 = await status_db_cluster(
            db_cluster_identifier='test-cluster', action='invalid-action', confirmation_token=token
        )

        assert 'error' in result2
        assert 'Invalid action' in result2['error']

    @pytest.mark.asyncio
    async def test_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster status change in readonly mode."""
        result = await status_db_cluster(db_cluster_identifier='test-cluster', action='stop')

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster status change with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'Cluster not found'}},
                'StopDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        # First get confirmation token
        result = await status_db_cluster(
            db_cluster_identifier='nonexistent-cluster', action='stop'
        )
        token = result['confirmation_token']

        # Then try with confirmation token
        result = await status_db_cluster(
            db_cluster_identifier='nonexistent-cluster', action='stop', confirmation_token=token
        )

        assert 'error' in result
        # Exception handler formats the error differently
        assert (
            'DBClusterNotFoundFault' in result.get('error', '')
            or result.get('error_code') == 'DBClusterNotFoundFault'
        )

    @pytest.mark.asyncio
    async def test_invalid_confirmation_token(self, mock_rds_context_allowed):
        """Test with invalid confirmation token."""
        result = await status_db_cluster(
            db_cluster_identifier='test-cluster', action='stop', confirmation_token='invalid-token'
        )

        assert 'error' in result
        assert 'Invalid or expired confirmation token' in result['error']

    @pytest.mark.asyncio
    async def test_parameter_mismatch(self, mock_rds_context_allowed):
        """Test with parameter mismatch."""
        # Get token for one cluster
        result = await status_db_cluster(db_cluster_identifier='cluster-1', action='stop')
        token = result['confirmation_token']

        # Try to use token for different cluster
        result = await status_db_cluster(
            db_cluster_identifier='cluster-2', action='stop', confirmation_token=token
        )

        assert 'error' in result
        assert 'Parameter mismatch' in result['error']

    @pytest.mark.asyncio
    async def test_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        # First get confirmation token
        result = await status_db_cluster(db_cluster_identifier='test-cluster', action='stop')
        token = result['confirmation_token']

        # Then try with confirmation token
        result = await status_db_cluster(
            db_cluster_identifier='test-cluster', action='stop', confirmation_token=token
        )

        assert 'error' in result
        assert 'General error' in result['error']
