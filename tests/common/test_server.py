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

"""Tests for server module."""

import pytest
from awslabs.rds_management_mcp_server.common.server import mcp


class TestMCPServer:
    """Test cases for MCP server setup."""

    def test_mcp_server_exists(self):
        """Test that MCP server instance exists."""
        assert mcp is not None
        assert hasattr(mcp, 'tool')
        assert hasattr(mcp, 'resource')

    def test_mcp_server_tool_decorator(self):
        """Test MCP server tool decorator."""
        # Test that tool decorator is callable
        assert callable(mcp.tool)

    def test_mcp_server_resource_decorator(self):
        """Test MCP server resource decorator."""
        # Test that resource decorator is callable
        assert callable(mcp.resource)

    def test_mcp_server_configuration(self):
        """Test MCP server configuration."""
        # Test server name
        assert mcp.name == 'awslabs.rds-management-mcp-server'
        # Test server has required attributes
        assert hasattr(mcp, 'instructions')
        assert hasattr(mcp, 'dependencies')

    @pytest.mark.asyncio
    async def test_mcp_server_tool_registration(self):
        """Test tool registration on MCP server."""

        @mcp.tool(name='test_tool', description='Test tool')
        def test_tool():
            return 'test'

        # Tool should be registered
        tools = await mcp.list_tools()
        assert 'test_tool' in [tool.name for tool in tools]

    @pytest.mark.asyncio
    async def test_mcp_server_resource_registration(self):
        """Test resource registration on MCP server."""

        @mcp.resource('test://resource')
        def test_resource():
            return 'test'

        # Resource should be registered
        resources = await mcp.list_resources()
        assert any('test://resource' in str(resource) for resource in resources)

    @pytest.mark.asyncio
    async def test_mcp_server_handles_multiple_tools(self):
        """Test MCP server handles multiple tool registrations."""

        @mcp.tool(name='test_tool_1', description='Test tool 1')
        def test_tool_1():
            return 'test1'

        @mcp.tool(name='test_tool_2', description='Test tool 2')
        def test_tool_2():
            return 'test2'

        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        assert 'test_tool_1' in tool_names
        assert 'test_tool_2' in tool_names

    @pytest.mark.asyncio
    async def test_mcp_server_handles_multiple_resources(self):
        """Test MCP server handles multiple resource registrations."""

        @mcp.resource('test://resource1')
        def test_resource_1():
            return 'test1'

        @mcp.resource('test://resource2')
        def test_resource_2():
            return 'test2'

        resources = await mcp.list_resources()
        assert len(resources) >= 2
