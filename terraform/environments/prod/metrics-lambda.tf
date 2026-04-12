# ========================================
# LAMBDA METRICS - PRODUCTION
# ========================================

module "metrics_lambda" {
  source = "../../modules/metrics-lambda"

  environment = "prod"

  # Collecte toutes les 6 heures
  enable_schedule     = true
  schedule_expression = "rate(6 hours)"

  # Rétention logs plus longue en prod
  log_retention_days = 30
}

output "metrics_lambda_name" {
  description = "Nom de la Lambda de métriques"
  value       = module.metrics_lambda.lambda_function_name
}

output "metrics_schedule" {
  description = "Planification d'exécution des métriques"
  value       = module.metrics_lambda.schedule_expression
}
