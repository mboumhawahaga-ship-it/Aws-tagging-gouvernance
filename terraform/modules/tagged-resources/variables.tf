variable "resource_name" {
  description = "Name of the resource to create"
  type        = string
}

variable "resource_type" {
  description = "Type of AWS resource (ec2, rds, s3, lambda)"
  type        = string
  validation {
    condition     = contains(["ec2", "rds", "s3", "lambda"], var.resource_type)
    error_message = "resource_type must be one of: ec2, rds, s3, lambda"
  }
}

variable "owner" {
  description = "Owner of the resource (required) - must be a valid company email"
  type        = string
  validation {
    condition     = can(regex("^[\\w\\-\\.]+@entreprise\\.com$", var.owner))
    error_message = "L'owner doit être une adresse email valide de l'entreprise (@entreprise.com). Exemple : jean.dupont@entreprise.com"
  }
}

variable "squad" {
  description = "Squad responsible for the resource (required)"
  type        = string
  validation {
    condition     = length(var.squad) > 0
    error_message = "Squad tag is mandatory and cannot be empty"
  }
}

variable "cost_center" {
  description = "Cost center for billing (required)"
  type        = string
  validation {
    condition     = length(var.cost_center) > 0
    error_message = "CostCenter tag is mandatory and cannot be empty"
  }
}

variable "auto_shutdown" {
  description = "Enable automatic shutdown for non-prod resources"
  type        = bool
  default     = false
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Resource-specific variables
variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.micro"
}

variable "ec2_ami" {
  description = "AMI ID for EC2 instance"
  type        = string
  default     = null
}

variable "rds_engine" {
  description = "RDS database engine"
  type        = string
  default     = "postgres"
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_master_username" {
  description = "Master username for RDS instance"
  type        = string
  default     = "dbadmin"

  validation {
    condition = !contains(
      ["admin", "root", "postgres", "master", "superuser", "rdsadmin"],
      var.rds_master_username
    )
    error_message = "Ce nom est réservé par AWS/RDS. Utilisez dbadmin, appuser, etc."
  }
}

variable "rds_allocated_storage" {
  description = "Allocated storage in GB for RDS instance"
  type        = number
  default     = 20
}

variable "rds_generate_random_password" {
  description = "Generate a random password for RDS (recommended for security)"
  type        = bool
  default     = true
}

variable "rds_master_password" {
  description = "Master password for RDS (only used if rds_generate_random_password is false). If not provided and rds_generate_random_password is true, a random password will be generated."
  type        = string
  default     = null
  sensitive   = true
}

variable "rds_backup_retention_period" {
  description = "Number of days to retain automated backups (0 to disable, 1-35 days). Recommended: 7+ for prod, 1 for dev"
  type        = number
  default     = 7
  validation {
    condition     = var.rds_backup_retention_period >= 0 && var.rds_backup_retention_period <= 35
    error_message = "Backup retention period must be between 0 and 35 days"
  }
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ deployment for high availability (recommended for prod)"
  type        = bool
  default     = false
}

variable "rds_storage_encrypted" {
  description = "Enable encryption at rest using AWS KMS (highly recommended)"
  type        = bool
  default     = true
}

variable "rds_deletion_protection" {
  description = "Enable deletion protection (recommended for prod)"
  type        = bool
  default     = false
}

variable "rds_publicly_accessible" {
  description = "Make the RDS instance publicly accessible (NOT recommended for security)"
  type        = bool
  default     = false
}

variable "s3_versioning_enabled" {
  description = "Enable S3 versioning"
  type        = bool
  default     = true
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_handler" {
  description = "Lambda handler function"
  type        = string
  default     = "index.handler"
}

variable "lambda_filename" {
  description = "Path to Lambda deployment package"
  type        = string
  default     = null
}
