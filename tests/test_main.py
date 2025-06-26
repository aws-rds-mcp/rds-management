# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

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

"""Tests for RDS Management MCP Server main module."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from awslabs.rds_management_mcp_server.server import main


class TestMain:
    """Tests for main entry point."""

    @patch('awslabs.rds_management_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.rds-management-mcp-server', '--region', 'us-east-1'])
    def test_main_default(self, mock_run):
        """Test main function with default arguments."""
        main()
        mock_run.assert_called_once()

    @patch('awslabs.rds_management_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.rds-management-mcp-server', '--region', 'us-east-1'])
    def test_module_execution(self, mock_run):
        """Test the module can be executed as a script."""
        with patch.object(sys, 'exit'):
            main()
        mock_run.assert_called_once()
