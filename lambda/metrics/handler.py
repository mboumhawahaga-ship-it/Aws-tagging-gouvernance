"""
Lambda de collecte de metriques pour le dashboard Grafana

Cette fonction :
1. Scanne les ressources AWS (EC2, RDS, S3, Lambda) pour la conformite des tags
2. Interroge Cost Explorer pour les couts par tag
3. Publie des metriques CloudWatch custom dans les namespaces :
   - TagCompliance  : pourcentage de conformite + ressources non conformes
   - ResourceCount  : nombre de ressources par type
   - AutoShutdown   : economies estimees
   - CostExplorer   : couts par Squad, CostCenter, service
4. Executee toutes les 6 heures via EventBridge
"""

import boto3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

# Configuration
REQUIRED_TAGS = ["Owner", "Squad", "CostCenter", "Environment"]
REGION = os.environ.get("AWS_REGION", "eu-west-1")

# Clients AWS
ec2_client = boto3.client('ec2', region_name=REGION)
rds_client = boto3.client('rds', region_name=REGION)
s3_client = boto3.client('s3', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)
cloudwatch = boto3.client('cloudwatch', region_name=REGION)
ce_client = boto3.client('ce', region_name="us-east-1")


def lambda_handler(event, context):
    """Point d'entree principal"""

    print("Demarrage de la collecte de metriques")

    results = {}

    # 1. Metriques de conformite des tags
    compliance_data = collect_tag_compliance()
    publish_tag_compliance_metrics(compliance_data)
    results["tag_compliance"] = compliance_data["summary"]

    # 2. Metriques de comptage des ressources
    resource_counts = compliance_data["counts"]
    publish_resource_count_metrics(resource_counts)
    results["resource_counts"] = resource_counts

    # 3. Metriques AutoShutdown (economies estimees)
    savings = calculate_autoshutdown_savings(compliance_data["resources"])
    publish_autoshutdown_metrics(savings)
    results["estimated_savings"] = savings

    # 4. Metriques Cost Explorer (couts par tag)
    cost_data = collect_cost_explorer_data()
    if cost_data:
        publish_cost_explorer_metrics(cost_data)
        results["cost_data"] = "published"
    else:
        results["cost_data"] = "unavailable (Cost Allocation Tags not yet active)"

    print(f"Collecte terminee : {json.dumps(results, default=str)}")

    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }


# ========================================
# COLLECTE DES DONNEES
# ========================================

