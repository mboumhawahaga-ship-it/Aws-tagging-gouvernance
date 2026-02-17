output "lambda_function_name" {
  description = "Nom de la fonction Lambda"
  value       = aws_lambda_function.cleanup.function_name
}

output "lambda_function_arn" {
  description = "ARN de la fonction Lambda"
  value       = aws_lambda_function.cleanup.arn
}

output "sns_topic_arn" {
  description = "ARN du topic SNS pour les notifications"
  value       = aws_sns_topic.cleanup_notifications.arn
}

output "cloudwatch_log_group" {
  description = "Nom du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "schedule_expression" {
  description = "Expression cron de planification"
  value       = var.enable_schedule ? var.schedule_expression : "Disabled"
}

output "dry_run_mode" {
  description = "Mode de fonctionnement (simulation ou production)"
  value       = var.dry_run ? "SIMULATION (DRY_RUN)" : "PRODUCTION (suppression réelle)"
}
