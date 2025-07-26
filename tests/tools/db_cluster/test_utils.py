"""Tests for db_cluster utils."""

from awslabs.rds_management_mcp_server.tools.db_cluster.utils import format_cluster_info


class TestDBClusterUtils:
    """Test cases for DB cluster utility functions."""

    def test_format_cluster_info_complete(self, sample_db_cluster):
        """Test formatting a complete DB cluster."""
        result = format_cluster_info(sample_db_cluster)

        assert result['cluster_id'] == 'test-db-cluster'
        assert result['status'] == 'available'
        assert result['engine'] == 'aurora-mysql'
        assert result['engine_version'] == '5.7.mysql_aurora.2.10.2'
        assert result['endpoint'] == 'test-db-cluster.cluster-abc123.us-east-1.rds.amazonaws.com'
        assert (
            result['reader_endpoint']
            == 'test-db-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com'
        )
        assert result['multi_az'] is True
        assert len(result['members']) == 2
        assert result['members'][0]['instance_id'] == 'test-db-instance-1'
        assert result['members'][0]['is_writer'] is True
        assert result['backup_retention'] == 7
        assert result['preferred_backup_window'] == '07:00-09:00'
        assert result['preferred_maintenance_window'] == 'sun:04:00-sun:05:00'
        assert len(result['vpc_security_groups']) == 1
        assert result['vpc_security_groups'][0]['id'] == 'sg-12345678'
        assert result['tags']['Environment'] == 'Production'

    def test_format_cluster_info_minimal(self):
        """Test formatting a minimal DB cluster."""
        minimal_cluster = {
            'DBClusterIdentifier': 'minimal-cluster',
            'Status': 'creating',
            'Engine': 'aurora-postgresql',
        }

        result = format_cluster_info(minimal_cluster)

        assert result['cluster_id'] == 'minimal-cluster'
        assert result['status'] == 'creating'
        assert result['engine'] == 'aurora-postgresql'
        assert result['endpoint'] is None
        assert result['reader_endpoint'] is None
        assert result['members'] == []
        assert result['vpc_security_groups'] == []
        assert result['tags'] == {}

    def test_format_cluster_info_with_empty_dict(self):
        """Test formatting with empty dict input."""
        result = format_cluster_info({})

        assert result['cluster_id'] is None
        assert result['status'] is None
        assert result['engine'] is None
        assert result['members'] == []
        assert result['vpc_security_groups'] == []
        assert result['tags'] == {}

    def test_format_cluster_info_with_tags(self, sample_db_cluster):
        """Test formatting DB cluster includes tags."""
        result = format_cluster_info(sample_db_cluster)

        assert 'TagList' in sample_db_cluster
        assert result['tags']['Environment'] == 'Production'

    def test_format_cluster_info_without_tags(self):
        """Test formatting DB cluster without tags."""
        cluster_without_tags = {
            'DBClusterIdentifier': 'cluster-no-tags',
            'Status': 'available',
            'Engine': 'aurora-mysql',
        }

        result = format_cluster_info(cluster_without_tags)
        assert result['tags'] == {}

    def test_format_cluster_info_with_multiple_members(self):
        """Test formatting DB cluster with multiple members."""
        cluster_with_members = {
            'DBClusterIdentifier': 'multi-member-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'DBClusterMembers': [
                {
                    'DBInstanceIdentifier': 'instance-1',
                    'IsClusterWriter': True,
                    'DBClusterParameterGroupStatus': 'in-sync',
                },
                {
                    'DBInstanceIdentifier': 'instance-2',
                    'IsClusterWriter': False,
                    'DBClusterParameterGroupStatus': 'in-sync',
                },
                {
                    'DBInstanceIdentifier': 'instance-3',
                    'IsClusterWriter': False,
                    'DBClusterParameterGroupStatus': 'pending-reboot',
                },
            ],
        }

        result = format_cluster_info(cluster_with_members)
        assert len(result['members']) == 3
        assert result['members'][0]['instance_id'] == 'instance-1'
        assert result['members'][0]['is_writer'] is True
        assert result['members'][2]['status'] == 'pending-reboot'

    def test_format_cluster_info_with_multiple_security_groups(self):
        """Test formatting DB cluster with multiple security groups."""
        cluster_with_sgs = {
            'DBClusterIdentifier': 'multi-sg-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'VpcSecurityGroups': [
                {'VpcSecurityGroupId': 'sg-11111111', 'Status': 'active'},
                {'VpcSecurityGroupId': 'sg-22222222', 'Status': 'active'},
                {'VpcSecurityGroupId': 'sg-33333333', 'Status': 'adding'},
            ],
        }

        result = format_cluster_info(cluster_with_sgs)
        assert len(result['vpc_security_groups']) == 3
        assert result['vpc_security_groups'][0]['id'] == 'sg-11111111'
        assert result['vpc_security_groups'][2]['status'] == 'adding'
