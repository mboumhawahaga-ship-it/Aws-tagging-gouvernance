# 🔒 Guide de Sécurité AWS - Meilleures Pratiques

Ce document décrit toutes les mesures de sécurité implémentées dans le projet et les meilleures pratiques à suivre.

---

## ✅ Mesures de sécurité implémentées

### 🔐 1. Gestion des secrets et mots de passe

#### AWS Secrets Manager (RDS)

**✅ Implémenté** :
- Génération automatique de mots de passe aléatoires (32 caractères)
- Stockage sécurisé dans AWS Secrets Manager
- Chiffrement au repos avec AWS KMS
- Rotation possible (à configurer)

**Configuration** :
```hcl
module "ma_database" {
  source = "../../modules/tagged-resources"

  resource_type = "rds"
  resource_name = "ma-db"

  # ✅ Génération automatique activée par défaut
  rds_generate_random_password = true
}
```

**Récupération sécurisée** :
```bash
# Obtenir le nom du secret
terraform output rds_secret_name

# Récupérer les credentials
aws secretsmanager get-secret-value \
  --secret-id dev-ma-db-rds-credentials \
  --query SecretString --output text | jq .
```

---

### 🔒 2. Chiffrement

#### RDS - Chiffrement au repos

**✅ Activé par défaut** :
```hcl
rds_storage_encrypted = true  # Par défaut
```

- Utilise AWS KMS pour chiffrer les données
- Chiffre les backups automatiquement
- Chiffre les snapshots

#### S3 - Chiffrement côté serveur

**✅ Activé automatiquement** :
- Algorithme : AES-256
- Appliqué à tous les objets
- Aucune configuration nécessaire

#### Secrets Manager

**✅ Chiffré automatiquement** :
- Chiffrement avec AWS KMS
- Clé par défaut ou clé personnalisée

---

### 🌐 3. Accès réseau

#### RDS - Pas d'accès public

**✅ Désactivé par défaut** :
```hcl
rds_publicly_accessible = false  # Par défaut
```

**Recommandation** :
- ✅ Utiliser des VPC et sous-réseaux privés
- ✅ Configurer des Security Groups restrictifs
- ✅ Utiliser AWS PrivateLink ou VPN pour l'accès

#### S3 - Blocage de l'accès public

**⚠️ À configurer manuellement** :
```hcl
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

---

### 💾 4. Sauvegardes et récupération

#### RDS - Backups automatiques

**✅ Configuré** :
```hcl
# En production : minimum 7 jours
backup_retention_period = var.environment == "prod" ? 7 : 1

# Fenêtre de backup (UTC)
backup_window = "03:00-04:00"
```

**Snapshot final** :
- ✅ Créé automatiquement en production avant suppression
- ❌ Désactivé en dev/staging (économie)

#### S3 - Versioning

**✅ Activé par défaut** :
```hcl
s3_versioning_enabled = true
```

---

### 🔄 5. Haute disponibilité

#### RDS - Multi-AZ

**✅ Activé automatiquement en production** :
```hcl
multi_az = var.environment == "prod" ? true : false
```

**Avantages** :
- Réplication synchrone dans une autre zone
- Basculement automatique en cas de panne
- Maintenance sans interruption

---

### 🛡️ 6. Protection contre la suppression

#### RDS - Deletion Protection

**✅ Activé automatiquement en production** :
```hcl
deletion_protection = var.environment == "prod" ? true : false
```

**Comportement** :
- Production : Impossible de supprimer sans désactiver manuellement
- Dev/Staging : Suppression libre (économie)

---

### 📊 7. Monitoring et audit

#### CloudWatch Logs

**✅ Activé automatiquement** :

**PostgreSQL** :
- Logs PostgreSQL
- Logs des upgrades

**MySQL** :
- Logs d'erreurs
- Logs généraux
- Logs des requêtes lentes

#### Tags obligatoires

**✅ Forcés sur toutes les ressources** :
```hcl
Owner        = "email@entreprise.com"  # Responsabilité
Squad        = "Nom-Equipe"            # Traçabilité
CostCenter   = "CC-XXX"                # Facturation
Environment  = "dev/staging/prod"      # Environnement
AutoShutdown = "true/false"            # Optimisation coûts
```

---

## 🚨 Risques identifiés et solutions

### ❌ Risque 1 : Terraform State contient des secrets

**Problème** :
Le fichier `terraform.tfstate` contient :
- Mots de passe RDS
- ARNs de ressources
- Configurations sensibles

**✅ Solution implémentée** :
```hcl
# .gitignore
*.tfstate
*.tfstate.*
*.tfvars
```

**✅ Solution recommandée - Backend S3** :
```hcl
# terraform/backend.tf
terraform {
  backend "s3" {
    bucket         = "mon-tfstate-bucket"
    key            = "aws-tagging-governance/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true                    # Chiffrement
    dynamodb_table = "terraform-state-lock"  # Verrouillage
    kms_key_id     = "arn:aws:kms:..."      # KMS personnalisé (optionnel)
  }
}
```

**Configuration du bucket** :
```bash
# 1. Créer le bucket
aws s3api create-bucket \
  --bucket mon-tfstate-bucket \
  --region eu-west-1 \
  --create-bucket-configuration LocationConstraint=eu-west-1

