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

"""Resource for getting detailed information about a specific RDS DB Instance."""

from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...models import InstanceEndpoint, InstanceModel, InstanceStorage, VpcSecurityGroup
from loguru import logger
from pydantic import Field
from typing_extensions import Annotated


GET_INSTANCE_DETAIL_RESOURCE_DESCRIPTION = """Get detailed information about a specific Amazon RDS instance.

<use_case>
Use this resource to retrieve comprehensive details about a specific RDS database instance
identified by its instance ID. This provides deeper insights than the instance list resource.
</use_case>

<important_notes>
1. The response contains full configuration details about the specified instance
2. This resource includes information not available in the list view such as storage details,
   parameter groups, backup configuration, maintenance windows and security settings
3. Use the instance list resource first to identify valid instance IDs
4. Error responses will be returned if the instance doesn't exist or there are permission issues
5. The response includes all tags associated with the instance
6. Security group information includes both the ID and current status
</important_notes>

## Response structure
Returns a JSON document containing detailed instance information:
- `instance_id`: The unique identifier for the instance
- `status`: Current operational status of the instance
- `engine`: Database engine type (e.g. mysql, postgres)
- `engine_version`: The version of the database engine
- `endpoint`: Connection endpoint information including address, port and hosted zone
- `instance_class`: The compute and memory capacity of the instance
- `availability_zone`: The AZ where the instance is located
- `multi_az`: Whether the instance is a Multi-AZ deployment
- `storage`: Detailed storage configuration including type, allocation and encryption status
- `preferred_backup_window`: When automated backups occur
- `preferred_maintenance_window`: When maintenance operations can occur
- `publicly_accessible`: Whether the instance is publicly accessible
- `vpc_security_groups`: Security groups associated with the instance
- `db_cluster`: The DB cluster identifier if this instance is part of a cluster
- `tags`: Any tags associated with the instance
- `resource_uri`: The full resource URI for this specific instance
"""


@mcp.resource(
    uri='aws-rds://db-instance/{instance_id}',
    name='GetDBInstanceDetail',
    description=GET_INSTANCE_DETAIL_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def get_instance_detail(
    instance_id: Annotated[str, Field(description='The instance identifier')],
) -> InstanceModel:
    """Get detailed information about a specific RDS instance.

    Retrieves comprehensive details about a specific RDS database instance identified
    by its instance ID. This provides detailed insights into the instance's configuration,
    performance, and status.

    Args:
        instance_id: The identifier of the DB instance to retrieve details for

    Returns:
        InstanceModel: Object containing detailed information about the DB instance
    """
    logger.info(f'Getting details for RDS instance: {instance_id}')
    rds_client = RDSConnectionManager.get_connection()

    response = rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
    instances = response.get('DBInstances', [])

    if not instances:
        raise ValueError(f'DB instance {instance_id} not found')

    instance_data = instances[0]

    # Format endpoint
    endpoint = InstanceEndpoint()
    if instance_data.get('Endpoint'):
        if isinstance(instance_data['Endpoint'], dict):
            endpoint = InstanceEndpoint(
                address=instance_data['Endpoint'].get('Address'),
                port=instance_data['Endpoint'].get('Port'),
                hosted_zone_id=instance_data['Endpoint'].get('HostedZoneId'),
            )
        else:
            endpoint = InstanceEndpoint(address=instance_data.get('Endpoint'))

    # Format storage
    storage = InstanceStorage(
        type=instance_data.get('StorageType'),
        allocated=instance_data.get('AllocatedStorage'),
        encrypted=instance_data.get('StorageEncrypted'),
    )

    # Format VPC security groups
    vpc_security_groups = []
    for sg in instance_data.get('VpcSecurityGroups', []):
        vpc_security_groups.append(
            VpcSecurityGroup(id=sg.get('VpcSecurityGroupId'), status=sg.get('Status'))
        )

    # Format tags
    tags = {}
    if instance_data.get('TagList'):
        for tag in instance_data.get('TagList', []):
            if 'Key' in tag and 'Value' in tag:
                tags[tag['Key']] = tag['Value']

    # Create the instance model
    instance = InstanceModel(
        instance_id=instance_data.get('DBInstanceIdentifier'),
        status=instance_data.get('DBInstanceStatus'),
        engine=instance_data.get('Engine'),
        engine_version=instance_data.get('EngineVersion'),
        instance_class=instance_data.get('DBInstanceClass'),
        endpoint=endpoint,
        availability_zone=instance_data.get('AvailabilityZone'),
        multi_az=instance_data.get('MultiAZ', False),
        storage=storage,
        preferred_backup_window=instance_data.get('PreferredBackupWindow'),
        preferred_maintenance_window=instance_data.get('PreferredMaintenanceWindow'),
        publicly_accessible=instance_data.get('PubliclyAccessible', False),
        vpc_security_groups=vpc_security_groups,
        db_cluster=instance_data.get('DBClusterIdentifier'),
        tags=tags,
        dbi_resource_id=instance_data.get('DbiResourceId'),
        resource_uri=f'aws-rds://db-instance/{instance_id}',
    )

    return instance
