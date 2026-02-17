# ========================================
# EXEMPLE D'UTILISATION DU MODULE
# Environnement : DEV
# ========================================

# Configuration du provider AWS
provider "aws" {
  region = "eu-west-1" # Paris
}

# ========================================
# EXEMPLE 1 : Serveur EC2 avec tags obligatoires
# ========================================

module "web_server" {
  source = "../../modules/tagged-resources"

  # Type de ressource
  resource_type = "ec2"
  resource_name = "web-server"

  # Tags OBLIGATOIRES (Terraform refuse si vous les oubliez)
  owner       = "jean.dupont@entreprise.com"
  squad       = "Data"
  cost_center = "CC-123"
  environment = "dev"

  # Tags optionnels
  auto_shutdown = true # S'éteint automatiquement le soir

  # Configuration EC2
  ec2_instance_type = "t3.micro"

  # Tags supplémentaires (optionnel)
  additional_tags = {
    Project     = "Analytics"
    Description = "Serveur web pour dashboard analytics"
  }
}

# ========================================
# EXEMPLE 2 : Base de données RDS (avec Secrets Manager)
# ========================================

module "analytics_db" {
  source = "../../modules/tagged-resources"

  resource_type = "rds"
  resource_name = "analytics-db"

  owner       = "marie.martin@entreprise.com"
  squad       = "Data"
  cost_center = "CC-123"
  environment = "dev"

  auto_shutdown = true

  # Configuration RDS
  rds_engine            = "postgres"
  rds_instance_class    = "db.t3.micro"
  rds_allocated_storage = 20
  rds_master_username   = "dbadmin"

  # 🔐 Sécurité : génération automatique d'un mot de passe aléatoire
  # Le mot de passe sera stocké dans AWS Secrets Manager
  rds_generate_random_password = true

  # 🔒 Sécurité : Options supplémentaires
  rds_storage_encrypted   = true  # Chiffrement au repos (activé par défaut)
  rds_publicly_accessible = false # Pas d'accès public (sécurité)
  rds_backup_retention_period = 1 # 1 jour de backup pour dev (économique)
  rds_multi_az            = false # Pas de Multi-AZ en dev (économique)

  # Alternative : fournir un mot de passe manuellement (NON recommandé)
  # rds_generate_random_password = false
  # rds_master_password          = "<votre-mot-de-passe>"

  additional_tags = {
    Project = "Analytics"
    Backup  = "Daily"
  }
}

# ========================================
# EXEMPLE 3 : Bucket S3
# ========================================

module "data_lake" {
  source = "../../modules/tagged-resources"

  resource_type = "s3"
  resource_name = "data-lake-440501616995"

  owner       = "paul.durand@entreprise.com"
  squad       = "DataEngineering"
  cost_center = "CC-456"
  environment = "dev"

  auto_shutdown = false # Les buckets S3 ne s'éteignent pas

  # Configuration S3
  s3_versioning_enabled = true

  additional_tags = {
    Project    = "DataLake"
    Encryption = "AES256"
  }
}

# ========================================
# EXEMPLE 4 : Fonction Lambda
# ========================================

module "data_processor" {
  source = "../../modules/tagged-resources"

  resource_type = "lambda"
  resource_name = "data-processor"

  owner       = "sophie.leblanc@entreprise.com"
  squad       = "Data"
  cost_center = "CC-123"
  environment = "dev"

  auto_shutdown = false

  # Configuration Lambda
  lambda_runtime = "python3.11"
  lambda_handler = "handler.process_data"
  # lambda_filename = "./lambda/data_processor.zip" # Décommentez quand vous avez le code

  additional_tags = {
    Project = "DataPipeline"
    Trigger = "S3"
  }
}
