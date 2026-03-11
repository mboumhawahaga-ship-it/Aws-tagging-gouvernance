"""
Lambda de cleanup automatique des ressources AWS sans tags obligatoires

Cette fonction :
1. Scanne toutes les ressources AWS (EC2, RDS, S3, Lambda)
2. Vérifie que les tags obligatoires sont présents
3. Supprime les ressources non conformes (avec période de grâce)
4. Envoie des notifications SNS
"""

import boto3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from botocore.exceptions import ClientError

# Configuration
REQUIRED_TAGS = ["Owner", "Squad", "CostCenter", "Environment"]
GRACE_PERIOD_HOURS = int(os.environ.get("GRACE_PERIOD_HOURS", "24"))
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

# Clients AWS
ec2_client = boto3.client('ec2')
rds_client = boto3.client('rds')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')
tagging_client = boto3.client('resourcegroupstaggingapi')


def lambda_handler(event, context):
    """Point d'entrée de la Lambda"""

    print(f"🚀 Démarrage du cleanup - DRY_RUN={DRY_RUN}")
    print(f"⏰ Période de grâce : {GRACE_PERIOD_HOURS} heures")

    results = {
        "scanned": 0,
        "non_compliant": 0,
        "deleted": 0,
        "errors": []
    }

    # Scan des différents types de ressources
    results.update(cleanup_ec2_instances())
    results.update(cleanup_rds_instances())
    results.update(cleanup_s3_buckets())
    results.update(cleanup_lambda_functions())

    # Envoi du rapport
    send_notification(results)

    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }


def check_required_tags(tags: List[Dict[str, str]]) -> tuple[bool, List[str]]:
    """
    Vérifie si tous les tags obligatoires sont présents

    Returns:
        (is_compliant, missing_tags)
    """
    if not tags:
        return False, REQUIRED_TAGS

    tag_keys = [tag.get('Key') for tag in tags]
    missing_tags = [tag for tag in REQUIRED_TAGS if tag not in tag_keys]

    return len(missing_tags) == 0, missing_tags


def is_within_grace_period(creation_time: datetime) -> bool:
    """Vérifie si la ressource est dans la période de grâce"""
    grace_period = timedelta(hours=GRACE_PERIOD_HOURS)
    return datetime.now(creation_time.tzinfo) - creation_time < grace_period


def cleanup_ec2_instances() -> Dict[str, Any]:
    print("🖥️  Scan des instances EC2...")
    results = {"ec2_scanned": 0, "ec2_non_compliant": 0, "ec2_deleted": 0, "ec2_in_grace_period": 0}

    try:
        response = ec2_client.describe_instances()

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                state = instance.get('State', {}).get('Name')
                
                # --- ÉTAPE 1 : ON COMPTE TOUT CE QU'ON VOIT ---
                results["ec2_scanned"] += 1

                # --- ÉTAPE 2 : ON IGNORE CE QUI EST DÉJÀ EN TRAIN DE PARTIR ---
                # C'est ici que Claude intervient : on ne touche pas aux morts
                if state in ['terminated', 'terminating']:
                    continue

                # --- ÉTAPE 3 : ON VÉRIFIE LES TAGS ---
                tags = instance.get('Tags', [])
                is_compliant, missing_tags = check_required_tags(tags)

                if not is_compliant:
                    results["ec2_non_compliant"] += 1
                    
                    # --- ÉTAPE 4 : PÉRIODE DE GRÂCE (on laisse une chance aux nouvelles instances) ---
                    launch_time = instance.get('LaunchTime')
                    if is_within_grace_period(launch_time):
                        results["ec2_in_grace_period"] += 1
                        print(f"⏳ {instance_id} : En sursis (tags manquants : {missing_tags})")
                        continue

                    # --- ÉTAPE 5 : ACTION (Suppression ou Simulation) ---
                    if DRY_RUN:
                        print(f"🔍 SIMULATION : {instance_id} serait supprimée car non-conforme")
                    else:
                        ec2_client.terminate_instances(InstanceIds=[instance_id])
                        print(f"🗑️  {instance_id} TERMINÉE (Tags absents)")
                        results["ec2_deleted"] += 1

    except Exception as e:
        print(f"❌ Erreur EC2 : {str(e)}")
        results["errors"] = [f"EC2: {str(e)}"]

    return results


