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

"""Decorators used by the RDS Management MCP Server."""

import json
from ..constants import (
    ERROR_CLIENT,
    ERROR_READONLY_MODE,
    ERROR_UNEXPECTED,
    STANDARD_CONFIRMATION_MESSAGE,
)
from ..context import Context
from ..exceptions import ConfirmationRequiredException, ReadOnlyModeException
from botocore.exceptions import ClientError
from functools import wraps
from inspect import iscoroutinefunction, signature
from loguru import logger
from mcp.server.fastmcp import Context as MCPContext
from typing import Any, Callable


def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions in MCP operations.

    Wraps the function in a try-catch block and returns any exceptions
    in a standardized error format.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that handles exceptions
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        try:
            if iscoroutinefunction(func):
                # If the decorated function is a coroutine, await it
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except Exception as error:
            if isinstance(error, ReadOnlyModeException):
                logger.warning(f'Operation blocked in readonly mode: {error.operation}')
                return json.dumps(
                    {
                        'error': ERROR_READONLY_MODE,
                        'operation': error.operation,
                        'message': str(error),
                    },
                    indent=2,
                )
            elif isinstance(error, ConfirmationRequiredException):
                logger.info(f'Confirmation required for operation: {error.operation}')
                return json.dumps(
                    {
                        'requires_confirmation': True,
                        'warning': error.warning_message,
                        'impact': error.impact,
                        'confirmation_token': error.confirmation_token,
                        'message': f'{error.warning_message}\n\nTo confirm, please call this function again with the confirmation_token parameter set to this token.',
                    },
                    indent=2,
                )
            elif isinstance(error, ClientError):
                error_code = error.response['Error']['Code']
                error_message = error.response['Error']['Message']
                logger.error(f'Failed with client error {error_code}: {error_message}')

                # JSON error response
                return json.dumps(
                    {
                        'error': ERROR_CLIENT.format(error_code),
                        'error_code': error_code,
                        'error_message': error_message,
                        'operation': func.__name__,
                    },
                    indent=2,
                )
            else:
                logger.exception(f'Failed with unexpected error: {str(error)}')

                # general exceptions
                return json.dumps(
                    {
                        'error': ERROR_UNEXPECTED.format(str(error)),
                        'error_type': type(error).__name__,
                        'error_message': str(error),
                        'operation': func.__name__,
                    },
                    indent=2,
                )

    return wrapper


def readonly_check(func: Callable) -> Callable:
    """Decorator to check if operation is allowed in readonly mode.

    This decorator automatically checks if the server is in readonly mode
    and blocks write operations. It determines the operation type from
    the function name.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that checks readonly mode
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        ctx = kwargs.get('ctx')
        if not ctx:
            for arg in args:
                if isinstance(arg, MCPContext):
                    ctx = arg
                    break

        func_name = func.__name__.lower()
        is_read_operation = any(
            func_name.startswith(prefix) for prefix in ['describe', 'list', 'get', 'read']
        )

        if not is_read_operation and Context.readonly_mode():
            raise ReadOnlyModeException(func.__name__)

        if iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


def require_confirmation(operation_type: str) -> Callable:
    """Decorator to require confirmation for destructive operations.

    This decorator handles the confirmation flow for operations that
    require explicit user confirmation before proceeding. It uses a
    standardized confirmation message from constants.py.

    Args:
        operation_type: The type of operation (e.g., 'delete_db_cluster')

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            from ..common.utils import (
                add_pending_operation,
                get_operation_impact,
                get_pending_operation,
                remove_pending_operation,
            )

            confirmation_token = kwargs.get('confirmation_token')

            if not confirmation_token:
                sig = signature(func)
                params = {}
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                for param_name, param_value in bound_args.arguments.items():
                    if param_name not in ['ctx', 'confirmation_token']:
                        params[param_name] = param_value

                impact = get_operation_impact(operation_type)

                resource_type = 'resource'
                identifier = 'unknown'

                if 'db_cluster_identifier' in params:
                    resource_type = 'DB cluster'
                    identifier = params['db_cluster_identifier']
                elif 'db_instance_identifier' in params:
                    resource_type = 'DB instance'
                    identifier = params['db_instance_identifier']
                elif 'db_snapshot_identifier' in params:
                    resource_type = 'DB snapshot'
                    identifier = params['db_snapshot_identifier']

                operation_name = operation_type.replace('_', ' ').title()

                warning_message = STANDARD_CONFIRMATION_MESSAGE.format(
                    operation=operation_name,
                    resource_type=resource_type,
                    identifier=identifier,
                    risk_level=impact.get('risk', 'Unknown'),
                )

                token = add_pending_operation(operation_type, params)
                raise ConfirmationRequiredException(
                    operation=operation_type,
                    confirmation_token=token,
                    warning_message=warning_message,
                    impact=impact,
                )
            pending_op = get_pending_operation(confirmation_token)
            if not pending_op:
                return {
                    'error': 'Invalid or expired confirmation token. Please request a new token by calling this function without a confirmation_token parameter.'
                }
            op_type, stored_params, _ = pending_op

            if op_type != operation_type:
                return {
                    'error': f'Invalid operation type. Expected "{operation_type}", got "{op_type}".'
                }

            sig = signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for key in ['db_cluster_identifier', 'db_instance_identifier']:
                if key in stored_params and key in bound_args.arguments:
                    if stored_params[key] != bound_args.arguments[key]:
                        return {
                            'error': f'Parameter mismatch. The confirmation token is for a different {key}.'
                        }

            remove_pending_operation(confirmation_token)

            if iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator
