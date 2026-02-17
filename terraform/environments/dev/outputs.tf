# ========================================
# OUTPUTS DES RESSOURCES CRÉÉES
# ========================================

# Outputs EC2
output "web_server_ip" {
  description = "Adresse IP publique du serveur web"
  value       = module.web_server.ec2_public_ip
}

output "web_server_tags" {
  description = "Tags appliqués au serveur web"
  value       = module.web_server.applied_tags
}

# Outputs RDS
output "analytics_db_endpoint" {
  description = "Endpoint de connexion à la base de données"
  value       = module.analytics_db.rds_endpoint
}

output "analytics_db_tags" {
  description = "Tags appliqués à la base de données"
  value       = module.analytics_db.applied_tags
}

# Outputs S3
output "data_lake_bucket" {
  description = "Nom du bucket S3"
  value       = module.data_lake.s3_bucket_name
}

output "data_lake_tags" {
  description = "Tags appliqués au bucket S3"
  value       = module.data_lake.applied_tags
}

# Outputs Lambda
output "data_processor_arn" {
  description = "ARN de la fonction Lambda"
  value       = module.data_processor.lambda_invoke_arn
}

output "data_processor_tags" {
  description = "Tags appliqués à la fonction Lambda"
  value       = module.data_processor.applied_tags
}

# ========================================
# RÉSUMÉ DE TOUTES LES RESSOURCES
# ========================================

output "all_resources_summary" {
  description = "Résumé de toutes les ressources créées"
  value = {
    web_server = {
      name = module.web_server.resource_name
      type = module.web_server.resource_type
      id   = module.web_server.resource_id
    }
    analytics_db = {
      name = module.analytics_db.resource_name
      type = module.analytics_db.resource_type
      id   = module.analytics_db.resource_id
    }
    data_lake = {
      name = module.data_lake.resource_name
      type = module.data_lake.resource_type
      id   = module.data_lake.resource_id
    }
    data_processor = {
      name = module.data_processor.resource_name
      type = module.data_processor.resource_type
      id   = module.data_processor.resource_id
    }
  }
}
