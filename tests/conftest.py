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

"""Global pytest fixtures for Amazon RDS Management MCP Server tests."""

import os
import pytest
from awslabs.rds_management_mcp_server.common.connection import RDSConnectionManager
from awslabs.rds_management_mcp_server.common.context import RDSContext
from unittest.mock import MagicMock, patch


@pytest.fixture(scope='session', autouse=True)
def tests_setup_and_teardown():
    """Mock environment and module variables for testing."""
    # Will be executed before the first test
    old_environ = dict(os.environ)
    os.environ.update(
        {
            'AWS_DEFAULT_REGION': 'us-east-1',  # pragma: allowlist secret
            'AWS_ACCESS_KEY_ID': 'mock_access_key',  # pragma: allowlist secret
            'AWS_SECRET_ACCESS_KEY': 'mock_secret_key',  # pragma: allowlist secret
        }
    )

    yield
    # Will be executed after the last test
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_rds_client():
    """Fixture providing a mock RDS client for tests.

    Resets the RDS connection before and after the test.
    Returns a mock client that's automatically patched into the RDSConnectionManager.
    """
    RDSConnectionManager._client = None

    mock_client = MagicMock()

    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_client) as _:
        yield mock_client

    RDSConnectionManager._client = None


@pytest.fixture
def mock_rds_context_allowed():
    """Mock RDS context to allow operations (readonly_mode returns False)."""
    with patch.object(RDSContext, 'readonly_mode', return_value=False) as mock:
        yield mock


@pytest.fixture
def mock_rds_context_readonly():
    """Mock RDS context to deny operations (readonly_mode returns True)."""
    with patch.object(RDSContext, 'readonly_mode', return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_asyncio_thread():
    """Mock asyncio.to_thread for testing async operations."""
    with patch('asyncio.to_thread') as mock:
        yield mock


@pytest.fixture
def sample_db_cluster():
    """Return a sample DB cluster response."""
    return {
        'DBClusterIdentifier': 'test-db-cluster',
        'Status': 'available',
        'Engine': 'aurora-mysql',
        'EngineVersion': '5.7.mysql_aurora.2.10.2',
        'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test-db-cluster',
        'Endpoint': 'test-db-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
        'ReaderEndpoint': 'test-db-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
        'Port': 3306,
        'MasterUsername': 'admin',
        'AvailabilityZones': ['us-east-1a', 'us-east-1b', 'us-east-1c'],
        'MultiAZ': True,
        'EngineMode': 'provisioned',
        'DBClusterMembers': [
            {
                'DBInstanceIdentifier': 'test-db-instance-1',
                'IsClusterWriter': True,
                'DBClusterParameterGroupStatus': 'in-sync',
                'PromotionTier': 1,
            },
            {
                'DBInstanceIdentifier': 'test-db-instance-2',
                'IsClusterWriter': False,
                'DBClusterParameterGroupStatus': 'in-sync',
                'PromotionTier': 1,
            },
        ],
        'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345678', 'Status': 'active'}],
        'DBClusterParameterGroup': 'default.aurora-mysql5.7',
        'DBSubnetGroup': 'default',
        'BackupRetentionPeriod': 7,
        'PreferredBackupWindow': '07:00-09:00',
        'PreferredMaintenanceWindow': 'sun:04:00-sun:05:00',
        'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
    }