def cleanup_rds_instances() -> Dict[str, Any]:
    """Nettoie les instances RDS sans tags obligatoires"""

    print("🗄️  Scan des instances RDS...")

    results = {
        "rds_scanned": 0,
        "rds_non_compliant": 0,
        "rds_deleted": 0,
        "rds_in_grace_period": 0
    }

    try:
        response = rds_client.describe_db_instances()

        for db_instance in response['DBInstances']:
            db_id = db_instance['DBInstanceIdentifier']
            db_arn = db_instance['DBInstanceArn']
            creation_time = db_instance.get('InstanceCreateTime')

            results["rds_scanned"] += 1

            # Récupérer les tags
            tags_response = rds_client.list_tags_for_resource(ResourceName=db_arn)
            tags = tags_response.get('TagList', [])

            # Vérifier les tags
            is_compliant, missing_tags = check_required_tags(tags)

            if not is_compliant:
                results["rds_non_compliant"] += 1

                # Vérifier la période de grâce
                if is_within_grace_period(creation_time):
                    results["rds_in_grace_period"] += 1
                    print(f"⏳ {db_id} : En période de grâce (tags manquants : {missing_tags})")
                    continue

                print(f"❌ {db_id} : Non conforme (tags manquants : {missing_tags})")

                # Suppression (ou simulation)
                if DRY_RUN:
                    print(f"🔍 DRY_RUN : {db_id} serait supprimé")
                else:
                    rds_client.delete_db_instance(
                        DBInstanceIdentifier=db_id,
                        SkipFinalSnapshot=True
                    )
                    print(f"🗑️  {db_id} supprimé")
                    results["rds_deleted"] += 1

    except Exception as e:
        print(f"❌ Erreur RDS : {str(e)}")
        results["errors"] = results.get("errors", []) + [f"RDS: {str(e)}"]

    return results


def cleanup_s3_buckets() -> Dict[str, Any]:
    """Nettoie les buckets S3 sans tags obligatoires"""

    print("🪣 Scan des buckets S3...")

    results = {
        "s3_scanned": 0,
        "s3_non_compliant": 0,
        "s3_deleted": 0
    }

    try:
        response = s3_client.list_buckets()

        for bucket in response['Buckets']:
            bucket_name = bucket['Name']
            creation_date = bucket.get('CreationDate')

            results["s3_scanned"] += 1

            try:
                # Récupérer les tags
                tags_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
                tags = tags_response.get('TagSet', [])
            except ClientError as e:
                if e.response['Error']['Code'] in ('NoSuchTagSet', 'NoSuchTagConfiguration'):
                    tags = []
                else:
                    raise

            # Vérifier les tags
            is_compliant, missing_tags = check_required_tags(tags)

            if not is_compliant:
                results["s3_non_compliant"] += 1

                # Vérifier la période de grâce
                if is_within_grace_period(creation_date):
                    print(f"⏳ {bucket_name} : En période de grâce (tags manquants : {missing_tags})")
                    continue

                print(f"❌ {bucket_name} : Non conforme (tags manquants : {missing_tags})")

                # Suppression (ou simulation)
                if DRY_RUN:
                    print(f"🔍 DRY_RUN : {bucket_name} serait supprimé")
                else:
                    # Vider le bucket avant de le supprimer
                    delete_all_objects_in_bucket(bucket_name)
                    s3_client.delete_bucket(Bucket=bucket_name)
                    print(f"🗑️  {bucket_name} supprimé")
                    results["s3_deleted"] += 1

    except Exception as e:
        print(f"❌ Erreur S3 : {str(e)}")
        results["errors"] = results.get("errors", []) + [f"S3: {str(e)}"]

    return results


def delete_all_objects_in_bucket(bucket_name: str):
    """
    Vide un bucket S3 avant suppression.
    Gère les objets standards, les versions et les delete markers
    (nécessaire quand le versioning est activé).
    """
    try:
        # Supprimer toutes les versions d'objets et les delete markers
        paginator = s3_client.get_paginator('list_object_versions')
        pages = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            objects_to_delete = []

            # Versions d'objets
            for version in page.get('Versions', []):
                objects_to_delete.append({
                    'Key': version['Key'],
                    'VersionId': version['VersionId']
                })

            # Delete markers (créés par S3 quand on supprime un objet versionné)
            for marker in page.get('DeleteMarkers', []):
                objects_to_delete.append({
                    'Key': marker['Key'],
                    'VersionId': marker['VersionId']
                })

            if objects_to_delete:
                # delete_objects accepte max 1000 objets par appel
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i + 1000]
                    s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': batch}
                    )

        print(f"✅ Bucket {bucket_name} vidé avec succès")
    except Exception as e:
        print(f"⚠️  Erreur lors du vidage du bucket {bucket_name}: {str(e)}")
        raise