def check_required_tags(tags: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
    """Verifie si tous les tags obligatoires sont presents"""
    if not tags:
        return False, REQUIRED_TAGS

    tag_keys = [tag.get('Key') for tag in tags]
    missing_tags = [tag for tag in REQUIRED_TAGS if tag not in tag_keys]

    return len(missing_tags) == 0, missing_tags


def get_tag_value(tags: List[Dict[str, str]], key: str) -> str:
    """Recupere la valeur d'un tag par sa cle"""
    for tag in tags:
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def collect_tag_compliance() -> Dict[str, Any]:
    """Scanne toutes les ressources et collecte les donnees de conformite"""

    all_resources = []
    counts = {"EC2": 0, "RDS": 0, "S3": 0, "Lambda": 0}
    total = 0
    compliant = 0

    # --- EC2 ---
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    state = instance.get('State', {}).get('Name')
                    if state in ['terminated', 'terminating']:
                        continue
                    counts["EC2"] += 1
                    total += 1
                    tags = instance.get('Tags', [])
                    is_ok, missing = check_required_tags(tags)
                    if is_ok:
                        compliant += 1
                    all_resources.append({
                        "type": "EC2",
                        "id": instance['InstanceId'],
                        "name": get_tag_value(tags, 'Name'),
                        "compliant": is_ok,
                        "missing_tags": missing,
                        "tags": tags
                    })
    except Exception as e:
        print(f"Erreur scan EC2 : {e}")

    # --- RDS ---
    try:
        paginator = rds_client.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for db in page['DBInstances']:
                counts["RDS"] += 1
                total += 1
                tags_response = rds_client.list_tags_for_resource(ResourceName=db['DBInstanceArn'])
                tags = tags_response.get('TagList', [])
                is_ok, missing = check_required_tags(tags)
                if is_ok:
                    compliant += 1
                all_resources.append({
                    "type": "RDS",
                    "id": db['DBInstanceIdentifier'],
                    "name": db['DBInstanceIdentifier'],
                    "compliant": is_ok,
                    "missing_tags": missing,
                    "tags": tags
                })
    except Exception as e:
        print(f"Erreur scan RDS : {e}")

    # --- S3 ---
    try:
        response = s3_client.list_buckets()
        for bucket in response['Buckets']:
            counts["S3"] += 1
            total += 1
            try:
                tags_response = s3_client.get_bucket_tagging(Bucket=bucket['Name'])
                tags = tags_response.get('TagSet', [])
            except Exception:
                tags = []
            is_ok, missing = check_required_tags(tags)
            if is_ok:
                compliant += 1
            all_resources.append({
                "type": "S3",
                "id": bucket['Name'],
                "name": bucket['Name'],
                "compliant": is_ok,
                "missing_tags": missing,
                "tags": tags
            })
    except Exception as e:
        print(f"Erreur scan S3 : {e}")

    # --- Lambda ---
    try:
        paginator = lambda_client.get_paginator('list_functions')
        for page in paginator.paginate():
            for func in page['Functions']:
                # Ne pas compter les Lambdas de governance elles-memes
                if func['FunctionName'] == os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                    continue
                counts["Lambda"] += 1
                total += 1
                tags_response = lambda_client.list_tags(Resource=func['FunctionArn'])
                tags = [{'Key': k, 'Value': v} for k, v in tags_response.get('Tags', {}).items()]
                is_ok, missing = check_required_tags(tags)
                if is_ok:
                    compliant += 1
                all_resources.append({
                    "type": "Lambda",
                    "id": func['FunctionName'],
                    "name": func['FunctionName'],
                    "compliant": is_ok,
                    "missing_tags": missing,
                    "tags": tags
                })
    except Exception as e:
        print(f"Erreur scan Lambda : {e}")

    percentage = (compliant / total * 100) if total > 0 else 100

    return {
        "resources": all_resources,
        "counts": counts,
        "summary": {
            "total": total,
            "compliant": compliant,
            "non_compliant": total - compliant,
            "percentage": round(percentage, 1)
        }
    }


def calculate_autoshutdown_savings(resources: List[Dict]) -> float:
    """
    Estime les economies liees aux ressources avec AutoShutdown=true.
    Hypothese : arret 12h/jour = 50% d'economie sur le cout horaire.
    """
    # Prix horaires approximatifs (on-demand, eu-west-1)
    hourly_prices = {
        "t3.micro": 0.0104,
        "t3.small": 0.0208,
        "t3.medium": 0.0416,
        "db.t3.micro": 0.018,
        "db.t3.small": 0.036,
    }

    savings = 0.0

    for resource in resources:
        auto_shutdown = get_tag_value(resource.get("tags", []), "AutoShutdown")
        if auto_shutdown != "true":
            continue

        if resource["type"] == "EC2":
            # Recuperer le type d'instance
            try:
                resp = ec2_client.describe_instances(InstanceIds=[resource["id"]])
                instance_type = resp['Reservations'][0]['Instances'][0].get('InstanceType', 't3.micro')
                hourly = hourly_prices.get(instance_type, 0.0104)
                # 12h d'arret par jour * 30 jours
                savings += hourly * 12 * 30
            except Exception:
                savings += hourly_prices["t3.micro"] * 12 * 30

        elif resource["type"] == "RDS":
            try:
                resp = rds_client.describe_db_instances(
                    DBInstanceIdentifier=resource["id"]
                )
                instance_class = resp['DBInstances'][0].get('DBInstanceClass', 'db.t3.micro')
                hourly = hourly_prices.get(instance_class, 0.018)
                savings += hourly * 12 * 30
            except Exception:
                savings += hourly_prices["db.t3.micro"] * 12 * 30

    return round(savings, 2)


def collect_cost_explorer_data() -> Dict[str, Any]:
    """Collecte les couts via Cost Explorer API, groupes par tag"""

    today = datetime.now()
    start_date = (today.replace(day=1)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    # Eviter une requete sur un seul jour (le 1er du mois)
    if start_date == end_date:
        start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')

    result = {}

    # --- Couts par Squad ---
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'TAG', 'Key': 'Squad'}]
        )
        result["by_squad"] = []
        for group_result in response.get('ResultsByTime', []):
            for group in group_result.get('Groups', []):
                tag_value = group['Keys'][0].replace('Squad$', '')
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                if tag_value and cost > 0:
                    result["by_squad"].append({"squad": tag_value, "cost": cost})
    except Exception as e:
        print(f"Cost Explorer (Squad) non disponible : {e}")

    # --- Couts par CostCenter ---
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'TAG', 'Key': 'CostCenter'}]
        )
        result["by_cost_center"] = []
        for group_result in response.get('ResultsByTime', []):
            for group in group_result.get('Groups', []):
                tag_value = group['Keys'][0].replace('CostCenter$', '')
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                if tag_value and cost > 0:
                    result["by_cost_center"].append({"cost_center": tag_value, "cost": cost})
    except Exception as e:
        print(f"Cost Explorer (CostCenter) non disponible : {e}")

    # --- Couts par Service (Top 10) ---
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        result["by_service"] = []
        for group_result in response.get('ResultsByTime', []):
            for group in group_result.get('Groups', []):
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                if cost > 0:
                    result["by_service"].append({"service": service, "cost": cost})
        # Trier par cout decroissant, top 10
        result["by_service"] = sorted(result["by_service"], key=lambda x: x["cost"], reverse=True)[:10]
    except Exception as e:
        print(f"Cost Explorer (Service) non disponible : {e}")

    return result


