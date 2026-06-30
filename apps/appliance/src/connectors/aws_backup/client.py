"""
AWS Backup connector for R3VP.

Authenticates via IAM role (boto3 default credential chain) and provides
methods to list backup vaults, recovery points, trigger test restores,
and check EC2 instance health post-restore.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class AWSBackupVault:
    vault_name: str
    vault_arn: str
    number_of_recovery_points: int = 0
    creation_date: datetime | None = None


@dataclass
class AWSRecoveryPoint:
    recovery_point_arn: str
    backup_vault_name: str
    resource_arn: str
    resource_type: str = "EC2"  # "EC2", "RDS", "EFS", "DynamoDB", etc.
    creation_date: datetime | None = None
    status: str = "COMPLETED"
    backup_size_bytes: int = 0


@dataclass
class AWSRestoreJob:
    restore_job_id: str
    recovery_point_arn: str
    status: str = "PENDING"
    created_resource_arn: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _try_import_boto3() -> Any:
    try:
        import boto3
        return boto3
    except ImportError:
        return None


class AWSBackupClient:
    """
    Client for AWS Backup and EC2.

    Requires boto3 and valid AWS credentials (IAM role, instance profile,
    or environment variables AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY).
    """

    def __init__(self, region: str = "us-east-1") -> None:
        self._region = region
        self._boto3 = _try_import_boto3()
        self._backup_client: Any = None
        self._ec2_client: Any = None
        self._ssm_client: Any = None

    def connect(self) -> bool:
        """Initialise boto3 clients. Returns True on success."""
        if not self._boto3:
            log.warning("aws_backup.unavailable", reason="boto3 not installed")
            return False
        try:
            session = self._boto3.Session(region_name=self._region)
            self._backup_client = session.client("backup")
            self._ec2_client = session.client("ec2")
            self._ssm_client = session.client("ssm")
            # Quick connectivity check
            self._backup_client.list_backup_vaults(MaxResults=1)
            log.info("aws_backup.connected", region=self._region)
            return True
        except Exception as exc:
            log.error("aws_backup.connect_failed", error=str(exc))
            return False

    def list_vaults(self) -> list[AWSBackupVault]:
        """List all AWS Backup vaults in the configured region."""
        if not self._backup_client:
            return []
        try:
            paginator = self._backup_client.get_paginator("list_backup_vaults")
            vaults = []
            for page in paginator.paginate():
                for v in page.get("BackupVaultList", []):
                    vaults.append(
                        AWSBackupVault(
                            vault_name=v["BackupVaultName"],
                            vault_arn=v["BackupVaultArn"],
                            number_of_recovery_points=v.get("NumberOfRecoveryPoints", 0),
                            creation_date=v.get("CreationDate"),
                        )
                    )
            return vaults
        except Exception as exc:
            log.error("aws_backup.list_vaults_failed", error=str(exc))
            return []

    def list_recovery_points(
        self, vault_name: str, resource_type: str = "EC2"
    ) -> list[AWSRecoveryPoint]:
        """List recovery points in a vault, optionally filtered by resource type."""
        if not self._backup_client:
            return []
        try:
            kwargs: dict = {"BackupVaultName": vault_name, "MaxResults": 100}
            if resource_type:
                kwargs["ByResourceType"] = resource_type
            resp = self._backup_client.list_recovery_points_by_backup_vault(**kwargs)
            points = []
            for rp in resp.get("RecoveryPoints", []):
                points.append(
                    AWSRecoveryPoint(
                        recovery_point_arn=rp["RecoveryPointArn"],
                        backup_vault_name=vault_name,
                        resource_arn=rp.get("ResourceArn", ""),
                        resource_type=rp.get("ResourceType", "EC2"),
                        creation_date=rp.get("CreationDate"),
                        status=rp.get("Status", "COMPLETED"),
                        backup_size_bytes=rp.get("BackupSizeInBytes", 0),
                    )
                )
            return points
        except Exception as exc:
            log.error("aws_backup.list_recovery_points_failed", vault=vault_name, error=str(exc))
            return []

    def start_restore_job(
        self,
        recovery_point_arn: str,
        target_subnet_id: str,
        target_security_group_id: str,
        iam_role_arn: str,
    ) -> AWSRestoreJob | None:
        """
        Restore an EC2 instance from a recovery point into an isolated VPC subnet.

        The target subnet should be in an isolated VPC with no internet gateway
        to ensure the restored instance cannot reach production systems during testing.
        """
        if not self._backup_client:
            return None
        try:
            resp = self._backup_client.start_restore_job(
                RecoveryPointArn=recovery_point_arn,
                Metadata={
                    "SubnetId": target_subnet_id,
                    "SecurityGroupIds": target_security_group_id,
                    "InstanceType": "t3.medium",  # Override to a standard size for testing
                },
                IamRoleArn=iam_role_arn,
                IdempotencyToken=f"r3vp-{recovery_point_arn[-8:]}",
                ResourceType="EC2",
            )
            job_id = resp["RestoreJobId"]
            log.info("aws_backup.restore_started", job_id=job_id)
            return AWSRestoreJob(
                restore_job_id=job_id,
                recovery_point_arn=recovery_point_arn,
                status="PENDING",
            )
        except Exception as exc:
            log.error("aws_backup.restore_failed", rp=recovery_point_arn, error=str(exc))
            return None

    def get_restore_job_status(self, restore_job_id: str) -> AWSRestoreJob | None:
        """Check status of a running restore job."""
        if not self._backup_client:
            return None
        try:
            resp = self._backup_client.describe_restore_job(RestoreJobId=restore_job_id)
            return AWSRestoreJob(
                restore_job_id=restore_job_id,
                recovery_point_arn=resp.get("RecoveryPointArn", ""),
                status=resp.get("Status", "PENDING"),
                created_resource_arn=resp.get("CreatedResourceArn", ""),
            )
        except Exception as exc:
            log.error("aws_backup.get_restore_status_failed", job_id=restore_job_id, error=str(exc))
            return None

    def check_ec2_health(self, instance_id: str) -> dict:
        """Check EC2 instance status and run a SSM health check command."""
        if not self._ec2_client:
            return {"available": False, "reason": "Not connected"}
        try:
            resp = self._ec2_client.describe_instance_status(InstanceIds=[instance_id])
            statuses = resp.get("InstanceStatuses", [])
            if not statuses:
                return {"available": False, "reason": "Instance not found or not running"}
            status = statuses[0]
            instance_ok = status["InstanceStatus"]["Status"] == "ok"
            system_ok = status["SystemStatus"]["Status"] == "ok"
            return {
                "available": True,
                "instance_id": instance_id,
                "state": status["InstanceState"]["Name"],
                "instance_checks_passed": instance_ok,
                "system_checks_passed": system_ok,
                "overall_health": "healthy" if (instance_ok and system_ok) else "degraded",
            }
        except Exception as exc:
            return {"available": False, "reason": str(exc)}

    def terminate_instance(self, instance_id: str) -> bool:
        """Terminate a restored test instance (teardown step)."""
        if not self._ec2_client:
            return False
        try:
            self._ec2_client.terminate_instances(InstanceIds=[instance_id])
            log.info("aws_backup.instance_terminated", instance_id=instance_id)
            return True
        except Exception as exc:
            log.error("aws_backup.terminate_failed", instance_id=instance_id, error=str(exc))
            return False
