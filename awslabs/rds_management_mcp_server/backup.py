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

"""Backup management functions for RDS Management MCP Server."""

import json
import secrets
import uuid
from typing import Any, Dict, List, Optional

from loguru import logger
from mcp.server.fastmcp import Context

from .models import (
    AutomatedBackupModel,
    BackupListModel,
    SnapshotModel,
)


async def create_db_cluster_snapshot(
    ctx: Context,
    rds_client,
    readonly: bool,
    db_cluster_snapshot_identifier: str,
    db_cluster_identifier: str,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Creates a manual snapshot of an RDS DB cluster.

    Args:
        ctx: MCP context
        rds_client: Boto3 RDS client
        readonly: Whether the server is in read-only mode
        db_cluster_snapshot_identifier: Identifier for the DB cluster snapshot
        db_cluster_identifier: Identifier of the DB cluster to snapshot
        tags: Optional list of tags to apply to the snapshot

    Returns:
        Response dictionary with status and snapshot details
    """
    if readonly:
        return {
            "message": "[READ-ONLY MODE] Snapshot creation simulated. "
            f"Would have created snapshot {db_cluster_snapshot_identifier} "
            f"from DB cluster {db_cluster_identifier}",
            "simulated": True,
        }

    try:
        kwargs = {
            "DBClusterSnapshotIdentifier": db_cluster_snapshot_identifier,
            "DBClusterIdentifier": db_cluster_identifier,
        }
        
        if tags:
            # Format tags for AWS API
            aws_tags = []
            for tag_item in tags:
                for key, value in tag_item.items():
                    aws_tags.append({"Key": key, "Value": value})
            kwargs["Tags"] = aws_tags
        
        response = rds_client.create_db_cluster_snapshot(**kwargs)
        
        # Format the response
        formatted_snapshot = {
            "snapshot_id": response.get("DBClusterSnapshot", {}).get("DBClusterSnapshotIdentifier"),
            "cluster_id": response.get("DBClusterSnapshot", {}).get("DBClusterIdentifier"),
            "status": response.get("DBClusterSnapshot", {}).get("Status"),
            "creation_time": response.get("DBClusterSnapshot", {}).get("SnapshotCreateTime"),
            "engine": response.get("DBClusterSnapshot", {}).get("Engine"),
            "engine_version": response.get("DBClusterSnapshot", {}).get("EngineVersion"),
        }
        
        return {
            "message": f"Successfully created DB cluster snapshot {db_cluster_snapshot_identifier}",
            "formatted_snapshot": formatted_snapshot,
            "DBClusterSnapshot": response.get("DBClusterSnapshot"),
        }
    except Exception as e:
        logger.error(f"Error creating DB cluster snapshot: {e}")
        return {"error": str(e)}


async def restore_db_cluster_from_snapshot(
    ctx: Context,
    rds_client,
    readonly: bool,
    db_cluster_identifier: str,
    snapshot_identifier: str,
    engine: str,
    vpc_security_group_ids: Optional[List[str]] = None,
    db_subnet_group_name: Optional[str] = None,
    engine_version: Optional[str] = None,
    port: Optional[int] = None,
    availability_zones: Optional[List[str]] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Creates a new RDS DB cluster from a DB cluster snapshot.

    Args:
        ctx: MCP context
        rds_client: Boto3 RDS client
        readonly: Whether the server is in read-only mode
        db_cluster_identifier: Identifier for the new DB cluster
        snapshot_identifier: Identifier of the DB cluster snapshot to restore from
        engine: Database engine to use
        vpc_security_group_ids: Optional list of VPC security group IDs
        db_subnet_group_name: Optional DB subnet group name
        engine_version: Optional engine version
        port: Optional port number
        availability_zones: Optional list of availability zones
        tags: Optional list of tags to apply to the new cluster

    Returns:
        Response dictionary with status and cluster details
    """
    if readonly:
        return {
            "message": "[READ-ONLY MODE] Cluster restoration simulated. "
            f"Would have restored cluster {db_cluster_identifier} "
            f"from snapshot {snapshot_identifier}",
            "simulated": True,
        }

    try:
        kwargs = {
            "DBClusterIdentifier": db_cluster_identifier,
            "SnapshotIdentifier": snapshot_identifier,
            "Engine": engine,
        }
        
        # Add optional parameters if provided
        if vpc_security_group_ids:
            kwargs["VpcSecurityGroupIds"] = vpc_security_group_ids
        if db_subnet_group_name:
            kwargs["DBSubnetGroupName"] = db_subnet_group_name
        if engine_version:
            kwargs["EngineVersion"] = engine_version
        if port:
            kwargs["Port"] = port
        if availability_zones:
            kwargs["AvailabilityZones"] = availability_zones
        if tags:
            # Format tags for AWS API
            aws_tags = []
            for tag_item in tags:
                for key, value in tag_item.items():
                    aws_tags.append({"Key": key, "Value": value})
            kwargs["Tags"] = aws_tags
        
        response = rds_client.restore_db_cluster_from_snapshot(**kwargs)
        
        # Format the response
        formatted_cluster = {
            "cluster_id": response.get("DBCluster", {}).get("DBClusterIdentifier"),
            "status": response.get("DBCluster", {}).get("Status"),
            "engine": response.get("DBCluster", {}).get("Engine"),
            "engine_version": response.get("DBCluster", {}).get("EngineVersion"),
        }
        
        return {
            "message": f"Successfully restored DB cluster {db_cluster_identifier} from snapshot {snapshot_identifier}",
            "formatted_cluster": formatted_cluster,
            "DBCluster": response.get("DBCluster"),
        }
    except Exception as e:
        logger.error(f"Error restoring DB cluster from snapshot: {e}")
        return {"error": str(e)}


async def restore_db_cluster_to_point_in_time(
    ctx: Context,
    rds_client,
    readonly: bool,
    db_cluster_identifier: str,
    source_db_cluster_identifier: str,
    restore_to_time: Optional[str] = None,
    use_latest_restorable_time: Optional[bool] = None,
    port: Optional[int] = None,
    db_subnet_group_name: Optional[str] = None,
    vpc_security_group_ids: Optional[List[str]] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Restores a DB cluster to a specific point in time.

    Args:
        ctx: MCP context
        rds_client: Boto3 RDS client
        readonly: Whether the server is in read-only mode
        db_cluster_identifier: Identifier for the new DB cluster
        source_db_cluster_identifier: Identifier of the source DB cluster
        restore_to_time: Optional timestamp to restore to (format: YYYY-MM-DDTHH:MM:SSZ)
        use_latest_restorable_time: Optional flag to use the latest restorable time
        port: Optional port number
        db_subnet_group_name: Optional DB subnet group name
        vpc_security_group_ids: Optional list of VPC security group IDs
        tags: Optional list of tags to apply to the new cluster

    Returns:
        Response dictionary with status and cluster details
    """
    if readonly:
        return {
            "message": "[READ-ONLY MODE] Point-in-time restoration simulated. "
            f"Would have restored cluster {db_cluster_identifier} "
            f"from source cluster {source_db_cluster_identifier}",
            "simulated": True,
        }

    # Validate that either restore_to_time or use_latest_restorable_time is provided
    if not restore_to_time and not use_latest_restorable_time:
        return {
            "error": "Either restore_to_time or use_latest_restorable_time must be provided"
        }

    try:
        kwargs = {
            "DBClusterIdentifier": db_cluster_identifier,
            "SourceDBClusterIdentifier": source_db_cluster_identifier,
        }
        
        # Add optional parameters if provided
        if restore_to_time:
            kwargs["RestoreToTime"] = restore_to_time
        if use_latest_restorable_time is not None:
            kwargs["UseLatestRestorableTime"] = use_latest_restorable_time
        if port:
            kwargs["Port"] = port
        if db_subnet_group_name:
            kwargs["DBSubnetGroupName"] = db_subnet_group_name
        if vpc_security_group_ids:
            kwargs["VpcSecurityGroupIds"] = vpc_security_group_ids
        if tags:
            # Format tags for AWS API
            aws_tags = []
            for tag_item in tags:
                for key, value in tag_item.items():
                    aws_tags.append({"Key": key, "Value": value})
            kwargs["Tags"] = aws_tags
        
        response = rds_client.restore_db_cluster_to_point_in_time(**kwargs)
        
        # Format the response
        formatted_cluster = {
            "cluster_id": response.get("DBCluster", {}).get("DBClusterIdentifier"),
            "status": response.get("DBCluster", {}).get("Status"),
            "engine": response.get("DBCluster", {}).get("Engine"),
            "engine_version": response.get("DBCluster", {}).get("EngineVersion"),
        }
        
        return {
            "message": f"Successfully restored DB cluster {db_cluster_identifier} to point in time",
            "formatted_cluster": formatted_cluster,
            "DBCluster": response.get("DBCluster"),
        }
    except Exception as e:
        logger.error(f"Error restoring DB cluster to point in time: {e}")
        return {"error": str(e)}


async def delete_db_cluster_snapshot(
    ctx: Context,
    rds_client,
    readonly: bool,
    db_cluster_snapshot_identifier: str,
    confirmation_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Deletes a DB cluster snapshot.

    Args:
        ctx: MCP context
        rds_client: Boto3 RDS client
        readonly: Whether the server is in read-only mode
        db_cluster_snapshot_identifier: Identifier of the DB cluster snapshot to delete
        confirmation_token: Optional confirmation token for destructive operation

    Returns:
        Response dictionary with status and snapshot details
    """
    if readonly:
        return {
            "message": "[READ-ONLY MODE] Snapshot deletion simulated. "
            f"Would have deleted snapshot {db_cluster_snapshot_identifier}",
            "simulated": True,
        }

    # If no confirmation token provided, request confirmation
    if not confirmation_token:
        # Generate a random token for confirmation
        token = secrets.token_hex(8)
        
        return {
            "requires_confirmation": True,
            "warning": f"You are about to delete snapshot {db_cluster_snapshot_identifier}. This operation cannot be undone.",
            "impact": "Deleting this snapshot will permanently remove it and prevent any future restore operations using this snapshot.",
            "confirmation_token": token,
            "message": f"To confirm deletion, please provide this token as confirmation_token: {token}",
        }
    
    try:
        response = rds_client.delete_db_cluster_snapshot(
            DBClusterSnapshotIdentifier=db_cluster_snapshot_identifier
        )
        
        # Format the response
        formatted_snapshot = {
            "snapshot_id": response.get("DBClusterSnapshot", {}).get("DBClusterSnapshotIdentifier"),
            "cluster_id": response.get("DBClusterSnapshot", {}).get("DBClusterIdentifier"),
            "status": response.get("DBClusterSnapshot", {}).get("Status"),
            "deletion_time": response.get("DBClusterSnapshot", {}).get("SnapshotCreateTime"),
        }
        
        return {
            "message": f"Successfully deleted DB cluster snapshot {db_cluster_snapshot_identifier}",
            "formatted_snapshot": formatted_snapshot,
            "DBClusterSnapshot": response.get("DBClusterSnapshot"),
        }
    except Exception as e:
        logger.error(f"Error deleting DB cluster snapshot: {e}")
        return {"error": str(e)}


async def get_cluster_backups_resource(
    db_cluster_identifier: str,
    rds_client,
) -> str:
    """Get all backups for a specific DB cluster.

    Args:
        db_cluster_identifier: Identifier of the DB cluster
        rds_client: Boto3 RDS client

    Returns:
        JSON string with backup information
    """
    try:
        # Get automated backups
        automated_backups = []
        try:
            auto_backups_response = rds_client.describe_db_cluster_automated_backups(
                DBClusterIdentifier=db_cluster_identifier
            )
            
            for backup in auto_backups_response.get("DBClusterAutomatedBackups", []):
                automated_backups.append(AutomatedBackupModel(
                    backup_id=backup.get("DBClusterAutomatedBackupArn"),
                    cluster_id=backup.get("DBClusterIdentifier"),
                    earliest_time=backup.get("RestoreWindow", {}).get("EarliestTime"),
                    latest_time=backup.get("RestoreWindow", {}).get("LatestTime"),
                    status=backup.get("Status"),
                    engine=backup.get("Engine"),
                    engine_version=backup.get("EngineVersion"),
                    resource_uri=f"aws-rds://db-cluster/{db_cluster_identifier}/backups",
                ))
        except Exception as e:
            logger.error(f"Error fetching automated backups for cluster {db_cluster_identifier}: {e}")
        
        # Get snapshots
        snapshots = []
        try:
            snapshots_response = rds_client.describe_db_cluster_snapshots(
                DBClusterIdentifier=db_cluster_identifier
            )
            
            for snapshot in snapshots_response.get("DBClusterSnapshots", []):
                # Convert tags from AWS format to dict
                tags = {}
                for tag in snapshot.get("TagList", []):
                    tags[tag.get("Key")] = tag.get("Value")
                
                snapshots.append(SnapshotModel(
                    snapshot_id=snapshot.get("DBClusterSnapshotIdentifier"),
                    cluster_id=snapshot.get("DBClusterIdentifier"),
                    creation_time=snapshot.get("SnapshotCreateTime"),
                    status=snapshot.get("Status"),
                    engine=snapshot.get("Engine"),
                    engine_version=snapshot.get("EngineVersion"),
                    port=snapshot.get("Port"),
                    vpc_id=snapshot.get("VpcId"),
                    tags=tags,
                    resource_uri=f"aws-rds://db-cluster/{db_cluster_identifier}/backups",
                ))
        except Exception as e:
            logger.error(f"Error fetching snapshots for cluster {db_cluster_identifier}: {e}")
        
        # Create the combined backup list model
        backup_list = BackupListModel(
            snapshots=snapshots,
            automated_backups=automated_backups,
            count=len(snapshots) + len(automated_backups),
            resource_uri=f"aws-rds://db-cluster/{db_cluster_identifier}/backups",
        )
        
        # Convert to JSON
        return json.dumps(backup_list.model_dump(), default=str)
    
    except Exception as e:
        logger.error(f"Error getting backups for cluster {db_cluster_identifier}: {e}")
        error_response = {
            "error": str(e),
            "cluster_id": db_cluster_identifier,
            "resource_uri": f"aws-rds://db-cluster/{db_cluster_identifier}/backups",
        }
        return json.dumps(error_response)


async def get_all_cluster_backups_resource(
    rds_client,
) -> str:
    """Get all backups across all DB clusters.

    Args:
        rds_client: Boto3 RDS client

    Returns:
        JSON string with backup information for all clusters
    """
    try:
        # Get all clusters first
        clusters_response = rds_client.describe_db_clusters()
        all_snapshots = []
        all_automated_backups = []
        
        # For each cluster, get its backups
        for cluster in clusters_response.get("DBClusters", []):
            cluster_id = cluster.get("DBClusterIdentifier")
            
            # Get automated backups
            try:
                auto_backups_response = rds_client.describe_db_cluster_automated_backups()
                
                for backup in auto_backups_response.get("DBClusterAutomatedBackups", []):
                    if backup.get("DBClusterIdentifier") == cluster_id:
                        all_automated_backups.append(AutomatedBackupModel(
                            backup_id=backup.get("DBClusterAutomatedBackupArn"),
                            cluster_id=backup.get("DBClusterIdentifier"),
                            earliest_time=backup.get("RestoreWindow", {}).get("EarliestTime"),
                            latest_time=backup.get("RestoreWindow", {}).get("LatestTime"),
                            status=backup.get("Status"),
                            engine=backup.get("Engine"),
                            engine_version=backup.get("EngineVersion"),
                            resource_uri=f"aws-rds://db-cluster/backups",
                        ))
            except Exception as e:
                logger.error(f"Error fetching automated backups for cluster {cluster_id}: {e}")
            
            # Get snapshots
            try:
                snapshots_response = rds_client.describe_db_cluster_snapshots(
                    DBClusterIdentifier=cluster_id
                )
                
                for snapshot in snapshots_response.get("DBClusterSnapshots", []):
                    # Convert tags from AWS format to dict
                    tags = {}
                    for tag in snapshot.get("TagList", []):
                        tags[tag.get("Key")] = tag.get("Value")
                    
                    all_snapshots.append(SnapshotModel(
                        snapshot_id=snapshot.get("DBClusterSnapshotIdentifier"),
                        cluster_id=snapshot.get("DBClusterIdentifier"),
                        creation_time=snapshot.get("SnapshotCreateTime"),
                        status=snapshot.get("Status"),
                        engine=snapshot.get("Engine"),
                        engine_version=snapshot.get("EngineVersion"),
                        port=snapshot.get("Port"),
                        vpc_id=snapshot.get("VpcId"),
                        tags=tags,
                        resource_uri=f"aws-rds://db-cluster/backups",
                    ))
            except Exception as e:
                logger.error(f"Error fetching snapshots for cluster {cluster_id}: {e}")
        
        # Create the combined backup list model
        backup_list = BackupListModel(
            snapshots=all_snapshots,
            automated_backups=all_automated_backups,
            count=len(all_snapshots) + len(all_automated_backups),
            resource_uri=f"aws-rds://db-cluster/backups",
        )
        
        # Convert to JSON
        return json.dumps(backup_list.model_dump(), default=str)
    
    except Exception as e:
        logger.error(f"Error getting backups for all clusters: {e}")
        error_response = {
            "error": str(e),
            "resource_uri": f"aws-rds://db-cluster/backups",
        }
        return json.dumps(error_response)


async def get_all_instance_backups_resource(
    rds_client,
) -> str:
    """Get all backups across all DB instances.

    Args:
        rds_client: Boto3 RDS client

    Returns:
        JSON string with backup information for all instances
    """
    try:
        # Get all instances first
        instances_response = rds_client.describe_db_instances()
        all_snapshots = []
        all_automated_backups = []
        
        # For each instance, get its backups
        for instance in instances_response.get("DBInstances", []):
            instance_id = instance.get("DBInstanceIdentifier")
            
            # Get automated backups
            try:
                auto_backups_response = rds_client.describe_db_instance_automated_backups()
                
                for backup in auto_backups_response.get("DBInstanceAutomatedBackups", []):
                    if backup.get("DBInstanceIdentifier") == instance_id:
                        all_automated_backups.append(AutomatedBackupModel(
                            backup_id=backup.get("DBInstanceAutomatedBackupsArn"),
                            cluster_id=backup.get("DBInstanceIdentifier"),  # Using instance ID here
                            earliest_time=backup.get("RestorableTime"),
                            latest_time=backup.get("LatestRestorableTime"),
                            status=backup.get("Status"),
                            engine=backup.get("Engine"),
                            engine_version=backup.get("EngineVersion"),
                            resource_uri=f"aws-rds://db-instance/backups",
                        ))
            except Exception as e:
                logger.error(f"Error fetching automated backups for instance {instance_id}: {e}")
            
            # Get snapshots
            try:
                snapshots_response = rds_client.describe_db_snapshots(
                    DBInstanceIdentifier=instance_id
                )
                
                for snapshot in snapshots_response.get("DBSnapshots", []):
                    # Convert tags from AWS format to dict
                    tags = {}
                    for tag in snapshot.get("TagList", []):
                        tags[tag.get("Key")] = tag.get("Value")
                    
                    all_snapshots.append(SnapshotModel(
                        snapshot_id=snapshot.get("DBSnapshotIdentifier"),
                        cluster_id=snapshot.get("DBInstanceIdentifier"),  # Using instance ID here
                        creation_time=snapshot.get("SnapshotCreateTime"),
                        status=snapshot.get("Status"),
                        engine=snapshot.get("Engine"),
                        engine_version=snapshot.get("EngineVersion"),
                        port=snapshot.get("Port"),
                        vpc_id=snapshot.get("VpcId"),
                        tags=tags,
                        resource_uri=f"aws-rds://db-instance/backups",
                    ))
            except Exception as e:
                logger.error(f"Error fetching snapshots for instance {instance_id}: {e}")
        
        # Create the combined backup list model
        backup_list = BackupListModel(
            snapshots=all_snapshots,
            automated_backups=all_automated_backups,
            count=len(all_snapshots) + len(all_automated_backups),
            resource_uri=f"aws-rds://db-instance/backups",
        )
        
        # Convert to JSON
        return json.dumps(backup_list.model_dump(), default=str)
    
    except Exception as e:
        logger.error(f"Error getting backups for all instances: {e}")
        error_response = {
            "error": str(e),
            "resource_uri": f"aws-rds://db-instance/backups",
        }
        return json.dumps(error_response)


async def get_instance_backups_resource(
    db_instance_identifier: str,
    rds_client,
) -> str:
    """Get all backups for a specific DB instance.

    Args:
        db_instance_identifier: Identifier of the DB instance
        rds_client: Boto3 RDS client

    Returns:
        JSON string with backup information
    """
    try:
        # Get automated backups
        automated_backups = []
        try:
            auto_backups_response = rds_client.describe_db_instance_automated_backups(
                DBInstanceIdentifier=db_instance_identifier
            )
            
            for backup in auto_backups_response.get("DBInstanceAutomatedBackups", []):
                automated_backups.append(AutomatedBackupModel(
                    backup_id=backup.get("DBInstanceAutomatedBackupsArn"),
                    cluster_id=backup.get("DBInstanceIdentifier"),  # Using instance ID here since this is instance backup
                    earliest_time=backup.get("RestorableTime"),
                    latest_time=backup.get("LatestRestorableTime"),
                    status=backup.get("Status"),
                    engine=backup.get("Engine"),
                    engine_version=backup.get("EngineVersion"),
                    resource_uri=f"aws-rds://db-instance/{db_instance_identifier}/backups",
                ))
        except Exception as e:
            logger.error(f"Error fetching automated backups for instance {db_instance_identifier}: {e}")
        
        # Get snapshots
        snapshots = []
        try:
            snapshots_response = rds_client.describe_db_snapshots(
                DBInstanceIdentifier=db_instance_identifier
            )
            
            for snapshot in snapshots_response.get("DBSnapshots", []):
                # Convert tags from AWS format to dict
                tags = {}
                for tag in snapshot.get("TagList", []):
                    tags[tag.get("Key")] = tag.get("Value")
                
                snapshots.append(SnapshotModel(
                    snapshot_id=snapshot.get("DBSnapshotIdentifier"),
                    cluster_id=snapshot.get("DBInstanceIdentifier"),  # Using instance ID here
                    creation_time=snapshot.get("SnapshotCreateTime"),
                    status=snapshot.get("Status"),
                    engine=snapshot.get("Engine"),
                    engine_version=snapshot.get("EngineVersion"),
                    port=snapshot.get("Port"),
                    vpc_id=snapshot.get("VpcId"),
                    tags=tags,
                    resource_uri=f"aws-rds://db-instance/{db_instance_identifier}/backups",
                ))
        except Exception as e:
            logger.error(f"Error fetching snapshots for instance {db_instance_identifier}: {e}")
        
        # Create the combined backup list model
        backup_list = BackupListModel(
            snapshots=snapshots,
            automated_backups=automated_backups,
            count=len(snapshots) + len(automated_backups),
            resource_uri=f"aws-rds://db-instance/{db_instance_identifier}/backups",
        )
        
        # Convert to JSON
        return json.dumps(backup_list.model_dump(), default=str)
    
    except Exception as e:
        logger.error(f"Error getting backups for instance {db_instance_identifier}: {e}")
        error_response = {
            "error": str(e),
            "instance_id": db_instance_identifier,
            "resource_uri": f"aws-rds://db-instance/{db_instance_identifier}/backups",
        }
        return json.dumps(error_response)