# ========================================
# PUBLICATION DES METRIQUES CLOUDWATCH
# ========================================

def publish_tag_compliance_metrics(data: Dict[str, Any]):
    """Publie les metriques de conformite des tags"""

    summary = data["summary"]

    # Pourcentage de conformite global
    cloudwatch.put_metric_data(
        Namespace='TagCompliance',
        MetricData=[
            {
                'MetricName': 'CompliancePercentage',
                'Value': summary["percentage"],
                'Unit': 'Percent',
                'Dimensions': [
                    {'Name': 'Scope', 'Value': 'Global'}
                ]
            },
            {
                'MetricName': 'TotalResources',
                'Value': summary["total"],
                'Unit': 'Count'
            },
            {
                'MetricName': 'CompliantResources',
                'Value': summary["compliant"],
                'Unit': 'Count'
            },
            {
                'MetricName': 'NonCompliantResources',
                'Value': summary["non_compliant"],
                'Unit': 'Count'
            }
        ]
    )

    # Metriques par type de ressource
    for resource in data["resources"]:
        if not resource["compliant"]:
            cloudwatch.put_metric_data(
                Namespace='TagCompliance',
                MetricData=[{
                    'MetricName': 'NonCompliantResources',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'ResourceType', 'Value': resource["type"]},
                        {'Name': 'ResourceId', 'Value': resource["id"]}
                    ]
                }]
            )

    print(f"TagCompliance : {summary['percentage']}% conforme ({summary['compliant']}/{summary['total']})")


def publish_resource_count_metrics(counts: Dict[str, int]):
    """Publie le nombre de ressources par type"""

    metric_data = []
    for resource_type, count in counts.items():
        metric_data.append({
            'MetricName': 'ResourcesByType',
            'Value': count,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'ResourceType', 'Value': resource_type}
            ]
        })

    if metric_data:
        cloudwatch.put_metric_data(
            Namespace='ResourceCount',
            MetricData=metric_data
        )

    print(f"ResourceCount : {counts}")


def publish_autoshutdown_metrics(savings: float):
    """Publie les economies estimees via AutoShutdown"""

    cloudwatch.put_metric_data(
        Namespace='AutoShutdown',
        MetricData=[{
            'MetricName': 'EstimatedSavings',
            'Value': savings,
            'Unit': 'None',
            'Dimensions': [
                {'Name': 'Period', 'Value': 'Monthly'}
            ]
        }]
    )

    print(f"AutoShutdown : economies estimees = ${savings}/mois")


def publish_cost_explorer_metrics(data: Dict[str, Any]):
    """Publie les metriques de couts depuis Cost Explorer"""

    # Couts par Squad
    for item in data.get("by_squad", []):
        cloudwatch.put_metric_data(
            Namespace='CostExplorer',
            MetricData=[{
                'MetricName': 'CostBySquad',
                'Value': item["cost"],
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'Squad', 'Value': item["squad"]}
                ]
            }]
        )

    # Couts par CostCenter
    for item in data.get("by_cost_center", []):
        cloudwatch.put_metric_data(
            Namespace='CostExplorer',
            MetricData=[{
                'MetricName': 'CostByCostCenter',
                'Value': item["cost"],
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'CostCenter', 'Value': item["cost_center"]}
                ]
            }]
        )

    # Couts par Service (Top 10)
    for item in data.get("by_service", []):
        cloudwatch.put_metric_data(
            Namespace='CostExplorer',
            MetricData=[{
                'MetricName': 'TopCostResources',
                'Value': item["cost"],
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'Service', 'Value': item["service"]}
                ]
            }]
        )

    print(f"CostExplorer : {len(data.get('by_squad', []))} squads, "
          f"{len(data.get('by_cost_center', []))} cost centers, "
          f"{len(data.get('by_service', []))} services")
