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

"""Tests for connection module."""

import pytest
from awslabs.rds_management_mcp_server.common.connection import RDSConnectionManager
from unittest.mock import MagicMock, patch


class TestRDSConnectionManager:
    """Test cases for RDSConnectionManager class."""

    def setup_method(self):
        """Reset the connection manager before each test."""
        RDSConnectionManager._client = None

    def test_get_connection_creates_client(self):
        """Test that get_connection creates a client."""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            result = RDSConnectionManager.get_connection()

            assert result is mock_client
            mock_session.return_value.client.assert_called_once_with(
                service_name='rds', config=mock_session.return_value.client.call_args[1]['config']
            )

    def test_get_connection_reuses_client(self):
        """Test that get_connection reuses existing client."""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            # First call should create client
            result1 = RDSConnectionManager.get_connection()
            # Second call should reuse client
            result2 = RDSConnectionManager.get_connection()

            assert result1 is result2
            mock_session.return_value.client.assert_called_once_with(
                service_name='rds', config=mock_session.return_value.client.call_args[1]['config']
            )

    def test_get_connection_with_region(self):
        """Test get_connection with specific region."""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-west-2'}):
                result = RDSConnectionManager.get_connection()

                assert result is mock_client
                mock_session.return_value.client.assert_called_once_with(
                    service_name='rds',
                    config=mock_session.return_value.client.call_args[1]['config'],
                )

    def test_get_connection_handles_exception(self):
        """Test get_connection handles boto3 exceptions."""
        with patch('boto3.Session') as mock_session:
            mock_session.return_value.client.side_effect = Exception('Connection failed')

            with pytest.raises(Exception):
                RDSConnectionManager.get_connection()

    def test_connection_manager_is_singleton(self):
        """Test that connection manager maintains singleton pattern."""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            # Multiple calls should return the same client
            client1 = RDSConnectionManager.get_connection()
            client2 = RDSConnectionManager.get_connection()
            client3 = RDSConnectionManager.get_connection()

            assert client1 is client2 is client3
            mock_session.return_value.client.assert_called_once()

    def test_reset_connection(self):
        """Test that connection can be reset."""
        with patch('boto3.Session') as mock_session:
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            mock_session.return_value.client.side_effect = [mock_client1, mock_client2]

            # First connection
            client1 = RDSConnectionManager.get_connection()
            assert client1 is mock_client1

            # Reset connection
            RDSConnectionManager._client = None

            # Second connection should create new client
            client2 = RDSConnectionManager.get_connection()
            assert client2 is mock_client2
            assert client1 is not client2

            assert mock_session.return_value.client.call_count == 2
