# ========================================
# OUTPUTS GÉNÉRAUX
# ========================================

output "resource_id" {
  description = "ID de la ressource créée"
  value = var.resource_type == "ec2" ? (
    length(aws_instance.this) > 0 ? aws_instance.this[0].id : null
    ) : var.resource_type == "rds" ? (
    length(aws_db_instance.this) > 0 ? aws_db_instance.this[0].id : null
    ) : var.resource_type == "s3" ? (
    length(aws_s3_bucket.this) > 0 ? aws_s3_bucket.this[0].id : null
    ) : var.resource_type == "lambda" ? (
    length(aws_lambda_function.this) > 0 ? aws_lambda_function.this[0].id : null
  ) : null
}

output "resource_arn" {
  description = "ARN de la ressource créée"
  value = var.resource_type == "ec2" ? (
    length(aws_instance.this) > 0 ? aws_instance.this[0].arn : null
    ) : var.resource_type == "rds" ? (
    length(aws_db_instance.this) > 0 ? aws_db_instance.this[0].arn : null
    ) : var.resource_type == "s3" ? (
    length(aws_s3_bucket.this) > 0 ? aws_s3_bucket.this[0].arn : null
    ) : var.resource_type == "lambda" ? (
    length(aws_lambda_function.this) > 0 ? aws_lambda_function.this[0].arn : null
  ) : null
}

output "resource_name" {
  description = "Nom complet de la ressource créée (avec préfixe environnement)"
  value       = local.resource_full_name
}

output "applied_tags" {
  description = "Tous les tags appliqués à la ressource"
  value       = local.all_tags
}

output "mandatory_tags" {
  description = "Tags obligatoires qui ont été appliqués"
  value       = local.mandatory_tags
}

output "resource_type" {
  description = "Type de ressource créée (ec2, rds, s3, lambda)"
  value       = var.resource_type
}

# ========================================
# OUTPUTS SPÉCIFIQUES EC2
# ========================================

output "ec2_public_ip" {
  description = "Adresse IP publique de l'instance EC2"
  value       = var.resource_type == "ec2" && length(aws_instance.this) > 0 ? aws_instance.this[0].public_ip : null
}

output "ec2_private_ip" {
  description = "Adresse IP privée de l'instance EC2"
  value       = var.resource_type == "ec2" && length(aws_instance.this) > 0 ? aws_instance.this[0].private_ip : null
}

output "ec2_instance_state" {
  description = "État de l'instance EC2"
  value       = var.resource_type == "ec2" && length(aws_instance.this) > 0 ? aws_instance.this[0].instance_state : null
}

# ========================================
# OUTPUTS SPÉCIFIQUES RDS
# ========================================

output "rds_endpoint" {
  description = "Endpoint de connexion à la base de données RDS"
  value       = var.resource_type == "rds" && length(aws_db_instance.this) > 0 ? aws_db_instance.this[0].endpoint : null
}

output "rds_port" {
  description = "Port de la base de données RDS"
  value       = var.resource_type == "rds" && length(aws_db_instance.this) > 0 ? aws_db_instance.this[0].port : null
}

output "rds_engine" {
  description = "Moteur de base de données utilisé"
  value       = var.resource_type == "rds" && length(aws_db_instance.this) > 0 ? aws_db_instance.this[0].engine : null
}

output "rds_secret_arn" {
  description = "ARN du secret AWS Secrets Manager contenant les credentials RDS"
  value       = var.resource_type == "rds" && length(aws_secretsmanager_secret.rds_credentials) > 0 ? aws_secretsmanager_secret.rds_credentials[0].arn : null
}

output "rds_secret_name" {
  description = "Nom du secret AWS Secrets Manager contenant les credentials RDS"
  value       = var.resource_type == "rds" && length(aws_secretsmanager_secret.rds_credentials) > 0 ? aws_secretsmanager_secret.rds_credentials[0].name : null
}

output "rds_master_username" {
  description = "Nom d'utilisateur master de la base de données RDS"
  value       = var.resource_type == "rds" ? var.rds_master_username : null
}

# ========================================
# OUTPUTS SPÉCIFIQUES S3
# ========================================

output "s3_bucket_name" {
  description = "Nom du bucket S3"
  value       = var.resource_type == "s3" && length(aws_s3_bucket.this) > 0 ? aws_s3_bucket.this[0].bucket : null
}

output "s3_bucket_domain" {
  description = "Nom de domaine du bucket S3"
  value       = var.resource_type == "s3" && length(aws_s3_bucket.this) > 0 ? aws_s3_bucket.this[0].bucket_domain_name : null
}

output "s3_bucket_region" {
  description = "Région du bucket S3"
  value       = var.resource_type == "s3" && length(aws_s3_bucket.this) > 0 ? aws_s3_bucket.this[0].region : null
}

# ========================================
# OUTPUTS SPÉCIFIQUES LAMBDA
# ========================================

output "lambda_function_name" {
  description = "Nom de la fonction Lambda"
  value       = var.resource_type == "lambda" && length(aws_lambda_function.this) > 0 ? aws_lambda_function.this[0].function_name : null
}

output "lambda_invoke_arn" {
  description = "ARN d'invocation de la fonction Lambda"
  value       = var.resource_type == "lambda" && length(aws_lambda_function.this) > 0 ? aws_lambda_function.this[0].invoke_arn : null
}

output "lambda_role_arn" {
  description = "ARN du rôle IAM de la fonction Lambda"
  value       = var.resource_type == "lambda" && length(aws_iam_role.lambda) > 0 ? aws_iam_role.lambda[0].arn : null
}

output "lambda_runtime" {
  description = "Runtime de la fonction Lambda"
  value       = var.resource_type == "lambda" && length(aws_lambda_function.this) > 0 ? aws_lambda_function.this[0].runtime : null
}
