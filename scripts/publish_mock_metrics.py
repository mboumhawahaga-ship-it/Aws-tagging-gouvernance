"""
Script de test : publie des metriques mock dans CloudWatch
pour alimenter le dashboard Grafana "AWS Tagging Governance".

Usage :
    python scripts/publish_mock_metrics.py

Les metriques sont publiees dans la region eu-west-1
dans les namespaces : TagCompliance, ResourceCount, AutoShutdown, CostExplorer
"""

import boto3
from datetime import datetime

REGION = "eu-west-1"
cloudwatch = boto3.client("cloudwatch", region_name=REGION)


def publish_tag_compliance():
    """Publie des metriques de conformite des tags"""
    total = 24
    compliant = 19
    non_compliant = total - compliant
    percentage = round(compliant / total * 100, 1)

    cloudwatch.put_metric_data(
        Namespace="TagCompliance",
        MetricData=[
            {
                "MetricName": "CompliancePercentage",
                "Value": percentage,
                "Unit": "Percent",
                "Dimensions": [{"Name": "Scope", "Value": "Global"}],
            },
            {
                "MetricName": "TotalResources",
                "Value": total,
                "Unit": "Count",
            },
            {
                "MetricName": "CompliantResources",
                "Value": compliant,
                "Unit": "Count",
            },
            {
                "MetricName": "NonCompliantResources",
                "Value": non_compliant,
                "Unit": "Count",
            },
        ],
    )
    print(f"  TagCompliance : {percentage}% ({compliant}/{total})")


def publish_resource_counts():
    """Publie le nombre de ressources par type"""
    counts = {"EC2": 8, "RDS": 3, "S3": 7, "Lambda": 6}

    metric_data = [
        {
            "MetricName": "ResourcesByType",
            "Value": count,
            "Unit": "Count",
            "Dimensions": [{"Name": "ResourceType", "Value": rtype}],
        }
        for rtype, count in counts.items()
    ]

    cloudwatch.put_metric_data(Namespace="ResourceCount", MetricData=metric_data)
    print(f"  ResourceCount : {counts}")


def publish_autoshutdown_savings():
    """Publie les economies estimees via AutoShutdown"""
    savings = 47.52

    cloudwatch.put_metric_data(
        Namespace="AutoShutdown",
        MetricData=[
            {
                "MetricName": "EstimatedSavings",
                "Value": savings,
                "Unit": "None",
                "Dimensions": [{"Name": "Period", "Value": "Monthly"}],
            }
        ],
    )
    print(f"  AutoShutdown : ${savings}/mois")


def publish_cost_by_squad():
    """Publie les couts par equipe (Squad)"""
    squads = [
        {"squad": "Data", "cost": 245.80},
        {"squad": "Backend", "cost": 189.30},
        {"squad": "DevOps", "cost": 312.50},
        {"squad": "Frontend", "cost": 67.20},
        {"squad": "DataEngineering", "cost": 156.40},
    ]

    for item in squads:
        cloudwatch.put_metric_data(
            Namespace="CostExplorer",
            MetricData=[
                {
                    "MetricName": "CostBySquad",
                    "Value": item["cost"],
                    "Unit": "None",
                    "Dimensions": [{"Name": "Squad", "Value": item["squad"]}],
                }
            ],
        )
    print(f"  CostBySquad : {len(squads)} equipes")


def publish_cost_by_cost_center():
    """Publie les couts par centre de couts"""
    cost_centers = [
        {"cost_center": "CC-123", "cost": 412.30},
        {"cost_center": "CC-456", "cost": 298.70},
        {"cost_center": "CC-789", "cost": 178.40},
        {"cost_center": "CC-101", "cost": 82.10},
    ]

    for item in cost_centers:
        cloudwatch.put_metric_data(
            Namespace="CostExplorer",
            MetricData=[
                {
                    "MetricName": "CostByCostCenter",
                    "Value": item["cost"],
                    "Unit": "None",
                    "Dimensions": [
                        {"Name": "CostCenter", "Value": item["cost_center"]}
                    ],
                }
            ],
        )
    print(f"  CostByCostCenter : {len(cost_centers)} centres")


def publish_top_services():
    """Publie les top services AWS par cout"""
    services = [
        {"service": "Amazon EC2", "cost": 320.50},
        {"service": "Amazon RDS", "cost": 215.80},
        {"service": "Amazon S3", "cost": 89.30},
        {"service": "AWS Lambda", "cost": 42.10},
        {"service": "Amazon CloudWatch", "cost": 28.60},
        {"service": "Amazon SNS", "cost": 12.40},
        {"service": "AWS KMS", "cost": 8.90},
        {"service": "Amazon Route 53", "cost": 5.20},
        {"service": "AWS Secrets Manager", "cost": 3.80},
        {"service": "Amazon ECR", "cost": 2.10},
    ]

    for item in services:
        cloudwatch.put_metric_data(
            Namespace="CostExplorer",
            MetricData=[
                {
                    "MetricName": "TopCostResources",
                    "Value": item["cost"],
                    "Unit": "None",
                    "Dimensions": [{"Name": "Service", "Value": item["service"]}],
                }
            ],
        )
    print(f"  TopCostResources : {len(services)} services")


if __name__ == "__main__":
    print(f"Publication des metriques mock dans CloudWatch ({REGION})")
    print(f"Timestamp : {datetime.now().isoformat()}")
    print("-" * 50)

    publish_tag_compliance()
    publish_resource_counts()
    publish_autoshutdown_savings()
    publish_cost_by_squad()
    publish_cost_by_cost_center()
    publish_top_services()

    print("-" * 50)
    print("Toutes les metriques ont ete publiees avec succes !")
    print("Ouvrez Grafana (http://localhost:3000) et rafraichissez le dashboard.")
