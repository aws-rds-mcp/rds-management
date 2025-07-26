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

"""Tests for create_instance tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_instance.create_instance import create_db_instance
from botocore.exceptions import ClientError


class TestCreateDBInstance:
    """Test cases for create_db_instance function."""

    @pytest.mark.asyncio
    async def test_create_instance_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful instance creation."""
        mock_rds_client.create_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'creating',
                'DBInstanceClass': 'db.t3.micro',
                'Engine': 'mysql',
                'EngineVersion': '8.0.35',
                'MasterUsername': 'admin',
                'AllocatedStorage': 20,
                'Endpoint': {
                    'Address': 'test-instance.abc123.us-east-1.rds.amazonaws.com',
                    'Port': 3306,
                },
                'AvailabilityZone': 'us-east-1a',
                'MultiAZ': False,
                'StorageType': 'gp2',
                'StorageEncrypted': False,
                'BackupRetentionPeriod': 7,
                'DBName': 'testdb',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_instance(
            db_instance_identifier='test-instance',
            db_instance_class='db.t3.micro',
            engine='mysql',
            master_username='admin',
            allocated_storage=20,
            db_name='testdb',
        )

        assert result['message'] == 'Successfully created DB instance test-instance'
        assert result['formatted_instance']['instance_id'] == 'test-instance'
        assert 'DBInstance' in result
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_readonly_mode(self, mock_rds_context_readonly):
        """Test instance creation in readonly mode."""
        result = await create_db_instance(
            db_instance_identifier='test-instance', db_instance_class='db.t3.micro', engine='mysql'
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_create_instance_with_all_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test instance creation with all parameters."""
        mock_rds_client.create_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'creating',
                'DBInstanceClass': 'db.t3.micro',
                'Engine': 'mysql',
                'EngineVersion': '8.0.35',
                'MasterUsername': 'admin',
                'AllocatedStorage': 100,
                'MultiAZ': True,
                'StorageType': 'gp2',
                'StorageEncrypted': True,
                'BackupRetentionPeriod': 14,
                'DBClusterIdentifier': 'test-cluster',
                'PubliclyAccessible': True,
                'Port': 3306,
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123456'}],
                'AvailabilityZone': 'us-east-1b',
                'DBSubnetGroup': {'DBSubnetGroupName': 'test-subnet-group'},
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_instance(
            db_instance_identifier='test-instance',
            db_instance_class='db.t3.micro',
            engine='mysql',
            allocated_storage=100,
            master_username='admin',
            db_name='testdb',
            db_cluster_identifier='test-cluster',
            vpc_security_group_ids=['sg-123456'],
            availability_zone='us-east-1b',
            db_subnet_group_name='test-subnet-group',
            multi_az=True,
            engine_version='8.0.35',
            storage_type='gp2',
            storage_encrypted=True,
            port=3306,
            publicly_accessible=True,
            backup_retention_period=14,
        )

        assert result['message'] == 'Successfully created DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBInstanceIdentifier'] == 'test-instance'
        assert call_args['DBInstanceClass'] == 'db.t3.micro'
        assert call_args['Engine'] == 'mysql'
        assert call_args['AllocatedStorage'] == 100
        assert call_args['MasterUsername'] == 'admin'
        assert call_args['DBName'] == 'testdb'
        assert call_args['DBClusterIdentifier'] == 'test-cluster'
        assert call_args['VpcSecurityGroupIds'] == ['sg-123456']
        assert call_args['AvailabilityZone'] == 'us-east-1b'
        assert call_args['DBSubnetGroupName'] == 'test-subnet-group'
        assert call_args['MultiAZ'] is True
        assert call_args['EngineVersion'] == '8.0.35'
        assert call_args['StorageType'] == 'gp2'
        assert call_args['StorageEncrypted'] is True
        assert call_args['Port'] == 3306
        assert call_args['PubliclyAccessible'] is True
        assert call_args['BackupRetentionPeriod'] == 14

    @pytest.mark.asyncio
    async def test_create_instance_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test instance creation with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'DBInstanceAlreadyExistsFault',
                        'Message': 'Instance already exists',
                    }
                },
                'CreateDBInstance',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_instance(
            db_instance_identifier='existing-instance',
            db_instance_class='db.t3.micro',
            engine='mysql',
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['error_code'] == 'DBInstanceAlreadyExistsFault'
        assert result['operation'] == 'create_db_instance'

    @pytest.mark.asyncio
    async def test_create_instance_adds_mcp_tags(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test that MCP tags are added to instance creation."""
        mock_rds_client.create_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'creating',
                'Engine': 'mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        await create_db_instance(
            db_instance_identifier='test-instance', db_instance_class='db.t3.micro', engine='mysql'
        )

        call_args = mock_asyncio_thread.call_args[1]
        tags = call_args.get('Tags', [])

        # Check that MCP tags were added
        tag_keys = [tag['Key'] for tag in tags]
        assert 'mcp_server_version' in tag_keys
        assert 'created_by' in tag_keys

    @pytest.mark.asyncio
    async def test_create_instance_minimal_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test instance creation with minimal parameters."""
        mock_rds_client.create_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'creating',
                'Engine': 'mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_instance(
            db_instance_identifier='test-instance', db_instance_class='db.t3.micro', engine='mysql'
        )

        assert result['message'] == 'Successfully created DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBInstanceIdentifier'] == 'test-instance'
        assert call_args['DBInstanceClass'] == 'db.t3.micro'
        assert call_args['Engine'] == 'mysql'

    @pytest.mark.asyncio
    async def test_create_instance_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_instance(
            db_instance_identifier='test-instance', db_instance_class='db.t3.micro', engine='mysql'
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['operation'] == 'create_db_instance'

    @pytest.mark.asyncio
    async def test_create_instance_manage_master_password(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test that ManageMasterUserPassword is set when no password provided."""
        mock_rds_client.create_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'creating',
                'Engine': 'mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        await create_db_instance(
            db_instance_identifier='test-instance',
            db_instance_class='db.t3.micro',
            engine='mysql',
            master_username='admin',
        )

        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['ManageMasterUserPassword'] is True
