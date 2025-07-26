"""Tests for modify_instance tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_instance.modify_instance import modify_db_instance


class TestModifyInstance:
    """Test cases for modify_db_instance function."""

    @pytest.mark.asyncio
    async def test_modify_instance_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test successful instance modification."""
        mock_rds_client.modify_db_instance.return_value = {'DBInstance': sample_db_instance}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance(
            db_instance_identifier='test-instance',
            db_instance_class='db.t3.small',
            apply_immediately=True,
        )

        assert result['message'] == 'Successfully modified DB instance test-instance'
        assert result['formatted_instance']['instance_id'] == 'test-db-instance'
        assert 'DBInstance' in result

    @pytest.mark.asyncio
    async def test_modify_instance_readonly_mode(self, mock_rds_context_readonly):
        """Test instance modification in readonly mode."""
        result = await modify_db_instance(
            db_instance_identifier='test-instance', db_instance_class='db.t3.small'
        )

        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']

    @pytest.mark.asyncio
    async def test_modify_instance_with_storage_options(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test instance modification with storage options."""
        mock_rds_client.modify_db_instance.return_value = {'DBInstance': sample_db_instance}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance(
            db_instance_identifier='test-instance',
            allocated_storage=100,
            storage_type='gp3',
            apply_immediately=False,
        )

        assert result['message'] == 'Successfully modified DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['AllocatedStorage'] == 100
        assert call_args['StorageType'] == 'gp3'
        assert call_args['ApplyImmediately'] is False

    @pytest.mark.asyncio
    async def test_modify_instance_with_security_groups(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test instance modification with security groups."""
        mock_rds_client.modify_db_instance.return_value = {'DBInstance': sample_db_instance}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance(
            db_instance_identifier='test-instance',
            vpc_security_group_ids=['sg-12345', 'sg-67890'],
            backup_retention_period=14,
        )

        assert result['message'] == 'Successfully modified DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['VpcSecurityGroupIds'] == ['sg-12345', 'sg-67890']
        assert call_args['BackupRetentionPeriod'] == 14

    @pytest.mark.asyncio
    async def test_modify_instance_with_maintenance_windows(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test instance modification with maintenance windows."""
        mock_rds_client.modify_db_instance.return_value = {'DBInstance': sample_db_instance}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance(
            db_instance_identifier='test-instance',
            preferred_backup_window='03:00-04:00',
            preferred_maintenance_window='sun:04:00-sun:05:00',
        )

        assert result['message'] == 'Successfully modified DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['PreferredBackupWindow'] == '03:00-04:00'
        assert call_args['PreferredMaintenanceWindow'] == 'sun:04:00-sun:05:00'

    @pytest.mark.asyncio
    async def test_modify_instance_with_version_upgrade(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread, sample_db_instance
    ):
        """Test instance modification with version upgrade."""
        mock_rds_client.modify_db_instance.return_value = {'DBInstance': sample_db_instance}

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_instance(
            db_instance_identifier='test-instance',
            engine_version='8.0.36',
            allow_major_version_upgrade=True,
            auto_minor_version_upgrade=False,
        )

        assert result['message'] == 'Successfully modified DB instance test-instance'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['EngineVersion'] == '8.0.36'
        assert call_args['AllowMajorVersionUpgrade'] is True
        assert call_args['AutoMinorVersionUpgrade'] is False
