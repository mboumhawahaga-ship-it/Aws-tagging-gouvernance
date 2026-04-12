# ========================================
# ENVIRONNEMENT PRODUCTION
# ========================================

provider "aws" {
  region = "eu-west-1"

  default_tags {
    tags = {
      ManagedBy   = "Terraform"
      Environment = "prod"
    }
  }
}
