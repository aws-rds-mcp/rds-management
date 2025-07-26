"""Tests for list_instances resource."""

import pytest
from awslabs.rds_management_mcp_server.resources.db_instance.list_instances import list_instances
from unittest.mock import MagicMock


class TestListInstances:
    """Test cases for list_instances function."""

    @pytest.mark.asyncio
    async def test_list_instances_success(
        self, mock_rds_client, mock_asyncio_thread, sample_db_instance
    ):
        """Test successful listing of instances."""
        # Mock the paginator
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBInstances': [sample_db_instance]}]

        result = await list_instances()

        assert result.instances
        assert result.count == 1
        assert result.instances[0].instance_id == 'test-db-instance'
        assert result.instances[0].status == 'available'
        assert result.instances[0].engine == 'mysql'

    @pytest.mark.asyncio
    async def test_list_instances_multiple(
        self, mock_rds_client, mock_asyncio_thread, sample_db_instance
    ):
        """Test listing multiple instances."""
        instance2 = sample_db_instance.copy()
        instance2['DBInstanceIdentifier'] = 'test-db-instance-2'

        # Mock the paginator
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBInstances': [sample_db_instance, instance2]}]

        result = await list_instances()

        assert result.count == 2
        assert len(result.instances) == 2
        assert result.instances[0].instance_id == 'test-db-instance'
        assert result.instances[1].instance_id == 'test-db-instance-2'

    @pytest.mark.asyncio
    async def test_list_instances_empty(self, mock_rds_client, mock_asyncio_thread):
        """Test listing when no instances exist."""
        # Mock the paginator
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBInstances': []}]

        result = await list_instances()

        assert len(result.instances) == 0
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_list_instances_error(self, mock_rds_client, mock_asyncio_thread):
        """Test error handling in list instances."""
        mock_rds_client.get_paginator.side_effect = Exception('Test error')

        result = await list_instances()

        # The handle_exceptions decorator should convert exceptions to dict with error key
        assert isinstance(result, dict) and 'error' in result
        assert 'Test error' in result['error']

    @pytest.mark.asyncio
    async def test_list_instances_with_tags(
        self, mock_rds_client, mock_asyncio_thread, sample_db_instance
    ):
        """Test listing instances includes tags."""
        # Mock the paginator
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBInstances': [sample_db_instance]}]

        result = await list_instances()

        assert result.instances[0].tag_list
        assert result.instances[0].tag_list['Environment'] == 'Test'
