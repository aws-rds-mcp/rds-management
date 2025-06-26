import os
import pytest
import boto3
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture(scope='session', autouse=True)
def tests_setup_and_teardown():
    """Mock environment and module variables for testing."""
    # Will be executed before the first test
    old_environ = dict(os.environ)
    os.environ.update({
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'mock_access_key',
        'AWS_SECRET_ACCESS_KEY': 'mock_secret_key',
    })

    yield
    # Will be executed after the last test
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_rds_client():
    """Create a mock RDS client."""
    with patch('boto3.client') as mock_client:
        mock_rds = MagicMock()
        mock_client.return_value = mock_rds
        yield mock_rds


@pytest.fixture
def mock_boto3():
    """Create a complete mock for boto3."""
    with patch('boto3.client') as mock_client:
        mock_rds = MagicMock()
        mock_client.return_value = mock_rds
        yield mock_client, mock_rds


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
                'PromotionTier': 1
            },
            {
                'DBInstanceIdentifier': 'test-db-instance-2',
                'IsClusterWriter': False,
                'DBClusterParameterGroupStatus': 'in-sync',
                'PromotionTier': 1
            }
        ],
        'VpcSecurityGroups': [
            {
                'VpcSecurityGroupId': 'sg-12345678',
                'Status': 'active'
            }
        ],
        'DBClusterParameterGroup': 'default.aurora-mysql5.7',
        'DBSubnetGroup': 'default',
        'BackupRetentionPeriod': 7,
        'PreferredBackupWindow': '07:00-09:00',
        'PreferredMaintenanceWindow': 'sun:04:00-sun:05:00',
        'TagList': [
            {
                'Key': 'Environment',
                'Value': 'Production'
            }
        ]
    }


@pytest.fixture
def context():
    """Create a mock context for MCP tools."""
    mock_ctx = MagicMock()
    # Make error and log methods return coroutines
    mock_ctx.error = AsyncMock()
    mock_ctx.log = AsyncMock()
    return mock_ctx
