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

"""Resource for listing available RDS DB Instances."""

from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions
from ...common.server import mcp
from ...common.utils import handle_paginated_aws_api_call
from loguru import logger
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class InstanceEndpoint(BaseModel):
    """DB instance endpoint model."""

    address: Optional[str] = Field(None, description='The DNS address of the instance')
    port: Optional[int] = Field(
        None, description='The port that the database engine is listening on'
    )
    hosted_zone_id: Optional[str] = Field(
        None, description='The ID of the Amazon Route 53 hosted zone'
    )


class InstanceStorage(BaseModel):
    """DB instance storage model."""

    type: Optional[str] = Field(None, description='The storage type')
    allocated: Optional[int] = Field(None, description='The allocated storage size in gibibytes')
    encrypted: Optional[bool] = Field(None, description='Whether the storage is encrypted')


class InstanceSummary(BaseModel):
    """Simplified DB instance model for list views."""

    instance_id: str = Field(description='The DB instance identifier')
    status: str = Field(description='The current status of the DB instance')
    engine: str = Field(description='The database engine')
    engine_version: Optional[str] = Field(None, description='The version of the database engine')
    instance_class: str = Field(
        description='The compute and memory capacity class of the DB instance'
    )
    endpoint: InstanceEndpoint = Field(
        default_factory=InstanceEndpoint, description='The connection endpoint'
    )
    availability_zone: Optional[str] = Field(
        None, description='The Availability Zone of the DB instance'
    )
    multi_az: bool = Field(description='Whether the DB instance is a Multi-AZ deployment')
    publicly_accessible: bool = Field(description='Whether the DB instance is publicly accessible')
    db_cluster: Optional[str] = Field(
        None, description='The DB cluster identifier, if this is a member of a DB cluster'
    )
    tag_list: Dict[str, str] = Field(default_factory=dict, description='A dictionary of tags')
    dbi_resource_id: Optional[str] = Field(
        None, description='The AWS Region-unique, immutable identifier for the DB instance'
    )

    @classmethod
    def from_dict(cls, instance: Dict) -> 'InstanceSummary':
        """Format instance information into a simplified summary model for list views.

        Args:
            instance: Raw instance data from AWS API response containing instance details and configuration

        Returns:
            InstanceSummary: Formatted instance summary information containing essential instance details
        """
        # Handle potentially nested endpoint structure
        endpoint = InstanceEndpoint()
        if instance.get('Endpoint'):
            if isinstance(instance['Endpoint'], dict):
                endpoint = InstanceEndpoint(
                    address=instance['Endpoint'].get('Address'),
                    port=instance['Endpoint'].get('Port'),
                    hosted_zone_id=instance['Endpoint'].get('HostedZoneId')
                )
            else:
                endpoint = InstanceEndpoint(address=instance.get('Endpoint'))
        
        # Format tags
        tags = {}
        if instance.get('TagList'):
            for tag in instance.get('TagList', []):
                if 'Key' in tag and 'Value' in tag:
                    tags[tag['Key']] = tag['Value']

        return InstanceSummary(
            instance_id=instance.get('DBInstanceIdentifier', ''),
            status=instance.get('DBInstanceStatus', ''),
            engine=instance.get('Engine', ''),
            engine_version=instance.get('EngineVersion'),
            instance_class=instance.get('DBInstanceClass', ''),
            endpoint=endpoint,
            availability_zone=instance.get('AvailabilityZone'),
            multi_az=instance.get('MultiAZ', False),
            publicly_accessible=instance.get('PubliclyAccessible', False),
            db_cluster=instance.get('DBClusterIdentifier'),
            tag_list=tags,
            dbi_resource_id=instance.get('DbiResourceId'),
        )


class InstanceSummaryList(BaseModel):
    """DB instance list model containing instance summaries and metadata."""

    instances: List[InstanceSummary] = Field(description='List of DB instances')
    count: int = Field(description='Number of DB instances')
    resource_uri: str = Field(description='The resource URI for instances')


LIST_INSTANCES_RESOURCE_DESCRIPTION = """List all available Amazon RDS instances in your account.

<use_case>
Use this resource to discover all available RDS database instances in your AWS account.
</use_case>

<important_notes>
1. The response provides essential information about each instance
2. Instance identifiers returned can be used with other tools and resources in this MCP server
3. Keep note of the instance_id and dbi_resource_id for use with other tools
4. Instances are filtered to the AWS region specified in your environment configuration
5. Use the `aws-rds://db-instance/{instance_id}` to get more information about a specific instance
</important_notes>

## Response structure
Returns a JSON document containing:
- `instances`: Array of DB instance objects
- `count`: Number of instances found
- `resource_uri`: Base URI for accessing instances

Each instance object contains:
- `instance_id`: Unique identifier for the instance
- `status`: Current status of the instance
- `engine`: Database engine type
- `engine_version`: The version of the database engine
- `instance_class`: The instance type (e.g., db.t3.medium)
- `availability_zone`: The AZ where the instance is located
- `multi_az`: Whether the instance has Multi-AZ deployment
- `publicly_accessible`: Whether the instance is publicly accessible
- `db_cluster`: The DB cluster identifier (if applicable)
- `tag_list`: Dictionary of instance tags
"""


@mcp.resource(
    uri='aws-rds://db-instance',
    name='ListDBInstances',
    description=LIST_INSTANCES_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def list_instances() -> InstanceSummaryList:
    """List all RDS instances in the current AWS region.

    Retrieves a complete list of all RDS database instances in the current AWS region.
    The function handles pagination automatically for large result sets and formats
    the instance information into a simplified summary model.

    Returns:
        InstanceSummaryList: Object containing list of formatted instance summaries,
        total count, and resource URI
    """
    logger.info('Listing RDS instances')
    rds_client = RDSConnectionManager.get_connection()

    instances = handle_paginated_aws_api_call(
        client=rds_client,
        paginator_name='describe_db_instances',
        operation_parameters={},
        format_function=InstanceSummary.from_dict,
        result_key='DBInstances',
    )

    result = InstanceSummaryList(
        instances=instances, count=len(instances), resource_uri='aws-rds://db-instance'
    )

    return result
