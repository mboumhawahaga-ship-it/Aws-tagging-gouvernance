"""
Controller - Évalue, vérifie la conformité et notifie.
Reçoit une action : evaluate | check_compliance | notify
Notifie via SNS (email) + Slack webhook (visible immédiatement)
"""

import os
import json
import urllib.request
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger(service="governance-controller")
tracer = Tracer(service="governance-controller")
metrics = Metrics(namespace="TagGovernance", service="governance-controller")

from shared.config import REQUIRED_TAGS, check_tags

REGION = os.environ.get("AWS_REGION", "eu-west-1")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
SLACK_SECRET_NAME = os.environ.get("SLACK_SECRET_NAME", "")

ec2 = boto3.client("ec2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
lmb = boto3.client("lambda", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)
secretsmanager = boto3.client("secretsmanager", region_name=REGION)

# Cache du webhook en mémoire — évite un appel Secrets Manager à chaque invocation
_slack_webhook_url: str | None = None


def get_slack_webhook_url() -> str:
    """Récupère le webhook Slack depuis Secrets Manager (avec cache mémoire Lambda)."""
    global _slack_webhook_url
    if _slack_webhook_url:
        return _slack_webhook_url
    if not SLACK_SECRET_NAME:
        return ""
    try:
        resp = secretsmanager.get_secret_value(SecretId=SLACK_SECRET_NAME)
        secret = json.loads(resp["SecretString"])
        _slack_webhook_url = secret.get("webhook_url", "")
        return _slack_webhook_url
    except Exception as e:
        logger.warning("Impossible de récupérer le webhook Slack", extra={"error": str(e)})
        return ""


def get_current_tags(resource_type: str, resource_id: str, resource_arn: str) -> list:
    try:
        if resource_type == "ec2":
            resp = ec2.describe_instances(InstanceIds=[resource_id])
            return resp["Reservations"][0]["Instances"][0].get("Tags", [])
        elif resource_type == "rds":
            resp = rds.list_tags_for_resource(ResourceName=resource_arn)
            return resp.get("TagList", [])
        elif resource_type == "s3":
            try:
                resp = s3.get_bucket_tagging(Bucket=resource_id)
                return resp.get("TagSet", [])
            except ClientError as e:
                if e.response["Error"]["Code"] in ("NoSuchTagSet", "NoSuchBucket"):
                    return []
                raise
        elif resource_type == "lambda":
            resp = lmb.list_tags(Resource=resource_arn)
            return [{"Key": k, "Value": v} for k, v in resp.get("Tags", {}).items()]
    except Exception as e:
        logger.error("Erreur récupération tags", extra={"resource_id": resource_id, "error": str(e)})
    return []


# ========================================
# SLACK
# ========================================

SLACK_COLORS = {"J0": "#FFA500", "J2": "#FF4500", "FAILURE": "#FF0000", "RESUME": "#36A64F"}
SLACK_EMOJIS = {"J0": "⚠️", "J2": "🔴", "FAILURE": "🚨", "RESUME": "✅"}


@tracer.capture_method
def notify_slack(resource: dict, step: str):
    """Envoie un message Slack structuré via webhook."""
    webhook_url = get_slack_webhook_url()
    if not webhook_url:
        logger.info("Slack webhook non configuré, notification ignorée")
        return

    step_labels = {
        "J0": "Ressource gelée — 48h pour corriger les tags",
        "J2": "RAPPEL — suppression dans 48h si aucune action",
        "FAILURE": "Erreur pipeline — intervention manuelle requise",
        "RESUME": "Tags corrigés — ressource réactivée automatiquement",
    }

    payload = {
        "attachments": [{
            "color": SLACK_COLORS.get(step, "#808080"),
            "title": f"{SLACK_EMOJIS.get(step, '🔔')} AWS Governance — {resource['resource_type'].upper()} {resource['resource_id']}",
            "text": step_labels.get(step, step),
            "fields": [
                {"title": "Type",           "value": resource["resource_type"].upper(),        "short": True},
                {"title": "Étape",          "value": step,                                     "short": True},
                {"title": "Tags manquants", "value": ", ".join(resource.get("missing_tags", [])) or "—", "short": False},
                {"title": "Owner",          "value": resource.get("owner") or "INCONNU",       "short": True},
                {"title": "Région",         "value": resource.get("region", REGION),           "short": True},
            ],
            "footer": "AWS Governance Pipeline",
            "ts": int(datetime.utcnow().timestamp()),
        }]
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        logger.info("Notification Slack envoyée", extra={"step": step, "resource_id": resource["resource_id"]})
    except Exception as e:
        # Ne pas faire échouer le pipeline si Slack est indisponible
        logger.warning("Échec notification Slack", extra={"error": str(e)})


# ========================================
# ACTIONS
# ========================================

@tracer.capture_method
def action_evaluate(resource: dict) -> dict:
    has_owner = bool(resource.get("owner"))
    notify_target = resource["owner"] if has_owner else ADMIN_EMAIL

    logger.info("Évaluation ressource", extra={
        "resource_id": resource["resource_id"],
        "has_owner": has_owner,
        "missing_tags": resource["missing_tags"],
    })

    return {"has_owner": has_owner, "notify_target": notify_target}


@tracer.capture_method
def action_check_compliance(resource: dict) -> dict:
    tags = get_current_tags(
        resource_type=resource["resource_type"],
        resource_id=resource["resource_id"],
        resource_arn=resource["resource_arn"],
    )
    compliant, missing = check_tags(tags)

    logger.info("Check conformité", extra={
        "resource_id": resource["resource_id"],
        "compliant": compliant,
        "missing_tags": missing,
    })

    if compliant:
        metrics.add_metric(name="TagsCorrectedByOwner", unit=MetricUnit.Count, value=1)
        notify_slack(resource, step="RESUME")

    return {"compliant": compliant, "missing_tags": missing}


@tracer.capture_method
def action_notify(resource: dict, step: str) -> dict:
    evaluation = resource.get("evaluation", {})
    notify_target = evaluation.get("notify_target", ADMIN_EMAIL)

    messages = {
        "J0": (
            f"[GOUVERNANCE AWS] Ressource non conforme détectée\n\n"
            f"Ressource      : {resource['resource_type'].upper()} {resource['resource_id']}\n"
            f"Région         : {resource['region']}\n"
            f"Tags manquants : {', '.join(resource['missing_tags'])}\n\n"
            f"⚠️  La ressource a été mise en pause.\n"
            f"Ajoutez les tags manquants dans les 48h pour la réactiver automatiquement.\n"
            f"Sans action, une relance sera envoyée à J+2 puis suppression à J+4."
        ),
        "J2": (
            f"[GOUVERNANCE AWS] ⚠️  RAPPEL — Ressource toujours non conforme\n\n"
            f"Ressource      : {resource['resource_type'].upper()} {resource['resource_id']}\n"
            f"Région         : {resource['region']}\n"
            f"Tags manquants : {', '.join(resource['missing_tags'])}\n\n"
            f"🔴 Sans action dans les 48h, la ressource sera supprimée définitivement."
        ),
        "FAILURE": (
            f"[GOUVERNANCE AWS] 🚨 ERREUR PIPELINE\n\n"
            f"Ressource  : {resource['resource_type'].upper()} {resource['resource_id']}\n"
            f"Erreur     : {resource.get('error', 'Inconnue')}\n\n"
            f"Intervention manuelle requise."
        ),
    }

    subject_map = {
        "J0":      f"[AWS Governance] Ressource non conforme : {resource['resource_id']}",
        "J2":      f"[AWS Governance] RAPPEL — {resource['resource_id']} toujours non conforme",
        "FAILURE": f"[AWS Governance] 🚨 ERREUR — {resource['resource_id']}",
    }

    # SNS — email archive
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject_map.get(step, "AWS Governance"),
        Message=messages.get(step, "Notification de gouvernance AWS"),
    )

    # Slack — notification immédiate
    notify_slack(resource, step=step)

    logger.info("Notifications envoyées", extra={"step": step, "target": notify_target, "resource_id": resource["resource_id"]})
    metrics.add_metric(name=f"Notification{step}", unit=MetricUnit.Count, value=1)

    return {"notified": True, "step": step, "target": notify_target}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event, context):
    action = event.get("action")
    resource = event.get("resource", event)

    logger.info("Action reçue", extra={"action": action, "resource_id": resource.get("resource_id")})

    if action == "evaluate":
        return action_evaluate(resource)
    elif action == "check_compliance":
        return action_check_compliance(resource)
    elif action == "notify":
        return action_notify(resource, step=event.get("step", "J0"))
    else:
        raise ValueError(f"Action inconnue : {action}")
