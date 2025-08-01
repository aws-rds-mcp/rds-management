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

"""Tests for create_cluster tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_cluster.create_cluster import create_db_cluster
from botocore.exceptions import ClientError


class TestCreateDBCluster:
    """Test cases for create_db_cluster function."""

    @pytest.mark.asyncio
    async def test_create_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster creation."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'MasterUsername': 'admin',
                'Endpoint': 'test-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
                'Port': 3306,
                'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        assert result['message'] == 'Successfully created DB cluster test-cluster'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert 'DBCluster' in result
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster creation in readonly mode."""
        result = await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_create_cluster_with_optional_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster creation with optional parameters."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'MasterUsername': 'admin',
                'Endpoint': 'test-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
                'Port': 3306,
                'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster(
            db_cluster_identifier='test-cluster',
            engine='aurora-mysql',
            master_username='admin',
            database_name='testdb',
            backup_retention_period=7,
            port=3306,
            vpc_security_group_ids=['sg-123456'],
            db_subnet_group_name='test-subnet-group',
            availability_zones=['us-east-1a', 'us-east-1b'],
            engine_version='5.7.mysql_aurora.2.10.2',
        )

        assert result['message'] == 'Successfully created DB cluster test-cluster'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DatabaseName'] == 'testdb'
        assert call_args['BackupRetentionPeriod'] == 7
        assert call_args['Port'] == 3306
        assert call_args['VpcSecurityGroupIds'] == ['sg-123456']
        assert call_args['DBSubnetGroupName'] == 'test-subnet-group'
        assert call_args['AvailabilityZones'] == ['us-east-1a', 'us-east-1b']
        assert call_args['EngineVersion'] == '5.7.mysql_aurora.2.10.2'

    @pytest.mark.asyncio
    async def test_create_cluster_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster creation with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'DBClusterAlreadyExistsFault',
                        'Message': 'Cluster already exists',
                    }
                },
                'CreateDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster(
            db_cluster_identifier='existing-cluster',
            engine='aurora-mysql',
            master_username='admin',
        )

        assert isinstance(result, dict) and 'error' in result
        assert (
            'DBClusterAlreadyExistsFault' in result.get('error', '')
            or result.get('error_code') == 'DBClusterAlreadyExistsFault'
        )

    @pytest.mark.asyncio
    async def test_create_cluster_adds_mcp_tags(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test that MCP tags are added to cluster creation."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        call_args = mock_asyncio_thread.call_args[1]
        tags = call_args.get('Tags', [])

        # Check that MCP tags were added
        tag_keys = [tag['Key'] for tag in tags]
        assert 'mcp_server_version' in tag_keys
        assert 'created_by' in tag_keys

    @pytest.mark.asyncio
    async def test_create_cluster_port_mapping(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test that port mapping works correctly for different engines."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        call_args = mock_asyncio_thread.call_args[1]
        # MySQL should default to port 3306
        assert call_args['Port'] == 3306

    @pytest.mark.asyncio
    async def test_create_cluster_manage_master_password(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test that ManageMasterUserPassword is set to True."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['ManageMasterUserPassword'] is True

    @pytest.mark.asyncio
    async def test_create_cluster_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'General error' in result['error']

    @pytest.mark.asyncio
    async def test_create_cluster_with_postgresql_engine(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster creation with PostgreSQL engine."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-postgres-cluster',
                'Status': 'creating',
                'Engine': 'aurora-postgresql',
                'EngineVersion': '13.7',
                'Port': 5432,
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster(
            db_cluster_identifier='test-postgres-cluster',
            engine='aurora-postgresql',
            master_username='admin',
        )

        assert result['message'] == 'Successfully created DB cluster test-postgres-cluster'
        assert result['formatted_cluster']['engine'] == 'aurora-postgresql'
        # Port will be in the DBCluster response, not in formatted_cluster

    @pytest.mark.asyncio
    async def test_create_cluster_with_invalid_engine(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster creation with an invalid engine."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'InvalidParameterValue',
                        'Message': 'Invalid engine specified',
                    }
                },
                'CreateDBCluster',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster(
            db_cluster_identifier='test-invalid-engine',
            engine='invalid-engine',
            master_username='admin',
        )

        assert isinstance(result, dict) and 'error' in result
        assert (
            'InvalidParameterValue' in result.get('error', '')
            or result.get('error_code') == 'InvalidParameterValue'
        )
