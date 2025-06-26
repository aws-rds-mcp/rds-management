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

"""DB parameter group management functionality for RDS Management MCP Server."""

import json
import secrets
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import Context

from .models import (
    ParameterModel,
    ParameterGroupModel,
    ParameterGroupListModel,
    ParameterListModel,
)
from .utils import handle_aws_error, format_aws_response


async def create_db_cluster_parameter_group(
    ctx: Context,
    rds_client: Any,
    readonly: bool,
    db_cluster_parameter_group_name: str,
    db_parameter_group_family: str,
    description: str,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Creates a new DB cluster parameter group.

    Args:
        ctx: The MCP context
        rds_client: RDS boto client
        readonly: Whether the operation is read-only
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        db_parameter_group_family: The DB parameter group family name
        description: The description for the DB cluster parameter group
        tags: A list of tags to apply to the new DB cluster parameter group

    Returns:
        Response with details about the DB cluster parameter group
    """
    if readonly:
        return {
            "message": f"[READONLY MODE] Would create DB cluster parameter group '{db_cluster_parameter_group_name}' with family '{db_parameter_group_family}'",
            "simulated": True,
            "parameters": {
                "db_cluster_parameter_group_name": db_cluster_parameter_group_name,
                "db_parameter_group_family": db_parameter_group_family,
                "description": description,
                "tags": tags,
            },
        }

    try:
        aws_tags = None
        if tags:
            aws_tags = [{"Key": k, "Value": v} for item in tags for k, v in item.items()]

        params = {
            "DBClusterParameterGroupName": db_cluster_parameter_group_name,
            "DBParameterGroupFamily": db_parameter_group_family,
            "Description": description,
        }
        if aws_tags:
            params["Tags"] = aws_tags

        try:
            response = rds_client.create_db_cluster_parameter_group(**params)
            response = format_aws_response(response)
        except Exception as e:
            return await handle_aws_error("create_db_cluster_parameter_group", e, ctx)

        formatted_response = {
            "name": response.get("DBClusterParameterGroup", {}).get("DBClusterParameterGroupName"),
            "description": response.get("DBClusterParameterGroup", {}).get("Description"),
            "family": response.get("DBClusterParameterGroup", {}).get("DBParameterGroupFamily"),
            "type": "cluster",
            "arn": response.get("DBClusterParameterGroup", {}).get("DBClusterParameterGroupArn"),
        }

        return {
            "message": f"Successfully created DB cluster parameter group '{db_cluster_parameter_group_name}'",
            "formatted_parameter_group": formatted_response,
            "DBClusterParameterGroup": response,
        }
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error creating DB cluster parameter group: {error_message}")
        return {"error": f"Failed to create DB cluster parameter group: {error_message}"}


async def modify_db_cluster_parameter_group(
    ctx: Context,
    rds_client: Any,
    readonly: bool,
    db_cluster_parameter_group_name: str,
    parameters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Modifies parameters in a DB cluster parameter group.

    Args:
        ctx: The MCP context
        rds_client: RDS boto client
        readonly: Whether the operation is read-only
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        parameters: The parameters to modify

    Returns:
        Response with details about the modified DB cluster parameter group
    """
    if readonly:
        return {
            "message": f"[READONLY MODE] Would modify parameters in DB cluster parameter group '{db_cluster_parameter_group_name}'",
            "simulated": True,
            "parameters": {
                "db_cluster_parameter_group_name": db_cluster_parameter_group_name,
                "parameters": parameters,
            },
        }

    try:
        formatted_parameters = []
        for param in parameters:
            formatted_param = {
                "ParameterName": param.get("name"),
                "ParameterValue": param.get("value"),
            }
            if param.get("apply_method"):
                formatted_param["ApplyMethod"] = param.get("apply_method")
            formatted_parameters.append(formatted_param)

        try:
            response = rds_client.modify_db_cluster_parameter_group(
                DBClusterParameterGroupName=db_cluster_parameter_group_name,
                Parameters=formatted_parameters
            )
            response = format_aws_response(response)
        except Exception as e:
            return await handle_aws_error("modify_db_cluster_parameter_group", e, ctx)

        try:
            parameters_response = rds_client.describe_db_cluster_parameters(
                DBClusterParameterGroupName=db_cluster_parameter_group_name
            )
            parameters_response = format_aws_response(parameters_response)
        except Exception as e:
            return await handle_aws_error("describe_db_cluster_parameters", e, ctx)

        formatted_parameters = []
        for param in parameters_response.get("Parameters", []):
            formatted_parameters.append({
                "name": param.get("ParameterName"),
                "value": param.get("ParameterValue"),
                "description": param.get("Description"),
                "allowed_values": param.get("AllowedValues"),
                "source": param.get("Source"),
                "apply_type": param.get("ApplyType"),
                "data_type": param.get("DataType"),
                "is_modifiable": param.get("IsModifiable", False),
            })

        return {
            "message": f"Successfully modified parameters in DB cluster parameter group '{db_cluster_parameter_group_name}'",
            "parameters_modified": len(response.get("Parameters", [])),
            "formatted_parameters": formatted_parameters[:10], 
            "total_parameters": len(formatted_parameters),
            "DBClusterParameterGroupStatus": response,
        }
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error modifying DB cluster parameter group: {error_message}")
        return {"error": f"Failed to modify DB cluster parameter group: {error_message}"}


async def reset_db_cluster_parameter_group(
    ctx: Context,
    rds_client: Any,
    readonly: bool,
    db_cluster_parameter_group_name: str,
    reset_all_parameters: bool = False,
    parameters: Optional[List[Dict[str, Any]]] = None,
    confirmation_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Resets parameters in a DB cluster parameter group to their default values.

    Args:
        ctx: The MCP context
        rds_client: RDS boto client
        readonly: Whether the operation is read-only
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        reset_all_parameters: Whether to reset all parameters
        parameters: The parameters to reset (if not resetting all)
        confirmation_token: Token to confirm this operation

    Returns:
        Response with details about the reset operation
    """
    if confirmation_token is None:
        token = secrets.token_hex(8)
        return {
            "requires_confirmation": True,
            "warning": f"You are about to reset parameters in DB cluster parameter group '{db_cluster_parameter_group_name}'",
            "impact": "This will revert parameters to their default values which may impact database behavior",
            "confirmation_token": token,
            "message": (
                f"To confirm reset of DB cluster parameter group '{db_cluster_parameter_group_name}', "
                f"please re-run with the confirmation_token parameter: {token}"
            ),
        }

    if readonly:
        return {
            "message": f"[READONLY MODE] Would reset parameters in DB cluster parameter group '{db_cluster_parameter_group_name}'",
            "simulated": True,
            "parameters": {
                "db_cluster_parameter_group_name": db_cluster_parameter_group_name,
                "reset_all_parameters": reset_all_parameters,
                "parameters": parameters,
            },
        }

    try:
        formatted_parameters = []
        if not reset_all_parameters and parameters:
            for param in parameters:
                formatted_param = {
                    "ParameterName": param.get("name"),
                }
                if param.get("apply_method"):
                    formatted_param["ApplyMethod"] = param.get("apply_method")
                formatted_parameters.append(formatted_param)

        try:
            response = rds_client.reset_db_cluster_parameter_group(
                DBClusterParameterGroupName=db_cluster_parameter_group_name,
                ResetAllParameters=reset_all_parameters,
                Parameters=formatted_parameters if not reset_all_parameters else []
            )
            response = format_aws_response(response)
        except Exception as e:
            return await handle_aws_error("reset_db_cluster_parameter_group", e, ctx)

        return {
            "message": (
                f"Successfully reset {'all parameters' if reset_all_parameters else 'specified parameters'} "
                f"in DB cluster parameter group '{db_cluster_parameter_group_name}'"
            ),
            "parameters_reset": len(response.get("Parameters", [])),
            "DBClusterParameterGroupStatus": response,
        }
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error resetting DB cluster parameter group: {error_message}")
        return {"error": f"Failed to reset DB cluster parameter group: {error_message}"}


async def describe_db_cluster_parameters(
    ctx: Context,
    rds_client: Any,
    db_cluster_parameter_group_name: str,
    source: Optional[str] = None,
    marker: Optional[str] = None,
    max_records: Optional[int] = None,
) -> Dict[str, Any]:
    """Returns a list of parameters for a DB cluster parameter group.

    Args:
        ctx: The MCP context
        rds_client: RDS boto client
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        source: The parameter source
        marker: Pagination marker
        max_records: Maximum number of records to return

    Returns:
        List of parameters for the DB cluster parameter group
    """
    try:
        params = {
            "DBClusterParameterGroupName": db_cluster_parameter_group_name,
        }
        if source:
            params["Source"] = source
        if marker:
            params["Marker"] = marker
        if max_records:
            params["MaxRecords"] = max_records

        try:
            response = rds_client.describe_db_cluster_parameters(**params)
            response = format_aws_response(response)
        except Exception as e:
            return await handle_aws_error("describe_db_cluster_parameters", e, ctx)

        formatted_parameters = []
        for param in response.get("Parameters", []):
            formatted_parameters.append({
                "name": param.get("ParameterName"),
                "value": param.get("ParameterValue"),
                "description": param.get("Description"),
                "allowed_values": param.get("AllowedValues"),
                "source": param.get("Source"),
                "apply_type": param.get("ApplyType"),
                "data_type": param.get("DataType"),
                "is_modifiable": param.get("IsModifiable", False),
            })

        parameter_list = ParameterListModel(
            parameters=formatted_parameters,
            count=len(formatted_parameters),
            parameter_group_name=db_cluster_parameter_group_name,
            resource_uri=f"aws-rds://db-cluster/parameter-groups/{db_cluster_parameter_group_name}/parameters",
        )

        return {
            "formatted_parameters": parameter_list,
            "Parameters": response.get("Parameters", []),
            "Marker": response.get("Marker"),
        }
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error describing DB cluster parameters: {error_message}")
        return {"error": f"Failed to describe DB cluster parameters: {error_message}"}


async def describe_db_instance_parameters(
    ctx: Context,
    rds_client: Any,
    db_parameter_group_name: str,
    source: Optional[str] = None,
    marker: Optional[str] = None,
    max_records: Optional[int] = None,
) -> Dict[str, Any]:
    """Returns a list of parameters for a DB instance parameter group.

    Args:
        ctx: The MCP context
        rds_client: RDS boto client
        db_parameter_group_name: The name of the DB parameter group
        source: The parameter source
        marker: Pagination marker
        max_records: Maximum number of records to return

    Returns:
        List of parameters for the DB parameter group
    """
    try:
        params = {
            "DBParameterGroupName": db_parameter_group_name,
        }
        if source:
            params["Source"] = source
        if marker:
            params["Marker"] = marker
        if max_records:
            params["MaxRecords"] = max_records

        try:
            response = rds_client.describe_db_parameters(**params)
            response = format_aws_response(response)
        except Exception as e:
            return await handle_aws_error("describe_db_parameters", e, ctx)

        formatted_parameters = []
        for param in response.get("Parameters", []):
            formatted_parameters.append({
                "name": param.get("ParameterName"),
                "value": param.get("ParameterValue"),
                "description": param.get("Description"),
                "allowed_values": param.get("AllowedValues"),
                "source": param.get("Source"),
                "apply_type": param.get("ApplyType"),
                "data_type": param.get("DataType"),
                "is_modifiable": param.get("IsModifiable", False),
            })

        parameter_list = ParameterListModel(
            parameters=formatted_parameters,
            count=len(formatted_parameters),
            parameter_group_name=db_parameter_group_name,
            resource_uri=f"aws-rds://db-instance/parameter-groups/{db_parameter_group_name}/parameters",
        )

        return {
            "formatted_parameters": parameter_list,
            "Parameters": response.get("Parameters", []),
            "Marker": response.get("Marker"),
        }
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error describing DB instance parameters: {error_message}")
        return {"error": f"Failed to describe DB instance parameters: {error_message}"}


async def describe_db_cluster_parameter_groups(
    ctx: Context,
    rds_client: Any,
    db_cluster_parameter_group_name: Optional[str] = None,
    marker: Optional[str] = None,
    max_records: Optional[int] = None,
) -> Dict[str, Any]:
    """Returns a list of DB cluster parameter group descriptions.

    Args:
        ctx: The MCP context
        rds_client: RDS boto client
        db_cluster_parameter_group_name: The name of the DB cluster parameter group
        marker: Pagination marker
        max_records: Maximum number of records to return

    Returns:
        List of DB cluster parameter group descriptions
    """
    try:
        params = {}
        if db_cluster_parameter_group_name:
            params["DBClusterParameterGroupName"] = db_cluster_parameter_group_name
        if marker:
            params["Marker"] = marker
        if max_records:
            params["MaxRecords"] = max_records

        try:
            response = rds_client.describe_db_cluster_parameter_groups(**params)
            response = format_aws_response(response)
        except Exception as e:
            return await handle_aws_error("describe_db_cluster_parameter_groups", e, ctx)

        formatted_parameter_groups = []
        for pg in response.get("DBClusterParameterGroups", []):
            try:
                parameters_response = rds_client.describe_db_cluster_parameters(
                    DBClusterParameterGroupName=pg.get("DBClusterParameterGroupName"),
                    MaxRecords=20 
                )
                parameters_response = format_aws_response(parameters_response)
            except Exception as e:
                logger.error(f"Error getting parameters for group {pg.get('DBClusterParameterGroupName')}: {str(e)}")
                parameters_response = {"Parameters": []}
            
            formatted_parameters = []
            for param in parameters_response.get("Parameters", []):
                formatted_parameters.append(
                    ParameterModel(
                        name=param.get("ParameterName"),
                        value=param.get("ParameterValue"),
                        description=param.get("Description"),
                        allowed_values=param.get("AllowedValues"),
                        source=param.get("Source"),
                        apply_type=param.get("ApplyType"),
                        data_type=param.get("DataType"),
                        is_modifiable=param.get("IsModifiable", False),
                    )
                )

            tags = {}
            if "Tags" in pg:
                tags = {tag.get("Key"): tag.get("Value") for tag in pg.get("Tags", [])}

            parameter_group = ParameterGroupModel(
                name=pg.get("DBClusterParameterGroupName"),
                description=pg.get("Description"),
                family=pg.get("DBParameterGroupFamily"),
                type="cluster",
                parameters=formatted_parameters,
                arn=pg.get("DBClusterParameterGroupArn"),
                tags=tags,
                resource_uri=f"aws-rds://db-cluster/parameter-groups/{pg.get('DBClusterParameterGroupName')}",
            )
            formatted_parameter_groups.append(parameter_group)

        parameter_group_list = ParameterGroupListModel(
            parameter_groups=formatted_parameter_groups,
            count=len(formatted_parameter_groups),
            resource_uri="aws-rds://db-cluster/parameter-groups",
        )

        return {
            "formatted_parameter_groups": parameter_group_list,
            "DBClusterParameterGroups": response.get("DBClusterParameterGroups", []),
            "Marker": response.get("Marker"),
        }
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error describing DB cluster parameter groups: {error_message}")
        return {"error": f"Failed to describe DB cluster parameter groups: {error_message}"}


async def describe_db_instance_parameter_groups(
    ctx: Context,
    rds_client: Any,
    db_parameter_group_name: Optional[str] = None,
    marker: Optional[str] = None,
    max_records: Optional[int] = None,
) -> Dict[str, Any]:
    """Returns a list of DB instance parameter group descriptions.

    Args:
        ctx: The MCP context
        rds_client: RDS boto client
        db_parameter_group_name: The name of the DB parameter group
        marker: Pagination marker
        max_records: Maximum number of records to return

    Returns:
        List of DB parameter group descriptions
    """
    try:
        params = {}
        if db_parameter_group_name:
            params["DBParameterGroupName"] = db_parameter_group_name
        if marker:
            params["Marker"] = marker
        if max_records:
            params["MaxRecords"] = max_records

        try:
            response = rds_client.describe_db_parameter_groups(**params)
            response = format_aws_response(response)
        except Exception as e:
            return await handle_aws_error("describe_db_parameter_groups", e, ctx)

        formatted_parameter_groups = []
        for pg in response.get("DBParameterGroups", []):
            try:
                parameters_response = rds_client.describe_db_parameters(
                    DBParameterGroupName=pg.get("DBParameterGroupName"),
                    MaxRecords=20  
                )
                parameters_response = format_aws_response(parameters_response)
            except Exception as e:
                logger.error(f"Error getting parameters for group {pg.get('DBParameterGroupName')}: {str(e)}")
                parameters_response = {"Parameters": []}
            
            formatted_parameters = []
            for param in parameters_response.get("Parameters", []):
                formatted_parameters.append(
                    ParameterModel(
                        name=param.get("ParameterName"),
                        value=param.get("ParameterValue"),
                        description=param.get("Description"),
                        allowed_values=param.get("AllowedValues"),
                        source=param.get("Source"),
                        apply_type=param.get("ApplyType"),
                        data_type=param.get("DataType"),
                        is_modifiable=param.get("IsModifiable", False),
                    )
                )

            tags = {}
            if "Tags" in pg:
                tags = {tag.get("Key"): tag.get("Value") for tag in pg.get("Tags", [])}

            parameter_group = ParameterGroupModel(
                name=pg.get("DBParameterGroupName"),
                description=pg.get("Description"),
                family=pg.get("DBParameterGroupFamily"),
                type="instance",
                parameters=formatted_parameters,
                arn=pg.get("DBParameterGroupArn"),
                tags=tags,
                resource_uri=f"aws-rds://db-instance/parameter-groups/{pg.get('DBParameterGroupName')}",
            )
            formatted_parameter_groups.append(parameter_group)

        parameter_group_list = ParameterGroupListModel(
            parameter_groups=formatted_parameter_groups,
            count=len(formatted_parameter_groups),
            resource_uri="aws-rds://db-instance/parameter-groups",
        )

        return {
            "formatted_parameter_groups": parameter_group_list,
            "DBParameterGroups": response.get("DBParameterGroups", []),
            "Marker": response.get("Marker"),
        }
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error describing DB instance parameter groups: {error_message}")
        return {"error": f"Failed to describe DB instance parameter groups: {error_message}"}


async def get_db_instance_parameters_resource(
    db_parameter_group_name: str,
    rds_client: Any,
) -> str:
    """Get parameters for a specific DB instance parameter group.

    Args:
        db_parameter_group_name: Name of the DB parameter group
        rds_client: RDS boto client

    Returns:
        JSON string with parameters
    """
    try:
        try:
            response = rds_client.describe_db_parameters(
                DBParameterGroupName=db_parameter_group_name
            )
            response = format_aws_response(response)
        except Exception as e:
            logger.error(f"Error retrieving DB parameters: {str(e)}")
            return json.dumps({"error": f"Failed to get DB parameters: {str(e)}"})

        parameters = []
        for param in response.get("Parameters", []):
            parameters.append({
                "name": param.get("ParameterName"),
                "value": param.get("ParameterValue"),
                "description": param.get("Description"),
                "allowed_values": param.get("AllowedValues"),
                "source": param.get("Source"),
                "apply_type": param.get("ApplyType"),
                "data_type": param.get("DataType"),
                "is_modifiable": param.get("IsModifiable", False),
            })

        result = {
            "parameters": parameters,
            "count": len(parameters),
            "parameter_group_name": db_parameter_group_name,
            "resource_uri": f"aws-rds://db-instance/parameter-groups/{db_parameter_group_name}/parameters",
        }
        return json.dumps(result)
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error getting DB instance parameters: {error_message}")
        return json.dumps({"error": f"Failed to get DB instance parameters: {error_message}"})


async def get_db_cluster_parameters_resource(
    db_cluster_parameter_group_name: str,
    rds_client: Any,
) -> str:
    """Get parameters for a specific DB cluster parameter group.

    Args:
        db_cluster_parameter_group_name: Name of the DB cluster parameter group
        rds_client: RDS boto client

    Returns:
        JSON string with parameters
    """
    try:
        try:
            response = rds_client.describe_db_cluster_parameters(
                DBClusterParameterGroupName=db_cluster_parameter_group_name
            )
            response = format_aws_response(response)
        except Exception as e:
            logger.error(f"Error retrieving DB cluster parameters: {str(e)}")
            return json.dumps({"error": f"Failed to get DB cluster parameters: {str(e)}"})

        parameters = []
        for param in response.get("Parameters", []):
            parameters.append({
                "name": param.get("ParameterName"),
                "value": param.get("ParameterValue"),
                "description": param.get("Description"),
                "allowed_values": param.get("AllowedValues"),
                "source": param.get("Source"),
                "apply_type": param.get("ApplyType"),
                "data_type": param.get("DataType"),
                "is_modifiable": param.get("IsModifiable", False),
            })

        result = {
            "parameters": parameters,
            "count": len(parameters),
            "parameter_group_name": db_cluster_parameter_group_name,
            "resource_uri": f"aws-rds://db-cluster/parameter-groups/{db_cluster_parameter_group_name}/parameters",
        }
        return json.dumps(result)
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error getting DB cluster parameters: {error_message}")
        return json.dumps({"error": f"Failed to get DB cluster parameters: {error_message}"})


async def get_db_instance_parameter_groups_resource(rds_client: Any) -> str:
    """List all DB instance parameter groups.

    Args:
        rds_client: RDS boto client

    Returns:
        JSON string with parameter groups
    """
    try:
        try:
            response = rds_client.describe_db_parameter_groups()
            response = format_aws_response(response)
        except Exception as e:
            logger.error(f"Error retrieving DB parameter groups: {str(e)}")
            return json.dumps({"error": f"Failed to get DB parameter groups: {str(e)}"})

        parameter_groups = []
        for pg in response.get("DBParameterGroups", []):
            tags = {}
            if "Tags" in pg:
                tags = {tag.get("Key"): tag.get("Value") for tag in pg.get("Tags", [])}
            
            parameter_groups.append({
                "name": pg.get("DBParameterGroupName"),
                "description": pg.get("Description"),
                "family": pg.get("DBParameterGroupFamily"),
                "type": "instance",
                "arn": pg.get("DBParameterGroupArn"),
                "tags": tags,
                "resource_uri": f"aws-rds://db-instance/parameter-groups/{pg.get('DBParameterGroupName')}",
            })

        result = {
            "parameter_groups": parameter_groups,
            "count": len(parameter_groups),
            "resource_uri": "aws-rds://db-instance/parameter-groups",
        }
        return json.dumps(result)
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error getting DB instance parameter groups: {error_message}")
        return json.dumps({"error": f"Failed to get DB instance parameter groups: {error_message}"})


async def get_db_cluster_parameter_groups_resource(rds_client: Any) -> str:
    """List all DB cluster parameter groups.

    Args:
        rds_client: RDS boto client

    Returns:
        JSON string with parameter groups
    """
    try:
        try:
            response = rds_client.describe_db_cluster_parameter_groups()
            response = format_aws_response(response)
        except Exception as e:
            logger.error(f"Error retrieving DB cluster parameter groups: {str(e)}")
            return json.dumps({"error": f"Failed to get DB cluster parameter groups: {str(e)}"})

        parameter_groups = []
        for pg in response.get("DBClusterParameterGroups", []):
            tags = {}
            if "Tags" in pg:
                tags = {tag.get("Key"): tag.get("Value") for tag in pg.get("Tags", [])}
            
            parameter_groups.append({
                "name": pg.get("DBClusterParameterGroupName"),
                "description": pg.get("Description"),
                "family": pg.get("DBParameterGroupFamily"),
                "type": "cluster",
                "arn": pg.get("DBClusterParameterGroupArn"),
                "tags": tags,
                "resource_uri": f"aws-rds://db-cluster/parameter-groups/{pg.get('DBClusterParameterGroupName')}",
            })

        result = {
            "parameter_groups": parameter_groups,
            "count": len(parameter_groups),
            "resource_uri": "aws-rds://db-cluster/parameter-groups",
        }
        return json.dumps(result)
    except ClientError as e:
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Error getting DB cluster parameter groups: {error_message}")
        return json.dumps({"error": f"Failed to get DB cluster parameter groups: {error_message}"})
