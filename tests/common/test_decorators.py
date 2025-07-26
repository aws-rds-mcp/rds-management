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

"""Tests for common decorators."""

import pytest
from awslabs.rds_management_mcp_server.common.decorators.handle_exceptions import handle_exceptions
from awslabs.rds_management_mcp_server.common.decorators.readonly_check import readonly_check
from awslabs.rds_management_mcp_server.common.decorators.require_confirmation import (
    require_confirmation,
)


class TestHandleExceptions:
    """Test cases for handle_exceptions decorator."""

    @pytest.mark.asyncio
    async def test_handle_exceptions_success(self):
        """Test handle_exceptions with successful function call."""

        @handle_exceptions
        async def test_func():
            return {'status': 'success'}

        result = await test_func()
        assert result == {'status': 'success'}

    @pytest.mark.asyncio
    async def test_handle_exceptions_with_exception(self):
        """Test handle_exceptions with exception."""

        @handle_exceptions
        async def test_func():
            raise ValueError('Test error')

        result = await test_func()
        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'Test error' in result['error_message']

    @pytest.mark.asyncio
    async def test_handle_exceptions_with_client_error(self):
        """Test handle_exceptions with client error."""
        from botocore.exceptions import ClientError

        @handle_exceptions
        async def test_func():
            raise ClientError(
                error_response={
                    'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}
                },
                operation_name='CreateDBCluster',
            )

        result = await test_func()
        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert result['error_message'] == 'Invalid parameter'


class TestReadonlyCheck:
    """Test cases for readonly_check decorator."""

    @pytest.mark.asyncio
    async def test_readonly_check_allowed(self, mock_rds_context_allowed):
        """Test readonly_check when operations are allowed."""

        @readonly_check
        async def test_func():
            return {'status': 'success'}

        result = await test_func()
        assert result == {'status': 'success'}

    @pytest.mark.asyncio
    async def test_readonly_check_blocked(self, mock_rds_context_readonly):
        """Test readonly_check when operations are blocked."""

        @readonly_check
        async def test_func():
            return {'status': 'success'}

        result = await test_func()
        assert hasattr(result, 'error') or (isinstance(result, dict) and 'error' in result)
        assert 'read-only mode' in result['message']


class TestRequireConfirmation:
    """Test cases for require_confirmation decorator."""

    @pytest.mark.asyncio
    async def test_require_confirmation_with_token(self):
        """Test require_confirmation with valid token."""

        @require_confirmation('DeleteDBCluster')
        async def test_func(db_cluster_identifier, confirmation_token=None):
            return {'status': 'success'}

        # First get a token
        result1 = await test_func(db_cluster_identifier='test-resource')
        token = result1['confirmation_token']

        # Then use the token
        result2 = await test_func(db_cluster_identifier='test-resource', confirmation_token=token)
        assert result2 == {'status': 'success'}

    @pytest.mark.asyncio
    async def test_require_confirmation_without_token(self):
        """Test require_confirmation without token."""

        @require_confirmation('DeleteDBCluster')
        async def test_func(db_cluster_identifier):
            return {'status': 'success'}

        result = await test_func(db_cluster_identifier='test-resource')
        assert result['requires_confirmation'] is True
        assert 'warning' in result
        assert 'confirmation_token' in result
        assert result['confirmation_token'] is not None

    @pytest.mark.asyncio
    async def test_require_confirmation_with_empty_token(self):
        """Test require_confirmation with empty token."""

        @require_confirmation('DeleteDBCluster')
        async def test_func(db_cluster_identifier, confirmation_token=None):
            return {'status': 'success'}

        # Empty string is treated as no token, so it should generate a new confirmation token
        result = await test_func(db_cluster_identifier='test-resource', confirmation_token='')
        assert result['requires_confirmation'] is True
        assert 'warning' in result
        assert 'confirmation_token' in result
        assert result['confirmation_token'] is not None
