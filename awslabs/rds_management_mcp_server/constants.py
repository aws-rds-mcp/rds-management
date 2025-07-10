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

# Confirmation Messages
CONFIRM_DELETE_CLUSTER = """
⚠️ WARNING: You are about to delete the database cluster '{cluster_id}'.

This action will:
- Permanently delete all data in the cluster (unless a final snapshot is created)
- Terminate all instances in the cluster
- Cause downtime for any applications using this database
- Remove all automated backups after the retention period

This operation cannot be undone.
"""

CONFIRM_DELETE_INSTANCE = """
⚠️ WARNING: You are about to delete the database instance '{instance_id}'.

This action will:
- Permanently delete all data in the instance (unless a final snapshot is created)
- Cause downtime for any applications using this database
- Remove all automated backups after the retention period

This operation cannot be undone.
"""

CONFIRM_STOP_CLUSTER = """
⚠️ NOTICE: You are about to stop the database cluster '{cluster_id}'.

This action will:
- Stop all instances in the cluster
- Make the database unavailable to applications
- Continue to incur storage charges
- Preserve all data and configurations

The cluster can be restarted later.
"""

CONFIRM_STOP = 'CONFIRM_STOP'
CONFIRM_START = 'CONFIRM_START'
CONFIRM_REBOOT = 'CONFIRM_REBOOT'

CONFIRM_FAILOVER = """
⚠️ NOTICE: You are about to initiate a failover for cluster '{cluster_id}'.

This action will:
- Promote a read replica to become the new primary instance
- Cause a brief interruption in database availability (typically 30-60 seconds)
- Update the cluster endpoint to point to the new primary

This is typically used for disaster recovery or maintenance.
"""

# Operation Impact Descriptions
OPERATION_IMPACTS = {
    # Cluster operations
    'delete_db_cluster': {
        'risk': RISK_CRITICAL,
        'downtime': 'Permanent',
        'data_loss': 'All data will be lost unless final snapshot is taken',
        'reversible': False,
        'estimated_time': '5-10 minutes',
    },
    'stop_db_cluster': {
        'risk': RISK_HIGH,
        'downtime': 'Until cluster is restarted',
        'data_loss': 'None',
        'reversible': True,
        'estimated_time': '5-10 minutes',
    },
    'failover_db_cluster': {
        'risk': RISK_HIGH,
        'downtime': '30-60 seconds',
        'data_loss': 'None',
        'reversible': False,
        'estimated_time': '1-2 minutes',
    },
    'modify_db_cluster': {
        'risk': RISK_HIGH,
        'downtime': 'Depends on modifications',
        'data_loss': 'None',
        'reversible': True,
        'estimated_time': 'Varies',
    },
    'reboot_db_cluster': {
        'risk': RISK_HIGH,
        'downtime': '2-5 minutes',
        'data_loss': 'None',
        'reversible': False,
        'estimated_time': '2-5 minutes',
    },
    'start_db_cluster': {
        'risk': RISK_LOW,
        'downtime': 'None',
        'data_loss': 'None',
        'reversible': True,
        'estimated_time': '5-10 minutes',
    },
    # Instance operations
    'delete_db_instance': {
        'risk': RISK_CRITICAL,
        'downtime': 'Permanent',
        'data_loss': 'All data will be lost unless final snapshot is taken',
        'reversible': False,
        'estimated_time': '3-5 minutes',
    },
    'stop_db_instance': {
        'risk': RISK_HIGH,
        'downtime': 'Until instance is restarted',
        'data_loss': 'None',
        'reversible': True,
        'estimated_time': '1-3 minutes',
    },
    'reboot_db_instance': {
        'risk': RISK_HIGH,
        'downtime': '1-3 minutes',
        'data_loss': 'None',
        'reversible': False,
        'estimated_time': '1-3 minutes',
    },
    'start_db_instance': {
        'risk': RISK_LOW,
        'downtime': 'None',
        'data_loss': 'None',
        'reversible': True,
        'estimated_time': '3-5 minutes',
    },
    'modify_db_instance': {
        'risk': RISK_HIGH,
        'downtime': 'Depends on modifications',
        'data_loss': 'None',
        'reversible': True,
        'estimated_time': 'Varies',
    },
}
