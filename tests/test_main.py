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

"""Tests for main module."""

import pytest
from awslabs.rds_management_mcp_server.main import main
from unittest.mock import patch


class TestMain:
    """Test cases for main function."""

    @pytest.mark.asyncio
    async def test_main_success(self):
        """Test successful main function execution."""
        with patch('awslabs.rds_management_mcp_server.main.mcp.run') as mock_run:
            with patch('sys.argv', ['test']):
                main()

            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_args(self):
        """Test main function with command line arguments."""
        with patch('awslabs.rds_management_mcp_server.main.mcp.run') as mock_run:
            with patch('sys.argv', ['test', '--readonly']):
                main()

            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_exception_handling(self):
        """Test main function exception handling."""
        with patch('awslabs.rds_management_mcp_server.main.mcp.run') as mock_run:
            mock_run.side_effect = Exception('Test exception')

            with patch('sys.argv', ['test']):
                with pytest.raises(Exception, match='Test exception'):
                    main()
