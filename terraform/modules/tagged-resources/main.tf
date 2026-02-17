resource "time_static" "created" {}

locals {
  # Tags obligatoires appliqués à TOUTES les ressources
  mandatory_tags = {
    Owner        = var.owner
    Squad        = var.squad
    CostCenter   = var.cost_center
    AutoShutdown = tostring(var.auto_shutdown)
    Environment  = var.environment
    ManagedBy    = "Terraform"
    CreatedAt    = time_static.created.rfc3339
  }

  # Fusion des tags obligatoires + tags additionnels
  all_tags = merge(local.mandatory_tags, var.additional_tags)

  # Nom complet de la ressource (avec préfixe environnement)
  resource_full_name = "${var.environment}-${var.resource_name}"
}

# ========================================
# DATA SOURCES
# ========================================

# Récupère la dernière AMI Amazon Linux 2023 ARM64 si non fournie
data "aws_ami" "amazon_linux_2" {
  count       = var.resource_type == "ec2" && var.ec2_ami == null ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-kernel-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

# ========================================
# RESSOURCE EC2
# ========================================

resource "aws_instance" "this" {
  count = var.resource_type == "ec2" ? 1 : 0

  ami           = var.ec2_ami != null ? var.ec2_ami : data.aws_ami.amazon_linux_2[0].id
  instance_type = var.ec2_instance_type

  # Application automatique des tags obligatoires
  tags = merge(
    local.all_tags,
    {
      Name = local.resource_full_name
      Type = "EC2Instance"
    }
  )

  # Monitoring détaillé activé en production
  monitoring = var.environment == "prod" ? true : false

  lifecycle {
    create_before_destroy = true
  }
}

# ========================================
# RESSOURCE RDS
# ========================================

# Génération d'un mot de passe aléatoire sécurisé (si activé)
resource "random_password" "rds_password" {
  count = var.resource_type == "rds" && var.rds_generate_random_password ? 1 : 0

  length  = 32
  special = true
  # Exclure certains caractères qui peuvent poser problème dans les chaînes de connexion
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Création du secret dans AWS Secrets Manager
resource "aws_secretsmanager_secret" "rds_credentials" {
  count = var.resource_type == "rds" ? 1 : 0

  name        = "${local.resource_full_name}-rds-credentials"
  description = "RDS credentials for ${local.resource_full_name}"

  # Politique de rotation (optionnel, à configurer selon vos besoins)
  # rotation_rules {
  #   automatically_after_days = 30
  # }

  tags = merge(
    local.all_tags,
    {
      Name = "${local.resource_full_name}-rds-credentials"
      Type = "SecretsManager"
    }
  )
}

# Stockage des credentials dans le secret (avec infos de connexion complètes)
resource "aws_secretsmanager_secret_version" "rds_credentials" {
  count = var.resource_type == "rds" ? 1 : 0

  secret_id = aws_secretsmanager_secret.rds_credentials[0].id
  secret_string = jsonencode({
    username             = var.rds_master_username
    password             = var.rds_generate_random_password ? random_password.rds_password[0].result : var.rds_master_password
    engine               = var.rds_engine
    host                 = aws_db_instance.this[0].address
    port                 = aws_db_instance.this[0].port
    dbname               = aws_db_instance.this[0].db_name
    dbInstanceIdentifier = aws_db_instance.this[0].identifier
  })

  depends_on = [
    aws_db_instance.this
  ]
}

# Instance RDS avec mot de passe depuis Secrets Manager
resource "aws_db_instance" "this" {
  count = var.resource_type == "rds" ? 1 : 0

  identifier        = local.resource_full_name
  engine            = var.rds_engine
  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage

  # Identifiants sécurisés via Secrets Manager
  username = var.rds_master_username
  password = var.rds_generate_random_password ? random_password.rds_password[0].result : var.rds_master_password

  # 🔒 Sécurité : Chiffrement au repos (activé par défaut)
  storage_encrypted = var.rds_storage_encrypted

  # 🔒 Sécurité : Pas d'accès public (sécurité par défaut)
  publicly_accessible = var.rds_publicly_accessible

  # 🔒 Sécurité : Protection contre la suppression (activé en prod)
  deletion_protection = var.environment == "prod" ? true : var.rds_deletion_protection

  # 💾 Backups automatiques
  backup_retention_period = var.environment == "prod" ? max(7, var.rds_backup_retention_period) : var.rds_backup_retention_period
  backup_window           = "03:00-04:00" # UTC - ajuster selon votre timezone
  maintenance_window      = "Mon:04:00-Mon:05:00"

  # 🔄 Haute disponibilité : Multi-AZ (recommandé pour prod)
  multi_az = var.environment == "prod" ? true : var.rds_multi_az

  # 🔄 Mises à jour automatiques des versions mineures
  auto_minor_version_upgrade = true

  # 📊 Logs CloudWatch (pour monitoring et audit)
  enabled_cloudwatch_logs_exports = var.rds_engine == "postgres" ? ["postgresql", "upgrade"] : var.rds_engine == "mysql" ? ["error", "general", "slowquery"] : []

  # Pas de snapshot final en dev/staging
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.resource_full_name}-final-snapshot-${formatdate("YYYY-MM-DD", time_static.created.rfc3339)}" : null

  # Application automatique des tags
  tags = merge(
    local.all_tags,
    {
      Name = local.resource_full_name
      Type = "RDSInstance"
    }
  )

  lifecycle {
    create_before_destroy = true
    # Ignorer les changements de mot de passe après la création initiale
    # (pour permettre la rotation via Secrets Manager)
    ignore_changes = [password, final_snapshot_identifier]
  }
}

# ========================================
# RESSOURCE S3
# ========================================

resource "aws_s3_bucket" "this" {
  count = var.resource_type == "s3" ? 1 : 0

  bucket = local.resource_full_name

  # Application automatique des tags
  tags = merge(
    local.all_tags,
    {
      Name = local.resource_full_name
      Type = "S3Bucket"
    }
  )

  lifecycle {
    prevent_destroy = false
  }
}

# Activation du versioning sur S3
resource "aws_s3_bucket_versioning" "this" {
  count = var.resource_type == "s3" ? 1 : 0

  bucket = aws_s3_bucket.this[0].id

  versioning_configuration {
    status = var.s3_versioning_enabled ? "Enabled" : "Disabled"
  }
}

# S3 Intelligent-Tiering (archivage automatique)
resource "aws_s3_bucket_intelligent_tiering_configuration" "this" {
  count  = var.resource_type == "s3" ? 1 : 0
  bucket = aws_s3_bucket.this[0].id
  name   = "EntireBucket"

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}

# Chiffrement par défaut sur S3
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  count = var.resource_type == "s3" ? 1 : 0

  bucket = aws_s3_bucket.this[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ========================================
# RESSOURCE LAMBDA
# ========================================

# Rôle IAM pour Lambda
resource "aws_iam_role" "lambda" {
  count = var.resource_type == "lambda" ? 1 : 0

  name = "${local.resource_full_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.all_tags
}

# Attachement de la politique d'exécution Lambda
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  count = var.resource_type == "lambda" ? 1 : 0

  role       = aws_iam_role.lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Fonction Lambda avec tags obligatoires
resource "aws_lambda_function" "this" {
  count = var.resource_type == "lambda" ? 1 : 0

  function_name = local.resource_full_name
  role          = aws_iam_role.lambda[0].arn
  handler       = var.lambda_handler
  runtime       = var.lambda_runtime
  architectures = ["arm64"]

  filename         = var.lambda_filename != null ? var.lambda_filename : "${path.module}/placeholder_lambda.zip"
  source_code_hash = filebase64sha256(var.lambda_filename != null ? var.lambda_filename : "${path.module}/placeholder_lambda.zip")

  # Variables d'environnement avec les tags
  environment {
    variables = {
      OWNER         = var.owner
      SQUAD         = var.squad
      COST_CENTER   = var.cost_center
      ENVIRONMENT   = var.environment
      AUTO_SHUTDOWN = tostring(var.auto_shutdown)
    }
  }

  # Application automatique des tags
  tags = merge(
    local.all_tags,
    {
      Name = local.resource_full_name
      Type = "LambdaFunction"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}
