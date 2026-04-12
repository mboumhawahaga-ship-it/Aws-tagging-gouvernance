# ========================================
# LAMBDA CLEANUP - PRODUCTION
# ========================================

module "cleanup_lambda" {
  source = "../../modules/cleanup-lambda"

  environment = "prod"

  # Grace period étendue en prod (48h)
  grace_period_hours = 48

  # IMPORTANT : passer à false uniquement après validation en DRY_RUN
  dry_run = true

  notification_email = var.notification_email

  # Planification : tous les jours à 2h UTC
  enable_schedule     = true
  schedule_expression = "cron(0 2 * * ? *)"

  # Rétention logs plus longue en prod
  log_retention_days = 30
}

output "cleanup_lambda_name" {
  description = "Nom de la Lambda de cleanup"
  value       = module.cleanup_lambda.lambda_function_name
}

output "cleanup_mode" {
  description = "Mode de fonctionnement actuel"
  value       = module.cleanup_lambda.dry_run_mode
}
