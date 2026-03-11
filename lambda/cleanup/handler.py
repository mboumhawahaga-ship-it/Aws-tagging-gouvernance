"""
🤖 MODULE DE GOUVERNANCE AWS - CLEANUP AUTOMATIQUE
Scanne EC2, RDS, S3 et Lambda. Supprime le non-conforme après une période de grâce.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import boto3
from botocore.exceptions import ClientError

# --- CONFIGURATION ---
REQUIRED_TAGS = ["Owner", "Squad", "CostCenter", "Environment"]
GRACE_PERIOD_HOURS = int(os.environ.get("GRACE_PERIOD_HOURS", "24"))
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

# --- CLIENTS AWS ---
ec2_client = boto3.client('ec2')
rds_client = boto3.client('rds')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')


def lambda_handler(event, context):
    """Point d'entrée principal de la Lambda."""
    print(f"🚀 Démarrage du cleanup - DRY_RUN={DRY_RUN}")

    global_results = {
        "ec2": {}, "rds": {}, "s3": {}, "lambda": {},
        "errors": []
    }

    global_results["ec2"] = cleanup_ec2_instances()
    global_results["rds"] = cleanup_rds_instances()
    global_results["s3"] = cleanup_s3_buckets()
    global_results["lambda"] = cleanup_lambda_functions()

    send_notification(global_results)

    return {
        'statusCode': 200,
        'body': json.dumps(global_results, default=str)
    }


def cleanup_ec2_instances() -> Dict[str, Any]:
    """Nettoie les instances EC2 non conformes."""
    print("🖥️  Scan EC2...")
    res = {
        "scanned": 0, "already_terminated": 0,
        "non_compliant": 0, "deleted": 0, "in_grace_period": 0
    }
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    state = instance.get('State', {}).get('Name')
                    res["scanned"] += 1

                    if state in ['terminated', 'terminating']:
                        res["already_terminated"] += 1
                        continue

                    compliant, _ = check_required_tags(instance.get('Tags', []))
                    if not compliant:
                        res["non_compliant"] += 1
                        if is_within_grace_period(instance.get('LaunchTime')):
                            res["in_grace_period"] += 1
                            continue

                        if not DRY_RUN:
                            ec2_client.terminate_instances(
                                InstanceIds=[instance_id]
                            )
                            res["deleted"] += 1
    except Exception as e:
        res["errors"] = str(e)
    return res


def cleanup_rds_instances() -> Dict[str, Any]:
    """Nettoie les instances RDS non conformes."""
    print("🗄️  Scan RDS...")
    res = {
        "scanned": 0, "already_deleted": 0,
        "non_compliant": 0, "deleted": 0, "in_grace_period": 0
    }
    try:
        response = rds_client.describe_db_instances()
        for db in response['DBInstances']:
            res["scanned"] += 1
            if db['DBInstanceStatus'] in ['deleting', 'deleted']:
                res["already_deleted"] += 1
                continue

            t_resp = rds_client.list_tags_for_resource(
                ResourceName=db['DBInstanceArn']
            )
            compliant, _ = check_required_tags(t_resp.get('TagList', []))

            if not compliant:
                res["non_compliant"] += 1
                create_time = db.get('InstanceCreateTime')
                if is_within_grace_period(create_time):
                    res["in_grace_period"] += 1
                    continue
                if not DRY_RUN:
                    rds_client.delete_db_instance(
                        DBInstanceIdentifier=db['DBInstanceIdentifier'],
                        SkipFinalSnapshot=True
                    )
                    res["deleted"] += 1
    except Exception as e:
        res["errors"] = str(e)
    return res


def cleanup_s3_buckets() -> Dict[str, Any]:
    """Nettoie les buckets S3 non conformes."""
    print("🪣  Scan S3...")
    res = {"scanned": 0, "non_compliant": 0, "deleted": 0}
    try:
        for b in s3_client.list_buckets()['Buckets']:
            name = b['Name']
            res["scanned"] += 1
            try:
                tags = s3_client.get_bucket_tagging(
                    Bucket=name
                ).get('TagSet', [])
            except ClientError:
                tags = []

            compliant, _ = check_required_tags(tags)
            if not compliant:
                res["non_compliant"] += 1
                if is_within_grace_period(b.get('CreationDate')):
                    continue
                if not DRY_RUN:
                    delete_all_objects_in_bucket(name)
                    s3_client.delete_bucket(Bucket=name)
                    res["deleted"] += 1
    except Exception as e:
        res["errors"] = str(e)
    return res


def cleanup_lambda_functions() -> Dict[str, Any]:
    """Nettoie les fonctions Lambda non conformes."""
    print("⚡ Scan Lambda...")
    res = {"scanned": 0, "non_compliant": 0, "deleted": 0}
    try:
        for f in lambda_client.list_functions()['Functions']:
            name = f['FunctionName']
            if name == os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                continue
            res["scanned"] += 1

            t_resp = lambda_client.list_tags(Resource=f['FunctionArn'])
            tags = t_resp.get('Tags', {})
            fmt_tags = [{'Key': k, 'Value': v} for k, v in tags.items()]

            compliant, _ = check_required_tags(fmt_tags)
            if not compliant:
                res["non_compliant"] += 1
                if not DRY_RUN:
                    lambda_client.delete_function(FunctionName=name)
                    res["deleted"] += 1
    except Exception as e:
        res["errors"] = str(e)
    return res


def check_required_tags(tags: List[Dict]) -> tuple[bool, List[str]]:
    """Vérifie la présence des tags obligatoires."""
    keys = [t.get('Key') for t in tags] if tags else []
    missing = [t for t in REQUIRED_TAGS if t not in keys]
    return len(missing) == 0, missing


def is_within_grace_period(creation_time: datetime) -> bool:
    """Vérifie si la ressource est encore sous période de grâce."""
    if not creation_time:
        return False
    delta = timedelta(hours=GRACE_PERIOD_HOURS)
    return datetime.now(creation_time.tzinfo) - creation_time < delta


def delete_all_objects_in_bucket(bucket_name: str):
    """Vide un bucket S3 de tous ses objets et versions."""
    paginator = s3_client.get_paginator('list_object_versions')
    for page in paginator.paginate(Bucket=bucket_name):
        versions = page.get('Versions', [])
        markers = page.get('DeleteMarkers', [])
        objs = [
            {'Key': v['Key'], 'VersionId': v['VersionId']}
            for v in versions + markers
        ]
        if objs:
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objs}
            )


def send_notification(res: Dict):
    """Envoie le rapport final via SNS."""
    if not SNS_TOPIC_ARN:
        return
    mode = 'SIMULATION' if DRY_RUN else 'PROD'
    msg = f"Rapport Cleanup AWS ({mode})\n\n"
    for s in ['ec2', 'rds', 's3', 'lambda']:
        msg += f"- {s.upper()}: {res[s].get('scanned', 0)} vus, "
        msg += f"{res[s].get('deleted', 0)} supprimés\n"
    sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="AWS Governance Report",
        Message=msg
    )
