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

"""Tests for utils module."""

from awslabs.rds_management_mcp_server.common.utils import (
    add_mcp_tags,
    convert_datetime_to_string,
    format_rds_api_response,
    handle_paginated_aws_api_call,
)
from unittest.mock import MagicMock


class TestFormatRDSApiResponse:
    """Test cases for format_rds_api_response function."""

    def test_format_response_with_response_metadata(self):
        """Test formatting response with ResponseMetadata."""
        response = {
            'DBCluster': {'DBClusterIdentifier': 'test-cluster'},
            'ResponseMetadata': {
                'RequestId': 'test-request-id',
                'HTTPStatusCode': 200,
                'HTTPHeaders': {'content-type': 'application/json'},
                'RetryAttempts': 0,
            },
        }

        result = format_rds_api_response(response)

        assert 'ResponseMetadata' not in result
        assert result['DBCluster']['DBClusterIdentifier'] == 'test-cluster'

    def test_format_response_without_response_metadata(self):
        """Test formatting response without ResponseMetadata."""
        response = {'DBCluster': {'DBClusterIdentifier': 'test-cluster'}}

        result = format_rds_api_response(response)

        assert result['DBCluster']['DBClusterIdentifier'] == 'test-cluster'

    def test_format_response_empty_dict(self):
        """Test formatting empty response."""
        response = {}

        result = format_rds_api_response(response)

        assert result == {}

    def test_format_response_only_response_metadata(self):
        """Test formatting response with only ResponseMetadata."""
        response = {'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 200}}

        result = format_rds_api_response(response)

        assert result == {}


class TestAddMCPTags:
    """Test cases for add_mcp_tags function."""

    def test_add_mcp_tags_to_empty_params(self):
        """Test adding MCP tags to empty parameters."""
        params = {}

        result = add_mcp_tags(params)

        assert 'Tags' in result
        assert len(result['Tags']) >= 2

        tag_keys = [tag['Key'] for tag in result['Tags']]
        assert 'mcp_server_version' in tag_keys
        assert 'created_by' in tag_keys

    def test_add_mcp_tags_to_existing_params(self):
        """Test adding MCP tags to existing parameters."""
        params = {'DBClusterIdentifier': 'test-cluster', 'Engine': 'aurora-mysql'}

        result = add_mcp_tags(params)

        assert result['DBClusterIdentifier'] == 'test-cluster'
        assert result['Engine'] == 'aurora-mysql'
        assert 'Tags' in result
        assert len(result['Tags']) >= 2

    def test_add_mcp_tags_with_existing_tags(self):
        """Test adding MCP tags to parameters with existing tags."""
        params = {
            'DBClusterIdentifier': 'test-cluster',
            'Tags': [
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Team', 'Value': 'DataEngineering'},
            ],
        }

        result = add_mcp_tags(params)

        assert result['DBClusterIdentifier'] == 'test-cluster'
        assert len(result['Tags']) >= 4  # 2 existing + 2 MCP tags

        tag_keys = [tag['Key'] for tag in result['Tags']]
        assert 'Environment' in tag_keys
        assert 'Team' in tag_keys
        assert 'mcp_server_version' in tag_keys
        assert 'created_by' in tag_keys

    def test_add_mcp_tags_preserves_original_params(self):
        """Test that adding MCP tags doesn't modify original parameters."""
        original_params = {'DBClusterIdentifier': 'test-cluster', 'Engine': 'aurora-mysql'}
        params = original_params.copy()

        result = add_mcp_tags(params)

        # Original should be unchanged
        assert 'Tags' not in original_params
        # Result should have tags
        assert 'Tags' in result


class TestConvertDatetimeToString:
    """Test cases for convert_datetime_to_string function."""

    def test_convert_datetime_to_string_with_datetime(self):
        """Test converting datetime object to string."""
        import datetime

        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        result = convert_datetime_to_string(dt)
        assert result == '2023-01-01T12:00:00'

    def test_convert_datetime_to_string_with_dict(self):
        """Test converting dictionary containing datetime objects."""
        import datetime

        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        obj = {'timestamp': dt, 'name': 'test'}
        result = convert_datetime_to_string(obj)
        assert result['timestamp'] == '2023-01-01T12:00:00'
        assert result['name'] == 'test'

    def test_convert_datetime_to_string_with_list(self):
        """Test converting list containing datetime objects."""
        import datetime

        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        obj = [dt, 'test', 42]
        result = convert_datetime_to_string(obj)
        assert result[0] == '2023-01-01T12:00:00'
        assert result[1] == 'test'
        assert result[2] == 42

    def test_convert_datetime_to_string_with_other_types(self):
        """Test converting other types returns unchanged."""
        assert convert_datetime_to_string('string') == 'string'
        assert convert_datetime_to_string(42) == 42
        assert convert_datetime_to_string(None) is None


class TestHandlePaginatedAwsApiCall:
    """Test cases for handle_paginated_aws_api_call function."""

    def test_handle_paginated_aws_api_call_single_page(self):
        """Test handling single page response."""
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator

        # Mock page iterator
        mock_page_iterator = [
            {
                'DBClusters': [
                    {'DBClusterIdentifier': 'cluster-1'},
                    {'DBClusterIdentifier': 'cluster-2'},
                ]
            }
        ]
        mock_paginator.paginate.return_value = mock_page_iterator

        def format_function(item):
            return {'cluster_id': item['DBClusterIdentifier']}

        result = handle_paginated_aws_api_call(
            client=mock_client,
            paginator_name='describe_db_clusters',
            operation_parameters={'MaxItems': 100},
            format_function=format_function,
            result_key='DBClusters',
        )

        assert len(result) == 2
        assert result[0]['cluster_id'] == 'cluster-1'
        assert result[1]['cluster_id'] == 'cluster-2'
        mock_client.get_paginator.assert_called_once_with('describe_db_clusters')

    def test_handle_paginated_aws_api_call_multiple_pages(self):
        """Test handling multiple page response."""
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator

        # Mock page iterator with multiple pages
        mock_page_iterator = [
            {'DBClusters': [{'DBClusterIdentifier': 'cluster-1'}]},
            {'DBClusters': [{'DBClusterIdentifier': 'cluster-2'}]},
        ]
        mock_paginator.paginate.return_value = mock_page_iterator

        def format_function(item):
            return {'cluster_id': item['DBClusterIdentifier']}

        result = handle_paginated_aws_api_call(
            client=mock_client,
            paginator_name='describe_db_clusters',
            operation_parameters={},
            format_function=format_function,
            result_key='DBClusters',
        )

        assert len(result) == 2
        assert result[0]['cluster_id'] == 'cluster-1'
        assert result[1]['cluster_id'] == 'cluster-2'

    def test_handle_paginated_aws_api_call_empty_result(self):
        """Test handling empty result."""
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator

        # Mock empty page iterator
        mock_page_iterator = [{'DBClusters': []}]
        mock_paginator.paginate.return_value = mock_page_iterator

        def format_function(item):
            return {'cluster_id': item['DBClusterIdentifier']}

        result = handle_paginated_aws_api_call(
            client=mock_client,
            paginator_name='describe_db_clusters',
            operation_parameters={},
            format_function=format_function,
            result_key='DBClusters',
        )

        assert len(result) == 0
