output "scanner_lambda_arn" {
  description = "ARN de la Lambda scanner"
  value       = module.governance.scanner_lambda_arn
}

output "state_machine_arn" {
  description = "ARN de la Step Function"
  value       = module.governance.state_machine_arn
}

output "sns_topic_arn" {
  description = "ARN du topic SNS pour les notifications"
  value       = module.governance.sns_topic_arn
}