def cleanup_lambda_functions() -> Dict[str, Any]:
    """Nettoie les fonctions Lambda sans tags obligatoires"""

    print("⚡ Scan des fonctions Lambda...")

    results = {
        "lambda_scanned": 0,
        "lambda_non_compliant": 0,
        "lambda_deleted": 0
    }

    try:
        response = lambda_client.list_functions()

        for function in response['Functions']:
            function_name = function['FunctionName']
            function_arn = function['FunctionArn']

            # Ne pas supprimer cette Lambda elle-même !
            if function_name == os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                continue

            results["lambda_scanned"] += 1

            # Récupérer les tags
            tags_response = lambda_client.list_tags(Resource=function_arn)
            tags = [{'Key': k, 'Value': v} for k, v in tags_response.get('Tags', {}).items()]

            # Vérifier les tags
            is_compliant, missing_tags = check_required_tags(tags)

            if not is_compliant:
                results["lambda_non_compliant"] += 1

                print(f"❌ {function_name} : Non conforme (tags manquants : {missing_tags})")

                # Suppression (ou simulation)
                if DRY_RUN:
                    print(f"🔍 DRY_RUN : {function_name} serait supprimée")
                else:
                    lambda_client.delete_function(FunctionName=function_name)
                    print(f"🗑️  {function_name} supprimée")
                    results["lambda_deleted"] += 1

    except Exception as e:
        print(f"❌ Erreur Lambda : {str(e)}")
        results["errors"] = results.get("errors", []) + [f"Lambda: {str(e)}"]

    return results


def send_notification(results: Dict[str, Any]):
    """Envoie un rapport par SNS"""

    if not SNS_TOPIC_ARN:
        print("⚠️  Pas de SNS_TOPIC_ARN configuré, pas d'envoi de notification")
        return

    total_scanned = (
        results.get("ec2_scanned", 0) +
        results.get("rds_scanned", 0) +
        results.get("s3_scanned", 0) +
        results.get("lambda_scanned", 0)
    )

    total_non_compliant = (
        results.get("ec2_non_compliant", 0) +
        results.get("rds_non_compliant", 0) +
        results.get("s3_non_compliant", 0) +
        results.get("lambda_non_compliant", 0)
    )

    total_deleted = (
        results.get("ec2_deleted", 0) +
        results.get("rds_deleted", 0) +
        results.get("s3_deleted", 0) +
        results.get("lambda_deleted", 0)
    )

    message = f"""
🤖 AWS Tagging Governance - Rapport de cleanup

📊 Résumé :
- Ressources scannées : {total_scanned}
- Non conformes : {total_non_compliant}
- Supprimées : {total_deleted}

📝 Détails :
- EC2 : {results.get("ec2_scanned", 0)} scannées, \
{results.get("ec2_non_compliant", 0)} non conformes, \
{results.get("ec2_deleted", 0)} supprimées
- RDS : {results.get("rds_scanned", 0)} scannées, \
{results.get("rds_non_compliant", 0)} non conformes, \
{results.get("rds_deleted", 0)} supprimées
- S3 : {results.get("s3_scanned", 0)} scannés, \
{results.get("s3_non_compliant", 0)} non conformes, \
{results.get("s3_deleted", 0)} supprimés
- Lambda : {results.get("lambda_scanned", 0)} scannées, \
{results.get("lambda_non_compliant", 0)} non conformes, \
{results.get("lambda_deleted", 0)} supprimées

⚙️  Mode : {"🔍 DRY_RUN (simulation)" if DRY_RUN else "🗑️ PRODUCTION (suppression réelle)"}

⏰ Date : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    if results.get("errors"):
        message += "\n\n❌ Erreurs :\n" + "\n".join(results["errors"])

    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="AWS Tagging Governance - Rapport de cleanup",
            Message=message
        )
        print("✅ Notification envoyée")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de la notification : {str(e)}")
