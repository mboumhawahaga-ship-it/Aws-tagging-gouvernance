output "scanner_lambda_arn" {
  description = "ARN de la Lambda scanner"
  value       = aws_lambda_function.scanner.arn
}

output "controller_lambda_arn" {
  description = "ARN de la Lambda controller"
  value       = aws_lambda_function.controller.arn
}

output "executor_lambda_arn" {
  description = "ARN de la Lambda executor"
  value       = aws_lambda_function.executor.arn
}

output "state_machine_arn" {
  description = "ARN de la Step Functions state machine"
  value       = aws_sfn_state_machine.governance.arn
}

output "sns_topic_arn" {
  description = "ARN du topic SNS de gouvernance"
  value       = aws_sns_topic.governance.arn
}

output "dry_run_mode" {
  description = "Mode DRY_RUN actif ou non"
  value       = var.dry_run ? "SIMULATION (aucune action destructive)" : "PRODUCTION (actions réelles)"
}
