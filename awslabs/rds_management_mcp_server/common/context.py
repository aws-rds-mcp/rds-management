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

"""Context management for Amazon RDS Management MCP Server."""

from typing import Any, Dict, Optional


class RDSContext:
    """Context class for RDS Management MCP Server."""

    _readonly = True
    _max_items = 100
    _endpoint_url: Optional[str] = None

    @classmethod
    def initialize(
        cls, readonly: bool = True, max_items: int = 100, endpoint_url: Optional[str] = None
    ):
        """Initialize the context.

        Args:
            readonly (bool): Whether to run in readonly mode. Defaults to True.
            max_items (int): Maximum number of items returned from API responses. Defaults to 100.
            endpoint_url (Optional[str]): Custom endpoint URL for RDS API calls. Defaults to None.
        """
        cls._readonly = readonly
        cls._max_items = max_items
        cls._endpoint_url = endpoint_url

    @classmethod
    def readonly_mode(cls) -> bool:
        """Check if the server is running in readonly mode.

        Returns:
            True if readonly mode is enabled, False otherwise
        """
        return cls._readonly

    @classmethod
    def max_items(cls) -> int:
        """Get the maximum number of items returned from API responses.

        Returns:
            The maximum number of items returned from API responses
        """
        return cls._max_items

    @classmethod
    def endpoint_url(cls) -> Optional[str]:
        """Get the custom endpoint URL for RDS API calls.

        Returns:
            The custom endpoint URL, or None if using default AWS endpoints
        """
        return cls._endpoint_url

    @classmethod
    def get_pagination_config(cls) -> Dict[str, Any]:
        """Get the pagination config needed for API responses.

        Returns:
            The pagination config needed for API responses
        """
        return {
            'MaxItems': cls._max_items,
        }
