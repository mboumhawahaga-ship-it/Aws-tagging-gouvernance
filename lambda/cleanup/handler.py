"""
🤖 MODULE DE GOUVERNANCE AWS - CLEANUP AUTOMATIQUE
Cette Lambda scanne EC2, RDS, S3 et Lambda pour supprimer les ressources 
non conformes aux tags obligatoires après une période de grâce.
"""

import boto3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
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
    print(f"🚀 Démarrage du cleanup - DRY_RUN={DRY_RUN}")
    
    # Initialisation des résultats globaux
    global_results = {
        "ec2": {}, "rds": {}, "s3": {}, "lambda": {},
        "errors": []
    }

    # Exécution des scans
    global_results["ec2"] = cleanup_ec2_instances()
    global_results["rds"] = cleanup_rds_instances()
    global_results["s3"] = cleanup_s3_buckets()
    global_results["lambda"] = cleanup_lambda_functions()

    # Envoi du rapport final
    send_notification(global_results)

    return {
        'statusCode': 200,
        'body': json.dumps(global_results, default=str)
    }

# --- LOGIQUE EC2 ---
def cleanup_ec2_instances():
    print("🖥️  Scan EC2...")
    res = {"scanned": 0, "non_compliant": 0, "deleted": 0}
    try:
        response = ec2_client.describe_instances()
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                state = instance.get('State', {}).get('Name')
                res["scanned"] += 1

                if state in ['terminated', 'terminating']: continue

                compliant, _ = check_required_tags(instance.get('Tags', []))
                if not compliant:
                    res["non_compliant"] += 1
                    if is_within_grace_period(instance.get('LaunchTime')): continue
                    
                    if not DRY_RUN:
                        ec2_client.terminate_instances(InstanceIds=[instance_id])
                        res["deleted"] += 1
    except Exception as e: res["errors"] = str(e)
    return res

# --- LOGIQUE RDS ---
def cleanup_rds_instances():
    print("🗄️  Scan RDS...")
    res = {"scanned": 0, "non_compliant": 0, "deleted": 0}
    try:
        response = rds_client.describe_db_instances()
        for db in response['DBInstances']:
            db_id = db['DBInstanceIdentifier']
            res["scanned"] += 1
            if db['DBInstanceStatus'] in ['deleting', 'deleted']: continue

            tags_resp = rds_client.list_tags_for_resource(ResourceName=db['DBInstanceArn'])
            compliant, _ = check_required_tags(tags_resp.get('TagList', []))
            
            if not compliant:
                res["non_compliant"] += 1
                if is_within_grace_period(db.get('InstanceCreateTime')): continue
                if not DRY_RUN:
                    rds_client.delete_db_instance(DBInstanceIdentifier=db_id, SkipFinalSnapshot=True)
                    res["deleted"] += 1
    except Exception as e: res["errors"] = str(e)
    return res

# --- LOGIQUE S3 ---
def cleanup_s3_buckets():
    print("🪣  Scan S3...")
    res = {"scanned": 0, "non_compliant": 0, "deleted": 0}
    try:
        response = s3_client.list_buckets()
        for bucket in response['Buckets']:
            name = bucket['Name']
            res["scanned"] += 1
            
            try:
                tags = s3_client.get_bucket_tagging(Bucket=name).get('TagSet', [])
            except ClientError: tags = []

            compliant, _ = check_required_tags(tags)
            if not compliant:
                res["non_compliant"] += 1
                if is_within_grace_period(bucket.get('CreationDate')): continue
                if not DRY_RUN:
                    delete_all_objects_in_bucket(name)
                    s3_client.delete_bucket(Bucket=name)
                    res["deleted"] += 1
    except Exception as e: res["errors"] = str(e)
    return res

# --- LOGIQUE LAMBDA ---
def cleanup_lambda_functions():
    print("⚡ Scan Lambda...")
    res = {"scanned": 0, "non_compliant": 0, "deleted": 0}
    try:
        response = lambda_client.list_functions()
        for f in response['Functions']:
            name = f['FunctionName']
            if name == os.environ.get('AWS_LAMBDA_FUNCTION_NAME'): continue
            res["scanned"] += 1

            tags = lambda_client.list_tags(Resource=f['FunctionArn']).get('Tags', {})
            formatted_tags = [{'Key': k, 'Value': v} for k, v in tags.items()]
            
            compliant, _ = check_required_tags(formatted_tags)
            if not compliant:
                res["non_compliant"] += 1
                # Note: Lambda n'a pas de date de création simple dans l'API de base, 
                # on se base sur la conformité immédiate ou on peut ignorer la période de grâce ici.
                if not DRY_RUN:
                    lambda_client.delete_function(FunctionName=name)
                    res["deleted"] += 1
    except Exception as e: res["errors"] = str(e)
    return res

# --- UTILS ---
def check_required_tags(tags: List[Dict]) -> tuple[bool, List[str]]:
    keys = [t.get('Key') for t in tags] if tags else []
    missing = [t for t in REQUIRED_TAGS if t not in keys]
    return len(missing) == 0, missing

def is_within_grace_period(creation_time: datetime) -> bool:
    if not creation_time: return False
    return datetime.now(creation_time.tzinfo) - creation_time < timedelta(hours=GRACE_PERIOD_HOURS)

def delete_all_objects_in_bucket(bucket_name):
    # Logique simplifiée pour vider le bucket (Versions + Objets)
    paginator = s3_client.get_paginator('list_object_versions')
    for page in paginator.paginate(Bucket=bucket_name):
        obj_to_del = [{'Key': v['Key'], 'VersionId': v['VersionId']} for v in page.get('Versions', []) + page.get('DeleteMarkers', [])]
        if obj_to_del: s3_client.delete_objects(Bucket=bucket_name, Delete={'Objects': obj_to_del})

def send_notification(res):
    if not SNS_TOPIC_ARN: return
    msg = f"Rapport Cleanup AWS ({'DRY_RUN' if DRY_RUN else 'PROD'})\n\n"
    for svc in ['ec2', 'rds', 's3', 'lambda']:
        msg += f"- {svc.upper()}: {res[svc].get('scanned', 0)} scannés, {res[svc].get('deleted', 0)} supprimés\n"
    sns_client.publish(TopicArn=SNS_TOPIC_ARN, Subject="AWS Governance Report", Message=msg)
