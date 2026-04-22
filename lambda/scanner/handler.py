"""
Scanner - Détecte les ressources non conformes et lance une Step Function par ressource.
"""

import os
import json
import boto3
from datetime import datetime

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger(service="governance-scanner")
tracer = Tracer(service="governance-scanner")
metrics = Metrics(namespace="TagGovernance", service="governance-scanner")

from shared.config import REQUIRED_TAGS, check_tags, get_tag_value

REGION = os.environ.get("AWS_REGION", "eu-west-1")
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]

ec2 = boto3.client("ec2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
lmb = boto3.client("lambda", region_name=REGION)
sfn = boto3.client("stepfunctions", region_name=REGION)
sts = boto3.client("sts")


def get_account_id() -> str:
    return sts.get_caller_identity()["Account"]





def build_payload(resource_id: str, resource_type: str, resource_arn: str, tags: list, missing: list) -> dict:
    return {
        "resource_id": resource_id,
        "resource_type": resource_type,
        "resource_arn": resource_arn,
        "owner": get_tag_value(tags, "Owner"),
        "squad": get_tag_value(tags, "Squad"),
        "missing_tags": missing,
        "account_id": get_account_id(),
        "region": REGION,
        "detected_at": datetime.utcnow().isoformat() + "Z",
    }


@tracer.capture_method
def scan_ec2() -> list:
    resources = []
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                if instance.get("State", {}).get("Name") in ["terminated", "terminating"]:
                    continue
                tags = instance.get("Tags", [])
                compliant, missing = check_tags(tags)
                if not compliant:
                    resources.append(build_payload(
                        resource_id=instance["InstanceId"],
                        resource_type="ec2",
                        resource_arn=f"arn:aws:ec2:{REGION}:{get_account_id()}:instance/{instance['InstanceId']}",
                        tags=tags,
                        missing=missing,
                    ))
    return resources


@tracer.capture_method
def scan_rds() -> list:
    resources = []
    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            if db["DBInstanceStatus"] in ["deleting", "deleted"]:
                continue
            tags_resp = rds.list_tags_for_resource(ResourceName=db["DBInstanceArn"])
            tags = tags_resp.get("TagList", [])
            compliant, missing = check_tags(tags)
            if not compliant:
                resources.append(build_payload(
                    resource_id=db["DBInstanceIdentifier"],
                    resource_type="rds",
                    resource_arn=db["DBInstanceArn"],
                    tags=tags,
                    missing=missing,
                ))
    return resources


@tracer.capture_method
def scan_s3() -> list:
    resources = []
    for bucket in s3.list_buckets().get("Buckets", []):
        name = bucket["Name"]
        try:
            tags = s3.get_bucket_tagging(Bucket=name).get("TagSet", [])
        except s3.exceptions.ClientError:
            tags = []
        compliant, missing = check_tags(tags)
        if not compliant:
            resources.append(build_payload(
                resource_id=name,
                resource_type="s3",
                resource_arn=f"arn:aws:s3:::{name}",
                tags=tags,
                missing=missing,
            ))
    return resources


@tracer.capture_method
def scan_lambda() -> list:
    resources = []
    paginator = lmb.get_paginator("list_functions")
    for page in paginator.paginate():
        for func in page["Functions"]:
            if func["FunctionName"] == os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                continue
            tags_resp = lmb.list_tags(Resource=func["FunctionArn"])
            tags = [{"Key": k, "Value": v} for k, v in tags_resp.get("Tags", {}).items()]
            compliant, missing = check_tags(tags)
            if not compliant:
                resources.append(build_payload(
                    resource_id=func["FunctionName"],
                    resource_type="lambda",
                    resource_arn=func["FunctionArn"],
                    tags=tags,
                    missing=missing,
                ))
    return resources


@tracer.capture_method
def launch_state_machine(payload: dict):
    name = f"governance-{payload['resource_type']}-{payload['resource_id']}-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
    # Step Functions n'accepte pas certains caractères dans le nom
    name = name.replace("/", "-").replace(":", "-")[:80]
    sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=name,
        input=json.dumps(payload),
    )
    logger.info("State machine lancée", extra={"resource_id": payload["resource_id"], "execution_name": name})


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event, context):
    non_compliant = []
    non_compliant += scan_ec2()
    non_compliant += scan_rds()
    non_compliant += scan_s3()
    non_compliant += scan_lambda()

    metrics.add_metric(name="NonCompliantResources", unit=MetricUnit.Count, value=len(non_compliant))
    logger.info(f"{len(non_compliant)} ressources non conformes détectées")

    launched = 0
    for resource in non_compliant:
        try:
            launch_state_machine(resource)
            launched += 1
        except Exception as e:
            logger.error("Échec lancement state machine", extra={"resource_id": resource["resource_id"], "error": str(e)})

    metrics.add_metric(name="StateMachinesLaunched", unit=MetricUnit.Count, value=launched)

    return {"non_compliant": len(non_compliant), "launched": launched}
