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

"""Constants for RDS Management MCP Server."""

# Version
MCP_SERVER_VERSION = '0.1.0'

# Error Messages
ERROR_READONLY_MODE = (
    'This operation requires write access. The server is currently in read-only mode.'
)
ERROR_MISSING_PARAMS = 'Missing required parameters: {}'
ERROR_INVALID_PARAMS = 'Invalid parameters: {}'
ERROR_CLIENT = 'Client error: {}'
ERROR_UNEXPECTED = 'Unexpected error: {}'
ERROR_NOT_FOUND = 'Resource not found: {}'
ERROR_OPERATION_FAILED = 'Operation failed: {}'

# Success Messages
SUCCESS_CREATED = 'Successfully created {}'
SUCCESS_MODIFIED = 'Successfully modified {}'
SUCCESS_DELETED = 'Successfully deleted {}'
SUCCESS_STARTED = 'Successfully started {}'
SUCCESS_STOPPED = 'Successfully stopped {}'
SUCCESS_REBOOTED = 'Successfully rebooted {}'
SUCCESS_RESTORED = 'Successfully restored {}'
SUCCESS_FAILOVER = 'Successfully initiated failover for {}'
SUCCESS_RESET = 'Successfully reset {}'

# Operation Risk Levels
RISK_LOW = 'low'
RISK_HIGH = 'high'
RISK_CRITICAL = 'critical'

# Operation Categories
OPERATION_READ = 'read'
OPERATION_CREATE = 'create'
OPERATION_MODIFY = 'modify'
OPERATION_DELETE = 'delete'
OPERATION_STATE_CHANGE = 'state_change'

# AWS RDS Engine Types
ENGINE_AURORA = 'aurora'
ENGINE_AURORA_MYSQL = 'aurora-mysql'
ENGINE_AURORA_POSTGRESQL = 'aurora-postgresql'
ENGINE_MYSQL = 'mysql'
ENGINE_POSTGRESQL = 'postgres'
ENGINE_MARIADB = 'mariadb'
ENGINE_ORACLE = 'oracle'
ENGINE_SQLSERVER = 'sqlserver'

# Default Values
DEFAULT_BACKUP_RETENTION_PERIOD = 7

# Engine port mapping
ENGINE_PORT_MAP = {
    'aurora': 3306,
    'aurora-mysql': 3306,
    'aurora-postgresql': 5432,
    'mysql': 3306,
    'postgres': 5432,
    'mariadb': 3306,
    'oracle': 1521,
    'sqlserver': 1433,
}

# Resource URIs
RESOURCE_PREFIX_DB_CLUSTER = 'aws-rds://clusters'
RESOURCE_PREFIX_DB_INSTANCE = 'aws-rds://instances'

# Default config values
DEFAULT_MAX_ITEMS = 100
