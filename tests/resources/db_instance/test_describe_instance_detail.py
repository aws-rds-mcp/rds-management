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

"""Tests for describe_instance_detail resource."""

import pytest
from awslabs.rds_management_mcp_server.resources.db_instance.describe_instance_detail import (
    Instance,
    describe_instance_detail,
)


class TestDescribeInstanceDetail:
    """Test cases for describe_instance_detail resource."""

    @pytest.mark.asyncio
    async def test_describe_instance_detail_success(self, mock_rds_client, sample_db_instance):
        """Test successful instance detail retrieval."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': [sample_db_instance]}

        instance_id = 'test-instance'
        result = await describe_instance_detail(instance_id)

        assert isinstance(result, Instance)
        assert result.instance_id == 'test-db-instance'
        assert result.instance_class == 'db.t3.micro'
        assert result.engine == 'mysql'
        assert result.engine_version == '8.0.35'
        assert result.status == 'available'
        assert result.multi_az is False
        assert result.publicly_accessible is True
        assert result.preferred_backup_window == '03:00-04:00'
        assert result.preferred_maintenance_window == 'sun:04:00-sun:05:00'
        assert result.availability_zone == 'us-east-1a'
        assert result.db_cluster == 'test-cluster'
        assert result.endpoint.address == 'test-db-instance.abc123.us-east-1.rds.amazonaws.com'
        assert result.endpoint.port == 3306
        assert len(result.vpc_security_groups) == 1
        assert result.resource_uri == f'aws-rds://db-instance/{instance_id}'

        mock_rds_client.describe_db_instances.assert_called_once_with(
            DBInstanceIdentifier='test-instance'
        )

    @pytest.mark.asyncio
    async def test_describe_instance_detail_not_found(self, mock_rds_client):
        """Test instance detail retrieval with instance not found."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': []}

        instance_id = 'nonexistent-instance'

        result = await describe_instance_detail(instance_id)
        assert 'error' in result
        assert 'not found' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_describe_instance_detail_empty_response(self, mock_rds_client):
        """Test instance detail retrieval with empty response."""
        mock_rds_client.describe_db_instances.return_value = {'DBInstances': []}

        instance_id = 'empty-instance'

        result = await describe_instance_detail(instance_id)
        assert 'error' in result
        assert 'not found' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_describe_instance_detail_minimal_instance(self, mock_rds_client):
        """Test instance detail retrieval with minimal instance data."""
        minimal_instance = {
            'DBInstanceIdentifier': 'minimal-instance',
            'DBInstanceClass': 'db.t3.micro',
            'Engine': 'mysql',
            'DBInstanceStatus': 'available',
            'AvailabilityZone': 'us-east-1a',
        }

        mock_rds_client.describe_db_instances.return_value = {'DBInstances': [minimal_instance]}

        instance_id = 'minimal-instance'
        result = await describe_instance_detail(instance_id)

        assert isinstance(result, Instance)
        assert result.instance_id == 'minimal-instance'
        assert result.instance_class == 'db.t3.micro'
        assert result.engine == 'mysql'
        assert result.status == 'available'
        assert result.availability_zone == 'us-east-1a'
        # Optional fields should have default values
        assert result.endpoint is None
        assert result.storage is not None  # Storage object exists but with None values
        assert result.storage.type is None
        assert result.storage.allocated is None
        assert result.storage.encrypted is None
        assert result.multi_az is False
        assert result.publicly_accessible is False
        assert result.vpc_security_groups == []

    @pytest.mark.asyncio
    async def test_describe_instance_detail_with_tags(self, mock_rds_client):
        """Test instance detail retrieval with tags."""
        instance_with_tags = {
            'DBInstanceIdentifier': 'tagged-instance',
            'DBInstanceClass': 'db.t3.micro',
            'Engine': 'mysql',
            'DBInstanceStatus': 'available',
            'AvailabilityZone': 'us-east-1a',
            'TagList': [
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Team', 'Value': 'DataEngineering'},
            ],
        }

        mock_rds_client.describe_db_instances.return_value = {'DBInstances': [instance_with_tags]}

        instance_id = 'tagged-instance'
        result = await describe_instance_detail(instance_id)

        assert isinstance(result, Instance)
        assert result.instance_id == 'tagged-instance'
        assert len(result.tags) == 2
        assert result.tags['Environment'] == 'Production'
        assert result.tags['Team'] == 'DataEngineering'

    @pytest.mark.asyncio
    async def test_describe_instance_detail_exception_handling(self, mock_rds_client):
        """Test instance detail retrieval with general exception."""
        mock_rds_client.describe_db_instances.side_effect = Exception('General error')

        instance_id = 'test-instance'

        result = await describe_instance_detail(instance_id)
        assert 'error' in result
        assert 'general error' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_describe_instance_detail_with_read_replicas(self, mock_rds_client):
        """Test instance detail retrieval with read replicas."""
        instance_with_replicas = {
            'DBInstanceIdentifier': 'primary-instance',
            'DBInstanceClass': 'db.t3.micro',
            'Engine': 'mysql',
            'DBInstanceStatus': 'available',
            'AvailabilityZone': 'us-east-1a',
            'ReadReplicaDBInstanceIdentifiers': ['replica-1', 'replica-2'],
            'ReadReplicaSourceDBInstanceIdentifier': None,
        }

        mock_rds_client.describe_db_instances.return_value = {
            'DBInstances': [instance_with_replicas]
        }

        instance_id = 'primary-instance'
        result = await describe_instance_detail(instance_id)

        assert isinstance(result, Instance)
        assert result.instance_id == 'primary-instance'
        assert result.read_replica_db_instance_identifiers == ['replica-1', 'replica-2']
        assert result.read_replica_source_db_instance_identifier is None
