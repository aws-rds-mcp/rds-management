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

"""Tests for modify_cluster tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_cluster.modify_cluster import modify_db_cluster
from botocore.exceptions import ClientError


class TestModifyDBCluster:
    """Test cases for modify_db_cluster function."""

    @pytest.mark.asyncio
    async def test_modify_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster modification."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'modifying',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'MasterUsername': 'admin',
                'BackupRetentionPeriod': 14,
                'Port': 3306,
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            backup_retention_period=14,
            apply_immediately=True,
        )

        assert result['message'] == 'Successfully modified DB cluster test-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'modifying'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        assert result['formatted_cluster']['engine_version'] == '5.7.mysql_aurora.2.10.2'
        assert result['formatted_cluster']['backup_retention'] == 14
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_modify_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster modification in readonly mode."""
        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster', backup_retention_period=14
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_modify_cluster_with_all_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with all parameters."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'modifying',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.3',
                'BackupRetentionPeriod': 21,
                'Port': 3307,
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123456'}],
                'DBClusterParameterGroup': 'custom-param-group',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            apply_immediately=True,
            backup_retention_period=21,
            db_cluster_parameter_group_name='custom-param-group',
            vpc_security_group_ids=['sg-123456'],
            port=3307,
            engine_version='5.7.mysql_aurora.2.10.3',
            allow_major_version_upgrade=True,
        )

        assert result['message'] == 'Successfully modified DB cluster test-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'modifying'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        assert result['formatted_cluster']['backup_retention'] == 21
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['ApplyImmediately'] is True
        assert call_args['BackupRetentionPeriod'] == 21
        assert call_args['DBClusterParameterGroupName'] == 'custom-param-group'
        assert call_args['VpcSecurityGroupIds'] == ['sg-123456']
        assert call_args['Port'] == 3307
        assert call_args['EngineVersion'] == '5.7.mysql_aurora.2.10.3'
        assert call_args['AllowMajorVersionUpgrade'] is True

    @pytest.mark.asyncio
    async def test_modify_cluster_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'Cluster not found'}},
                'ModifyDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await modify_db_cluster(
            db_cluster_identifier='nonexistent-cluster', backup_retention_period=14
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'DBClusterNotFoundFault'

    @pytest.mark.asyncio
    async def test_modify_cluster_no_changes(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with no actual changes."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'available',
                'Engine': 'aurora-mysql',
                'BackupRetentionPeriod': 7,
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            backup_retention_period=7,  # Same as current
        )

        assert result['message'] == 'Successfully modified DB cluster test-cluster'
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_modify_cluster_minimal_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with minimal parameters."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'modifying',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster', backup_retention_period=10
        )

        assert result['message'] == 'Successfully modified DB cluster test-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert result['formatted_cluster']['status'] == 'modifying'
        assert result['formatted_cluster']['engine'] == 'aurora-mysql'
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterIdentifier'] == 'test-cluster'
        assert call_args['BackupRetentionPeriod'] == 10
        # ApplyImmediately should not be set if not provided
        assert 'ApplyImmediately' not in call_args

    @pytest.mark.asyncio
    async def test_modify_cluster_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster', backup_retention_period=14
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'General error' in result['error']

    @pytest.mark.asyncio
    async def test_modify_cluster_invalid_parameter(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with an invalid parameter value."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidParameterValue',
                        'Message': 'Invalid backup retention period',
                    }
                },
                'ModifyDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            backup_retention_period=40,  # Assuming this is an invalid value
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'InvalidParameterValue'

    @pytest.mark.asyncio
    async def test_modify_cluster_result_formatting(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test the formatting of the modified cluster information in the result."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'modifying',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.3',
                'BackupRetentionPeriod': 14,
                'Port': 3307,
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123456'}],
                'DBClusterParameterGroup': 'custom-param-group',
                'AvailabilityZones': ['us-west-2a', 'us-west-2b', 'us-west-2c'],
                'MultiAZ': True,
                'Endpoint': 'test-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com',
                'ReaderEndpoint': 'test-cluster.cluster-ro-123456789012.us-west-2.rds.amazonaws.com',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            backup_retention_period=14,
            port=3307,
            vpc_security_group_ids=['sg-123456'],
            db_cluster_parameter_group_name='custom-param-group',
            engine_version='5.7.mysql_aurora.2.10.3',
        )

        assert result['message'] == 'Successfully modified DB cluster test-cluster'
        formatted_cluster = result['formatted_cluster']
        assert formatted_cluster['cluster_id'] == 'test-cluster'
        assert formatted_cluster['status'] == 'modifying'
        assert formatted_cluster['engine'] == 'aurora-mysql'
        assert formatted_cluster['engine_version'] == '5.7.mysql_aurora.2.10.3'
        assert formatted_cluster['backup_retention'] == 14
        # The format_cluster_info function doesn't include these fields:
        # - port
        # - vpc_security_groups (it's formatted differently)
        # - db_cluster_parameter_group
        # - availability_zones
        assert formatted_cluster['multi_az'] is True
        assert (
            formatted_cluster['endpoint']
            == 'test-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com'
        )
        assert (
            formatted_cluster['reader_endpoint']
            == 'test-cluster.cluster-ro-123456789012.us-west-2.rds.amazonaws.com'
        )

    @pytest.mark.asyncio
    async def test_modify_cluster_conflicting_parameters(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with conflicting parameters."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidParameterCombination',
                        'Message': 'Cannot modify EngineVersion and AllowMajorVersionUpgrade at the same time',
                    }
                },
                'ModifyDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            engine_version='5.7.mysql_aurora.2.10.3',
            allow_major_version_upgrade=True,
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'InvalidParameterCombination'

    @pytest.mark.asyncio
    async def test_modify_cluster_pending_modification(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test modifying a cluster with a pending modification."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidDBClusterStateFault',
                        'Message': 'DB cluster has pending modifications',
                    }
                },
                'ModifyDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster', backup_retention_period=14
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'InvalidDBClusterStateFault'
