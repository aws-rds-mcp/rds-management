"""Tests for db_instance utils."""

from awslabs.rds_management_mcp_server.tools.db_instance.utils import format_instance_info


class TestDBInstanceUtils:
    """Test DB instance utility functions."""

    def test_format_instance_info_basic(self):
        """Test basic format_instance_info functionality."""
        # Test with minimal data
        instance_data = {'DBInstanceIdentifier': 'test-instance', 'DBInstanceStatus': 'available'}
        result = format_instance_info(instance_data)
        assert isinstance(result, dict)
        assert result['instance_id'] == 'test-instance'
        assert result['status'] == 'available'

    def test_format_instance_info_with_empty_dict(self):
        """Test format_instance_info with empty dict."""
        result = format_instance_info({})
        assert isinstance(result, dict)
        assert result['instance_id'] is None
        assert result['status'] is None

    def test_format_instance_info_without_endpoint(self):
        """Test format_instance_info without endpoint."""
        instance_data = {'DBInstanceIdentifier': 'test'}
        result = format_instance_info(instance_data)
        assert isinstance(result, dict)
        assert result['endpoint'] == {}

    def test_format_instance_info_with_tags(self):
        """Test format_instance_info with tags."""
        instance_data = {
            'DBInstanceIdentifier': 'test',
            'TagList': [{'Key': 'Env', 'Value': 'Test'}],
        }
        result = format_instance_info(instance_data)
        assert isinstance(result, dict)
        assert result['tags'] == {'Env': 'Test'}

    def test_format_instance_info_with_pending_values(self):
        """Test format_instance_info with pending values."""
        instance_data = {
            'DBInstanceIdentifier': 'test',
            'PendingModifiedValues': {'AllocatedStorage': 100},
        }
        result = format_instance_info(instance_data)
        assert isinstance(result, dict)
        # Note: format_instance_info doesn't handle PendingModifiedValues, so we just check basic functionality

    def test_format_instance_info_with_read_replicas(self):
        """Test format_instance_info with read replicas."""
        instance_data = {
            'DBInstanceIdentifier': 'test',
            'ReadReplicaDBInstanceIdentifiers': ['replica-1'],
        }
        result = format_instance_info(instance_data)
        assert isinstance(result, dict)
        # Note: format_instance_info doesn't handle ReadReplicaDBInstanceIdentifiers, so we just check basic functionality