@pytest.fixture
def sample_db_instance():
    """Return a sample DB instance response."""
    return {
        'DBInstanceIdentifier': 'test-db-instance',
        'DBInstanceClass': 'db.t3.micro',
        'Engine': 'mysql',
        'EngineVersion': '8.0.35',
        'DBInstanceStatus': 'available',
        'MasterUsername': 'admin',
        'DBName': 'testdb',
        'Endpoint': {
            'Address': 'test-db-instance.abc123.us-east-1.rds.amazonaws.com',
            'Port': 3306,
            'HostedZoneId': 'Z2R2ITUGPM61AM',
        },
        'AllocatedStorage': 20,
        'InstanceCreateTime': '2023-01-01T00:00:00.000Z',
        'PreferredBackupWindow': '03:00-04:00',
        'BackupRetentionPeriod': 7,
        'DBSecurityGroups': [],
        'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345678', 'Status': 'active'}],
        'DBParameterGroups': [
            {'DBParameterGroupName': 'default.mysql8.0', 'ParameterApplyStatus': 'in-sync'}
        ],
        'AvailabilityZone': 'us-east-1a',
        'DBSubnetGroup': {
            'DBSubnetGroupName': 'default',
            'DBSubnetGroupDescription': 'default',
            'VpcId': 'vpc-12345678',
            'SubnetGroupStatus': 'Complete',
            'Subnets': [],
        },
        'PreferredMaintenanceWindow': 'sun:04:00-sun:05:00',
        'PendingModifiedValues': {},
        'LatestRestorableTime': '2023-01-01T00:00:00.000Z',
        'MultiAZ': False,
        'AutoMinorVersionUpgrade': True,
        'ReadReplicaDBInstanceIdentifiers': [],
        'LicenseModel': 'general-public-license',
        'OptionGroupMemberships': [{'OptionGroupName': 'default:mysql-8-0', 'Status': 'in-sync'}],
        'PubliclyAccessible': True,
        'StorageType': 'gp2',
        'StorageEncrypted': False,
        'DbiResourceId': 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ',  # pragma: allowlist secret
        'CACertificateIdentifier': 'rds-ca-2019',
        'DomainMemberships': [],
        'CopyTagsToSnapshot': False,
        'MonitoringInterval': 0,
        'DBInstanceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-db-instance',
        'TagList': [{'Key': 'Environment', 'Value': 'Test'}],
        'DBClusterIdentifier': 'test-cluster',
        'DeletionProtection': False,
        'AssociatedRoles': [],
        'MaxAllocatedStorage': 1000,
    }


@pytest.fixture
def sample_parameter_group():
    """Return a sample parameter group response."""
    return {
        'DBParameterGroupName': 'test-parameter-group',
        'DBParameterGroupFamily': 'mysql8.0',
        'Description': 'Test parameter group',
        'DBParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:pg:test-parameter-group',
    }


@pytest.fixture
def sample_cluster_parameter_group():
    """Return a sample cluster parameter group response."""
    return {
        'DBClusterParameterGroupName': 'test-cluster-parameter-group',
        'DBParameterGroupFamily': 'aurora-mysql5.7',
        'Description': 'Test cluster parameter group',
        'DBClusterParameterGroupArn': 'arn:aws:rds:us-east-1:123456789012:cluster-pg:test-cluster-parameter-group',
    }


@pytest.fixture
def sample_snapshot():
    """Return a sample snapshot response."""
    return {
        'DBClusterSnapshotIdentifier': 'test-snapshot',
        'DBClusterIdentifier': 'test-cluster',
        'SnapshotCreateTime': '2023-01-01T00:00:00.000Z',
        'Engine': 'aurora-mysql',
        'EngineVersion': '5.7.mysql_aurora.2.10.2',
        'AllocatedStorage': 20,
        'Status': 'available',
        'Port': 3306,
        'VpcId': 'vpc-12345678',
        'ClusterCreateTime': '2023-01-01T00:00:00.000Z',
        'MasterUsername': 'admin',
        'EngineMode': 'provisioned',
        'LicenseModel': 'general-public-license',
        'SnapshotType': 'manual',
        'PercentProgress': 100,
        'StorageEncrypted': False,
        'DBClusterSnapshotArn': 'arn:aws:rds:us-east-1:123456789012:cluster-snapshot:test-snapshot',
        'TagList': [],
    }


@pytest.fixture
def context():
    """Create a mock context for MCP tools."""
    mock_ctx = MagicMock()
    return mock_ctx
