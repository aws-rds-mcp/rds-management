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

"""Tests for create_snapshot tool."""

import pytest
from awslabs.rds_management_mcp_server.tools.db_cluster.create_snapshot import (
    create_db_cluster_snapshot,
)
from botocore.exceptions import ClientError


class TestCreateDBClusterSnapshot:
    """Test cases for create_db_cluster_snapshot function."""

    @pytest.mark.asyncio
    async def test_create_snapshot_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful snapshot creation."""
        mock_rds_client.create_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': {
                'DBClusterSnapshotIdentifier': 'test-snapshot',
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'SnapshotType': 'manual',
                'PercentProgress': 0,
                'StorageEncrypted': False,
                'Port': 3306,
                'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot', db_cluster_identifier='test-cluster'
        )

        assert result['message'] == 'Successfully created DB cluster snapshot test-snapshot'
        assert result['formatted_snapshot']['snapshot_id'] == 'test-snapshot'
        assert 'DBClusterSnapshot' in result
        mock_asyncio_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_snapshot_with_tags(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test snapshot creation with tags."""
        mock_rds_client.create_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': {
                'DBClusterSnapshotIdentifier': 'test-snapshot',
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'TagList': [
                    {'Key': 'Environment', 'Value': 'Test'},
                    {'Key': 'Team', 'Value': 'DataEngineering'},
                ],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot',
            db_cluster_identifier='test-cluster',
            tags=[{'Environment': 'Test'}, {'Team': 'DataEngineering'}],
        )

        assert result['message'] == 'Successfully created DB cluster snapshot test-snapshot'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        # Check that tags are present and include our tags (MCP tags will also be added)
        assert 'Tags' in call_args
        tag_dict = {tag['Key']: tag['Value'] for tag in call_args['Tags']}
        assert 'Environment' in tag_dict
        assert tag_dict['Environment'] == 'Test'
        assert 'Team' in tag_dict
        assert tag_dict['Team'] == 'DataEngineering'
        assert 'mcp_server_version' in tag_dict  # MCP tags are always added
        assert 'created_by' in tag_dict

    @pytest.mark.asyncio
    async def test_create_snapshot_readonly_mode(self, mock_rds_context_readonly):
        """Test snapshot creation in readonly mode."""
        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot', db_cluster_identifier='test-cluster'
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_create_snapshot_client_error(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test snapshot creation with client error."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {
                    'Error': {
                        'Code': 'DBClusterSnapshotAlreadyExistsFault',
                        'Message': 'Snapshot already exists',
                    }
                },
                'CreateDBClusterSnapshot',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='existing-snapshot',
            db_cluster_identifier='test-cluster',
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'DBClusterSnapshotAlreadyExistsFault'

    @pytest.mark.asyncio
    async def test_create_snapshot_exception_handling(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test general exception handling."""

        async def async_error(func, **kwargs):
            raise Exception('General error')

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot', db_cluster_identifier='test-cluster'
        )

        assert isinstance(result, dict) and 'error' in result
        assert 'General error' in result['error']

    @pytest.mark.asyncio
    async def test_create_snapshot_minimal_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test snapshot creation with minimal parameters."""
        mock_rds_client.create_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': {
                'DBClusterSnapshotIdentifier': 'test-snapshot',
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot', db_cluster_identifier='test-cluster'
        )

        assert result['message'] == 'Successfully created DB cluster snapshot test-snapshot'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterSnapshotIdentifier'] == 'test-snapshot'
        assert call_args['DBClusterIdentifier'] == 'test-cluster'
        # Tags should not be set if not provided
        # MCP tags are always added, so Tags will be present
        assert 'Tags' in call_args
        tag_keys = [tag['Key'] for tag in call_args['Tags']]
        assert 'mcp_server_version' in tag_keys
        assert 'created_by' in tag_keys

    @pytest.mark.asyncio
    async def test_create_snapshot_non_existent_cluster(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test snapshot creation with a non-existent cluster."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'DB cluster not found'}},
                'CreateDBClusterSnapshot',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot',
            db_cluster_identifier='non-existent-cluster',
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'DBClusterNotFoundFault'

    @pytest.mark.asyncio
    async def test_create_snapshot_invalid_tags(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test snapshot creation with invalid tags."""

        async def async_error(func, **kwargs):
            raise ClientError(
                {'Error': {'Code': 'InvalidParameterValue', 'Message': 'Invalid tag key'}},
                'CreateDBClusterSnapshot',
            )

        mock_asyncio_thread.side_effect = async_error

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot',
            db_cluster_identifier='test-cluster',
            tags=[{'': 'EmptyKey'}],  # Invalid tag with empty key
        )

        assert isinstance(result, dict) and ('error' in result or 'error_code' in result)
        if 'error_code' in result:
            assert result['error_code'] == 'InvalidParameterValue'

    @pytest.mark.asyncio
    async def test_create_snapshot_result_formatting(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test the formatting of the snapshot information in the result."""
        mock_rds_client.create_db_cluster_snapshot.return_value = {
            'DBClusterSnapshot': {
                'DBClusterSnapshotIdentifier': 'test-snapshot',
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'SnapshotType': 'manual',
                'PercentProgress': 0,
                'StorageEncrypted': True,
                'Port': 3306,
                'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster_snapshot(
            db_cluster_snapshot_identifier='test-snapshot', db_cluster_identifier='test-cluster'
        )

        assert result['message'] == 'Successfully created DB cluster snapshot test-snapshot'
        assert result['formatted_snapshot']['snapshot_id'] == 'test-snapshot'
        assert result['formatted_snapshot']['cluster_id'] == 'test-cluster'
        assert result['formatted_snapshot']['status'] == 'creating'
        assert result['formatted_snapshot']['engine'] == 'aurora-mysql'
        assert result['formatted_snapshot']['engine_version'] == '5.7.mysql_aurora.2.10.2'
        # Full details are in the DBClusterSnapshot key
        assert result['DBClusterSnapshot']['SnapshotType'] == 'manual'
        assert result['DBClusterSnapshot']['PercentProgress'] == 0
        assert result['DBClusterSnapshot']['StorageEncrypted'] is True
        assert result['DBClusterSnapshot']['Port'] == 3306
