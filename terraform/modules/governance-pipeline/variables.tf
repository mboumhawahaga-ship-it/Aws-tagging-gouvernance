variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "aws_region" {
  description = "Région AWS de déploiement"
  type        = string
  default     = "eu-west-1"
}

variable "admin_email" {
  description = "Email administrateur pour les notifications de gouvernance"
  type        = string
}

variable "dry_run" {
  description = "Mode simulation — aucune action destructive si true"
  type        = bool
  default     = true
}

variable "scan_schedule" {
  description = "Expression cron EventBridge pour le scanner"
  type        = string
  default     = "cron(0 2 * * ? *)"
}

variable "log_retention_days" {
  description = "Rétention des logs CloudWatch en jours"
  type        = number
  default     = 30
}
