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

"""Tests for failover_cluster tool."""

import pytest
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    _pending_operations,
)
from awslabs.rds_management_mcp_server.tools.db_cluster.failover_cluster import failover_db_cluster
from botocore.exceptions import ClientError


class TestFailoverDBCluster:
    """Test cases for failover_db_cluster function."""

    def setup_method(self):
        """Clear pending operations before each test."""
        _pending_operations.clear()

    @pytest.mark.asyncio
    async def test_failover_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster failover."""
        mock_rds_client.failover_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'failing-over',
                'Engine': 'aurora-mysql',
                'DBClusterMembers': [
                    {
                        'DBInstanceIdentifier': 'test-instance-1',
                        'IsClusterWriter': False,
                        'PromotionTier': 1,
                    },
                    {
                        'DBInstanceIdentifier': 'test-instance-2',
                        'IsClusterWriter': True,
                        'PromotionTier': 1,
                    },
                ],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # First call without confirmation token
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result
        assert 'WARNING' in result['warning']

        # Second call with confirmation token
        token = result['confirmation_token']
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )

        assert result['message'] == 'Successfully initiated failover for DB cluster test-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'failing-over'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_failover_cluster_with_target(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster failover with target instance."""
        mock_rds_client.failover_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'failing-over',
                'Engine': 'aurora-mysql',
                'DBClusterMembers': [
                    {
                        'DBInstanceIdentifier': 'test-instance-1',
                        'IsClusterWriter': False,
                        'PromotionTier': 1,
                    },
                    {
                        'DBInstanceIdentifier': 'test-instance-2',
                        'IsClusterWriter': True,
                        'PromotionTier': 1,
                    },
                ],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # First call without confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', target_db_instance_identifier='test-instance-2'
        )

        assert result['requires_confirmation'] is True
        token = result['confirmation_token']

        # Second call with confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster',
            target_db_instance_identifier='test-instance-2',
            confirmation_token=token,
        )

        assert result['message'] == 'Successfully initiated failover for DB cluster test-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'failing-over'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['TargetDBInstanceIdentifier'] == 'test-instance-2'

    @pytest.mark.asyncio
    async def test_failover_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster failover in readonly mode."""
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')

        assert isinstance(result, dict) and 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_failover_cluster_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster failover with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'Cluster not found'}},
                'FailoverDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        # First get confirmation token
        result = await failover_db_cluster(db_cluster_identifier='nonexistent-cluster')
        token = result['confirmation_token']

        # Then try with confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='nonexistent-cluster', confirmation_token=token
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'DBClusterNotFoundFault'

    @pytest.mark.asyncio
    async def test_failover_cluster_invalid_confirmation_token(self, mock_rds_context_allowed):
        """Test with invalid confirmation token."""
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token='invalid-token'
        )

        assert isinstance(result, dict) and 'error' in result
        assert (
            'Invalid' in result['error']
            or 'expired' in result['error']
            or 'token' in result['error']
        )

    @pytest.mark.asyncio
    async def test_failover_cluster_parameter_mismatch(self, mock_rds_context_allowed):
        """Test with parameter mismatch."""
        # Get token for one cluster
        result = await failover_db_cluster(db_cluster_identifier='cluster-1')
        token = result['confirmation_token']

        # Try to use token for different cluster
        result = await failover_db_cluster(
            db_cluster_identifier='cluster-2', confirmation_token=token
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'Parameter mismatch' in result['error']

    @pytest.mark.asyncio
    async def test_failover_cluster_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        # First get confirmation token
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')
        token = result['confirmation_token']

        # Then try with confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'General error' in result['error']

    @pytest.mark.asyncio
    async def test_failover_cluster_no_target_instance(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster failover without target instance."""
        mock_rds_client.failover_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'failing-over',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # First call without confirmation token
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')
        token = result['confirmation_token']

        # Second call with confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )

        assert result['message'] == 'Successfully initiated failover for DB cluster test-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'failing-over'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterIdentifier'] == 'test-cluster'
        # TargetDBInstanceIdentifier should not be set if not provided
        assert 'TargetDBInstanceIdentifier' not in call_args

    @pytest.mark.asyncio
    async def test_failover_cluster_invalid_target(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test failover with an invalid target instance identifier."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidDBInstanceStateFault',
                        'Message': 'Instance is not a read replica',
                    }
                },
                'FailoverDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        # First get confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', target_db_instance_identifier='invalid-instance'
        )
        token = result['confirmation_token']

        # Then try with confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster',
            target_db_instance_identifier='invalid-instance',
            confirmation_token=token,
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'InvalidDBInstanceStateFault'

    @pytest.mark.asyncio
    async def test_failover_cluster_result_formatting(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test the formatting of the cluster information in the result."""
        mock_rds_client.failover_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'failing-over',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'Endpoint': 'test-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com',
                'ReaderEndpoint': 'test-cluster.cluster-ro-123456789012.us-west-2.rds.amazonaws.com',
                'MultiAZ': True,
                'AvailabilityZones': ['us-west-2a', 'us-west-2b', 'us-west-2c'],
                'DBClusterMembers': [
                    {
                        'DBInstanceIdentifier': 'test-instance-1',
                        'IsClusterWriter': True,
                        'DBClusterParameterGroupStatus': 'in-sync',
                        'PromotionTier': 1,
                    },
                    {
                        'DBInstanceIdentifier': 'test-instance-2',
                        'IsClusterWriter': False,
                        'DBClusterParameterGroupStatus': 'in-sync',
                        'PromotionTier': 2,
                    },
                ],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        # First get confirmation token
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')
        token = result['confirmation_token']

        # Then try with confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )

        assert result['message'] == 'Successfully initiated failover for DB cluster test-cluster'
        formatted_cluster = result['formatted_cluster']
        assert formatted_cluster['cluster_id'] == 'test-cluster'
        assert formatted_cluster['status'] == 'failing-over'
        assert formatted_cluster['engine'] == 'aurora-mysql'
        assert formatted_cluster['engine_version'] == '5.7.mysql_aurora.2.10.2'
        assert (
            formatted_cluster['endpoint']
            == 'test-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com'
        )
        assert (
            formatted_cluster['reader_endpoint']
            == 'test-cluster.cluster-ro-123456789012.us-west-2.rds.amazonaws.com'
        )
        assert formatted_cluster['multi_az'] is True
        assert len(formatted_cluster['members']) == 2
        assert formatted_cluster['members'][0]['instance_id'] == 'test-instance-1'
        assert formatted_cluster['members'][0]['is_writer'] is True
        assert formatted_cluster['members'][1]['instance_id'] == 'test-instance-2'
        assert formatted_cluster['members'][1]['is_writer'] is False
        assert 'DBCluster' in result

    @pytest.mark.asyncio
    async def test_failover_cluster_invalid_state(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test failover when the cluster is not in a valid state for failover."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidDBClusterStateFault',
                        'Message': 'Cluster is not in available state',
                    }
                },
                'FailoverDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        # First get confirmation token
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')
        token = result['confirmation_token']

        # Then try with confirmation token
        result = await failover_db_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'InvalidDBClusterStateFault'
