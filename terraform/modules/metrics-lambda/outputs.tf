output "lambda_function_name" {
  description = "Nom de la fonction Lambda de metriques"
  value       = aws_lambda_function.metrics.function_name
}

output "lambda_function_arn" {
  description = "ARN de la fonction Lambda de metriques"
  value       = aws_lambda_function.metrics.arn
}

output "cloudwatch_log_group" {
  description = "Nom du groupe de logs CloudWatch"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "schedule_expression" {
  description = "Expression de planification"
  value       = var.enable_schedule ? var.schedule_expression : "Disabled"
}
