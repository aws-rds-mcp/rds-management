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

"""Tests for delete_cluster tool."""

import pytest
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    _pending_operations,
)
from awslabs.rds_management_mcp_server.tools.db_cluster.delete_cluster import delete_db_cluster
from botocore.exceptions import ClientError


class TestDeleteCluster:
    """Test cases for delete_cluster function."""

    def setup_method(self):
        """Clear pending operations before each test."""
        _pending_operations.clear()

    @pytest.mark.asyncio
    async def test_delete_cluster_requires_confirmation(self, mock_rds_context_allowed):
        """Test delete cluster requires confirmation when no token provided."""
        result = await delete_db_cluster(db_cluster_identifier='test-cluster')

        assert result['requires_confirmation'] is True
        assert 'warning' in result
        assert 'WARNING' in result['warning']
        assert 'confirmation_token' in result
        assert result['confirmation_token'] is not None

    @pytest.mark.asyncio
    async def test_delete_cluster_with_confirmation(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster deletion with valid confirmation token."""
        mock_rds_client.delete_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'deleting',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # Get confirmation token first
        result1 = await delete_db_cluster(db_cluster_identifier='test-cluster')
        token = result1['confirmation_token']

        # Use token to confirm deletion
        result2 = await delete_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )

        assert result2['message'] == 'Successfully deleted DB cluster test-cluster'
        assert result2['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result2['formatted_cluster']['status'] == 'deleting'
        assert result2['formatted_cluster']['engine'] == 'aurora-mysql'
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster deletion in readonly mode."""
        result = await delete_db_cluster(db_cluster_identifier='test-cluster')

        assert isinstance(result, dict) and 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_delete_cluster_with_final_snapshot(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster deletion with final snapshot."""
        mock_rds_client.delete_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'deleting',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # Get confirmation token first
        result1 = await delete_db_cluster(db_cluster_identifier='test-cluster')
        token = result1['confirmation_token']

        # Use token with snapshot option
        result2 = await delete_db_cluster(
            db_cluster_identifier='test-cluster',
            confirmation_token=token,
            skip_final_snapshot=False,
            final_db_snapshot_identifier='test-cluster-final-snapshot',
        )

        assert result2['message'] == 'Successfully deleted DB cluster test-cluster'
        assert result2['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result2['formatted_cluster']['status'] == 'deleting'
        assert result2['formatted_cluster']['engine'] == 'aurora-mysql'
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['SkipFinalSnapshot'] is False
        assert call_args['FinalDBSnapshotIdentifier'] == 'test-cluster-final-snapshot'

    @pytest.mark.asyncio
    async def test_delete_cluster_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster deletion with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'Cluster not found'}},
                'DeleteDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        # Get confirmation token first
        result1 = await delete_db_cluster(db_cluster_identifier='nonexistent-cluster')
        token = result1['confirmation_token']

        # Try to delete with confirmation
        result2 = await delete_db_cluster(
            db_cluster_identifier='nonexistent-cluster', confirmation_token=token
        )

        assert isinstance(result2, dict) and ('error' in result2 or 'error_code' in result2)
        if 'error_code' in result2:
            assert result2['error_code'] == 'DBClusterNotFoundFault'

    @pytest.mark.asyncio
    async def test_delete_cluster_invalid_token(self, mock_rds_context_allowed):
        """Test cluster deletion with invalid confirmation token."""
        result = await delete_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token='invalid-token'
        )

        assert isinstance(result, dict) and 'error' in result
        assert (
            'Invalid' in result['error']
            or 'expired' in result['error']
            or 'token' in result['error']
        )

    @pytest.mark.asyncio
    async def test_delete_cluster_missing_final_snapshot_identifier(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster deletion without final snapshot identifier when required."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidParameterCombination',
                        'Message': 'FinalDBSnapshotIdentifier must be provided when SkipFinalSnapshot is false.',
                    }
                },
                'DeleteDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        # Get confirmation token first
        result1 = await delete_db_cluster(db_cluster_identifier='test-cluster')
        token = result1['confirmation_token']

        # Try to delete with confirmation but missing final snapshot identifier
        result2 = await delete_db_cluster(
            db_cluster_identifier='test-cluster',
            confirmation_token=token,
            skip_final_snapshot=False,
        )

        assert isinstance(result2, dict) and ('error' in result2 or 'error_code' in result2)
        if 'error_code' in result2:
            assert result2['error_code'] == 'InvalidParameterCombination'

    @pytest.mark.asyncio
    async def test_delete_cluster_invalid_final_snapshot_identifier(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster deletion with an invalid final snapshot identifier."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidParameterValue',
                        'Message': 'The specified FinalDBSnapshotIdentifier is invalid.',
                    }
                },
                'DeleteDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        # Get confirmation token first
        result1 = await delete_db_cluster(db_cluster_identifier='test-cluster')
        token = result1['confirmation_token']

        # Try to delete with confirmation and invalid final snapshot identifier
        result2 = await delete_db_cluster(
            db_cluster_identifier='test-cluster',
            confirmation_token=token,
            skip_final_snapshot=False,
            final_db_snapshot_identifier='invalid/snapshot-name',
        )

        assert isinstance(result2, dict) and ('error' in result2 or 'error_code' in result2)
        if 'error_code' in result2:
            assert result2['error_code'] == 'InvalidParameterValue'

    @pytest.mark.asyncio
    async def test_delete_cluster_general_exception(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster deletion with a general exception."""

        async def async_error(func, **kwargs):
            raise Exception('Unexpected error occurred')

        mock_asyncio_thread.side_effect = async_error

        # Get confirmation token first
        result1 = await delete_db_cluster(db_cluster_identifier='test-cluster')
        token = result1['confirmation_token']

        # Try to delete with confirmation
        result2 = await delete_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )

        assert isinstance(result2, dict) and 'error' in result2
        assert 'Unexpected error occurred' in result2['error']