# 2. Activer le versioning
aws s3api put-bucket-versioning \
  --bucket mon-tfstate-bucket \
  --versioning-configuration Status=Enabled

# 3. Activer le chiffrement
aws s3api put-bucket-encryption \
  --bucket mon-tfstate-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# 4. Bloquer l'accès public
aws s3api put-public-access-block \
  --bucket mon-tfstate-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# 5. Créer la table DynamoDB pour le verrouillage
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

---

### ❌ Risque 2 : Variables sensibles dans les fichiers .tfvars

**Problème** :
Les fichiers `.tfvars` peuvent contenir des secrets.

**✅ Solution implémentée** :
```bash
# .gitignore
*.tfvars
!*.tfvars.example  # Les exemples sont OK
```

**✅ Bonne pratique** :
```bash
# Utiliser des variables d'environnement
export TF_VAR_rds_master_password="..."

# Ou utiliser AWS Secrets Manager dans Terraform
data "aws_secretsmanager_secret_version" "var" {
  secret_id = "terraform/variables"
}
```

---

### ❌ Risque 3 : Accès non autorisé aux secrets

**Problème** :
N'importe qui avec accès AWS peut lire les secrets.

**✅ Solution recommandée - IAM Policy restrictive** :
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:*-rds-credentials-*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "eu-west-1"
        }
      }
    }
  ]
}
```

---

## 📋 Checklist de sécurité

### Avant de déployer en production

- [ ] **Backend Terraform S3 configuré** avec chiffrement
- [ ] **IAM Roles** configurés avec le principe du moindre privilège
- [ ] **VPC et Security Groups** créés et configurés
- [ ] **RDS** :
  - [ ] `rds_storage_encrypted = true`
  - [ ] `rds_publicly_accessible = false`
  - [ ] `rds_multi_az = true`
  - [ ] `rds_backup_retention_period >= 7`
  - [ ] `rds_deletion_protection = true`
- [ ] **S3** :
  - [ ] Versioning activé
  - [ ] Blocage de l'accès public configuré
  - [ ] Lifecycle policies configurées
- [ ] **Secrets Manager** :
  - [ ] Rotation des secrets configurée (optionnel)
  - [ ] IAM policies restrictives
- [ ] **CloudWatch** :
  - [ ] Alarmes configurées
  - [ ] Logs activés et rétention configurée
- [ ] **AWS Config** :
  - [ ] Rules de conformité activées
  - [ ] Audit des tags obligatoires
- [ ] **Documentation** :
  - [ ] Runbook de récupération d'incident
  - [ ] Contacts d'urgence documentés

---

## 🔄 Maintenance et rotation des secrets

### Rotation manuelle des mots de passe RDS

```bash
# 1. Générer un nouveau mot de passe
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Mettre à jour le secret
aws secretsmanager update-secret \
  --secret-id dev-ma-db-rds-credentials \
  --secret-string "{\"password\":\"$NEW_PASSWORD\"}"

# 3. Mettre à jour RDS
aws rds modify-db-instance \
  --db-instance-identifier dev-ma-db \
  --master-user-password "$NEW_PASSWORD" \
  --apply-immediately
```

### Rotation automatique (recommandé)

```hcl
resource "aws_secretsmanager_secret" "rds_credentials" {
  # ...

  rotation_rules {
    automatically_after_days = 30
  }
}

resource "aws_secretsmanager_secret_rotation" "rds" {
  secret_id           = aws_secretsmanager_secret.rds_credentials.id
  rotation_lambda_arn = aws_lambda_function.rotate_secret.arn

  rotation_rules {
    automatically_after_days = 30
  }
}
```

---

## 📞 Support et ressources

### Documentation AWS

- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [RDS Security Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.Security.html)
- [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [Terraform Security Best Practices](https://developer.hashicorp.com/terraform/tutorials/cloud/terraform-security)

### Outils d'audit

- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [AWS Security Hub](https://aws.amazon.com/security-hub/)
- [Checkov](https://www.checkov.io/) - Scanner de sécurité Terraform
- [tfsec](https://github.com/aquasecurity/tfsec) - Scanner de sécurité Terraform

### Contact

- 📧 Email : cloud-governance@entreprise.com
- 💬 Slack : `#aws-security`
- 🚨 Incidents : `#aws-incidents`

---

**Dernière mise à jour** : 2026-02-09
**Version** : 1.0
**Auteur** : Cloud Governance Team
