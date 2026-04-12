# ========================================
# PIPELINE DE GOUVERNANCE — PRODUCTION
# ========================================

module "governance_pipeline" {
  source = "../../modules/governance-pipeline"

  environment = "prod"
  aws_region  = "eu-west-1"
  admin_email = var.notification_email

  # IMPORTANT : passer à false après validation en DRY_RUN
  dry_run = true

  # Scan tous les jours à 2h UTC
  scan_schedule = "cron(0 2 * * ? *)"

  # Logs 30 jours en prod
  log_retention_days = 30
}

output "governance_state_machine_arn" {
  description = "ARN de la state machine de gouvernance"
  value       = module.governance_pipeline.state_machine_arn
}

output "governance_mode" {
  description = "Mode de fonctionnement actuel"
  value       = module.governance_pipeline.dry_run_mode
}
