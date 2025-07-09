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

"""awslabs RDS Management MCP Server implementation."""

import argparse
import awslabs.rds_management_mcp_server.resources  # noqa: F401 - imported for side effects to register resources
import awslabs.rds_management_mcp_server.tools  # noqa: F401 - imported for side effects to register tools
import os
import sys
from awslabs.rds_management_mcp_server.common.connection import RDSConnectionManager
from awslabs.rds_management_mcp_server.common.server import SERVER_VERSION, mcp
from awslabs.rds_management_mcp_server.context import Context
from loguru import logger


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs MCP server for comprehensive management of Amazon RDS databases'
    )
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument(
        '--max-items',
        default=100,
        type=int,
        help='The maximum number of items (logs, reports, etc.) to retrieve',
    )
    parser.add_argument(
        '--region',
        type=str,
        default=os.environ.get('AWS_REGION', 'us-east-1'),
        help='AWS region for RDS operations',
    )
    parser.add_argument(
        '--readonly',
        default='true',
        action=argparse.BooleanOptionalAction,
        help='Prevents the MCP server from performing mutating operations',
    )
    parser.add_argument('--profile', type=str, help='AWS profile to use for credentials')

    args = parser.parse_args()
    logger.remove()
    logger.add(sys.stderr, level=os.environ.get('FASTMCP_LOG_LEVEL', 'INFO'))

    # aws profile
    if args.profile:
        os.environ['AWS_PROFILE'] = args.profile

    # init connection manager and context
    readonly_mode = args.readonly
    RDSConnectionManager.initialize(readonly=readonly_mode, region=args.region)
    Context.initialize(readonly_mode, args.max_items)

    # config server port
    mcp.settings.port = args.port

    # logger info
    logger.info(f'Starting RDS Management MCP Server v{SERVER_VERSION}')
    logger.info(f'Region: {RDSConnectionManager.get_region()}')
    logger.info(f'Read-only mode: {RDSConnectionManager.is_readonly()}')
    if args.profile:
        logger.info(f'AWS Profile: {args.profile}')

    mcp.run()


if __name__ == '__main__':
    main()
