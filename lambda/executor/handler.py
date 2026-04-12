"""
Executor - Actions destructives : freeze, resume, delete.
Reçoit une action : freeze | resume | delete
"""

import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger(service="governance-executor")
tracer = Tracer(service="governance-executor")
metrics = Metrics(namespace="TagGovernance", service="governance-executor")

REGION = os.environ.get("AWS_REGION", "eu-west-1")
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"

ec2 = boto3.client("ec2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
lmb = boto3.client("lambda", region_name=REGION)


# ========================================
# FREEZE
# ========================================

@tracer.capture_method
def freeze_ec2(resource_id: str):
    logger.info("Freeze EC2", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        ec2.stop_instances(InstanceIds=[resource_id])
    metrics.add_metric(name="FreezeEC2", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def freeze_rds(resource_id: str, resource_arn: str):
    logger.info("Freeze RDS", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        snapshot_id = f"governance-{resource_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        ec2.create_db_snapshot = None  # guard
        rds.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=resource_id,
            Tags=[{"Key": "ManagedBy", "Value": "GovernanceAutomation"}],
        )
        logger.info("Snapshot RDS créé", extra={"snapshot_id": snapshot_id})
        rds.stop_db_instance(DBInstanceIdentifier=resource_id)
    metrics.add_metric(name="FreezeRDS", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def freeze_s3(resource_id: str):
    """Bloque tout accès public + active le versioning."""
    logger.info("Freeze S3", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        s3.put_public_access_block(
            Bucket=resource_id,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        s3.put_bucket_versioning(
            Bucket=resource_id,
            VersioningConfiguration={"Status": "Enabled"},
        )
        logger.info("S3 accès public bloqué + versioning activé", extra={"bucket": resource_id})
    metrics.add_metric(name="FreezeS3", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def freeze_lambda(resource_arn: str, resource_id: str):
    """Met la concurrence à 0 — la fonction existe mais ne peut plus s'exécuter."""
    logger.info("Freeze Lambda", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        lmb.put_function_concurrency(
            FunctionName=resource_arn,
            ReservedConcurrentExecutions=0,
        )
    metrics.add_metric(name="FreezeLambda", unit=MetricUnit.Count, value=1)


# ========================================
# RESUME
# ========================================

@tracer.capture_method
def resume_ec2(resource_id: str):
    logger.info("Resume EC2", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        ec2.start_instances(InstanceIds=[resource_id])
    metrics.add_metric(name="ResumeEC2", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def resume_rds(resource_id: str):
    logger.info("Resume RDS", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        rds.start_db_instance(DBInstanceIdentifier=resource_id)
    metrics.add_metric(name="ResumeRDS", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def resume_lambda(resource_arn: str, resource_id: str):
    """Supprime la limite de concurrence → la fonction reprend normalement."""
    logger.info("Resume Lambda", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        lmb.delete_function_concurrency(FunctionName=resource_arn)
    metrics.add_metric(name="ResumeLambda", unit=MetricUnit.Count, value=1)


# S3 : pas de resume — on ne débloque pas l'accès public automatiquement
def resume_s3(resource_id: str):
    logger.info("Resume S3 : aucune action (accès public reste bloqué par sécurité)", extra={"resource_id": resource_id})


# ========================================
# DELETE
# ========================================

@tracer.capture_method
def delete_ec2(resource_id: str):
    logger.info("Delete EC2", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        ec2.terminate_instances(InstanceIds=[resource_id])
    metrics.add_metric(name="DeleteEC2", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def delete_rds(resource_id: str):
    """Snapshot final obligatoire avant suppression."""
    logger.info("Delete RDS", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        snapshot_id = f"governance-final-{resource_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        rds.delete_db_instance(
            DBInstanceIdentifier=resource_id,
            SkipFinalSnapshot=False,
            FinalDBSnapshotIdentifier=snapshot_id,
        )
        logger.info("RDS supprimée avec snapshot final", extra={"snapshot_id": snapshot_id})
    metrics.add_metric(name="DeleteRDS", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def delete_lambda(resource_id: str):
    logger.info("Delete Lambda", extra={"resource_id": resource_id, "dry_run": DRY_RUN})
    if not DRY_RUN:
        lmb.delete_function(FunctionName=resource_id)
    metrics.add_metric(name="DeleteLambda", unit=MetricUnit.Count, value=1)


def delete_s3(resource_id: str):
    """S3 : on ne supprime jamais automatiquement."""
    logger.warning("Delete S3 ignoré — suppression manuelle requise", extra={"bucket": resource_id})
    metrics.add_metric(name="DeleteS3Skipped", unit=MetricUnit.Count, value=1)


# ========================================
# DISPATCHER
# ========================================

FREEZE_MAP = {
    "ec2": lambda r: freeze_ec2(r["resource_id"]),
    "rds": lambda r: freeze_rds(r["resource_id"], r["resource_arn"]),
    "s3": lambda r: freeze_s3(r["resource_id"]),
    "lambda": lambda r: freeze_lambda(r["resource_arn"], r["resource_id"]),
}

RESUME_MAP = {
    "ec2": lambda r: resume_ec2(r["resource_id"]),
    "rds": lambda r: resume_rds(r["resource_id"]),
    "s3": lambda r: resume_s3(r["resource_id"]),
    "lambda": lambda r: resume_lambda(r["resource_arn"], r["resource_id"]),
}

DELETE_MAP = {
    "ec2": lambda r: delete_ec2(r["resource_id"]),
    "rds": lambda r: delete_rds(r["resource_id"]),
    "s3": lambda r: delete_s3(r["resource_id"]),
    "lambda": lambda r: delete_lambda(r["resource_id"]),
}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event, context):
    action = event.get("action")
    resource = event.get("resource", event)
    resource_type = resource.get("resource_type")

    logger.info("Action reçue", extra={"action": action, "resource_type": resource_type, "resource_id": resource.get("resource_id")})

    dispatch = {"freeze": FREEZE_MAP, "resume": RESUME_MAP, "delete": DELETE_MAP}.get(action)

    if not dispatch:
        raise ValueError(f"Action inconnue : {action}")

    handler_fn = dispatch.get(resource_type)
    if not handler_fn:
        raise ValueError(f"Type de ressource non supporté : {resource_type}")

    handler_fn(resource)

    return {"action": action, "resource_id": resource["resource_id"], "dry_run": DRY_RUN, "status": "ok"}
