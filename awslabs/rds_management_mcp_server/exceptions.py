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

"""Custom exceptions for the RDS Management MCP Server."""


class RDSMCPException(Exception):
    """Base exception for RDS MCP Server."""

    pass


class ReadOnlyModeException(RDSMCPException):
    """Exception raised when a write operation is attempted in read-only mode."""

    def __init__(self, operation: str):
        """Initialize the ReadOnlyModeException.

        Args:
            operation: The name of the operation that was attempted
        """
        self.operation = operation
        super().__init__(
            f"Operation '{operation}' requires write access. The server is currently in read-only mode."
        )


class ConfirmationRequiredException(RDSMCPException):
    """Exception raised when a destructive operation requires confirmation."""

    def __init__(
        self, operation: str, confirmation_token: str, warning_message: str, impact: dict
    ):
        """Initialize the ConfirmationRequiredException.

        Args:
            operation: The name of the operation that requires confirmation
            confirmation_token: A unique token for confirming the operation
            warning_message: A message warning about the operation's impact
            impact: A dictionary containing details about the operation's impact
        """
        self.operation = operation
        self.confirmation_token = confirmation_token
        self.warning_message = warning_message
        self.impact = impact
        super().__init__(warning_message)
