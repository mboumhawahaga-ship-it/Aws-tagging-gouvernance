# 🏷️ Module Terraform : Tagged Resources

Ce module **force le tagging strict** sur toutes vos ressources AWS pour garantir la gouvernance et la traçabilité.

## 📋 Vue d'ensemble

**Problème résolu** : Empêcher la création de ressources AWS sans tags obligatoires.

**Tags obligatoires** :
- `Owner` : Propriétaire de la ressource
- `Squad` : Équipe responsable
- `CostCenter` : Centre de coûts pour facturation
- `AutoShutdown` : Arrêt automatique (true/false)
- `Environment` : Environnement (dev/staging/prod)

**Ressources supportées** :
- ✅ EC2 (instances)
- ✅ RDS (bases de données)
- ✅ S3 (buckets)
- ✅ Lambda (fonctions)

---

## 🚀 Utilisation rapide

### Exemple minimal : Créer un serveur EC2

```hcl
module "mon_serveur" {
  source = "../../modules/tagged-resources"

  resource_type = "ec2"
  resource_name = "web-server"

  # Tags obligatoires
  owner       = "Jean Dupont"
  squad       = "Data"
  cost_center = "CC-123"
  environment = "dev"
}
```

### Exemple avec options : Base de données RDS

```hcl
module "ma_database" {
  source = "../../modules/tagged-resources"

  resource_type = "rds"
  resource_name = "postgres-db"

  # Tags obligatoires
  owner       = "Marie Martin"
  squad       = "Backend"
  cost_center = "CC-456"
  environment = "prod"

  # Options RDS
  rds_engine         = "postgres"
  rds_instance_class = "db.t3.small"

  # Tags additionnels
  additional_tags = {
    Backup = "Daily"
    Project = "API"
  }
}
```

---

## 📥 Inputs (Variables)

### Variables obligatoires

| Nom | Type | Description |
|-----|------|-------------|
| `resource_type` | string | Type de ressource : `ec2`, `rds`, `s3`, `lambda` |
| `resource_name` | string | Nom de la ressource |
| `owner` | string | Propriétaire (nom ou email) |
| `squad` | string | Équipe responsable |
| `cost_center` | string | Code du centre de coûts |

### Variables optionnelles

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `environment` | string | `dev` | Environnement (dev, staging, prod) |
| `auto_shutdown` | bool | `false` | Arrêt automatique |
| `additional_tags` | map(string) | `{}` | Tags supplémentaires |

### Variables spécifiques EC2

| Nom | Type | Défaut |
|-----|------|--------|
| `ec2_instance_type` | string | `t3.micro` |
| `ec2_ami` | string | Dernière Amazon Linux 2 |

### Variables spécifiques RDS

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `rds_engine` | string | `postgres` | Moteur de base de données |
| `rds_instance_class` | string | `db.t3.micro` | Classe d'instance |
| `rds_master_username` | string | `admin` | Nom d'utilisateur master |
| `rds_allocated_storage` | number | `20` | Stockage alloué en GB |
| `rds_generate_random_password` | bool | `true` | 🔐 Génération auto du mot de passe (recommandé) |
| `rds_master_password` | string | `null` | ⚠️ Mot de passe manuel (NON recommandé) |
| `rds_storage_encrypted` | bool | `true` | 🔒 Chiffrement au repos (recommandé) |
| `rds_backup_retention_period` | number | `7` | Rétention des backups (0-35 jours) |
| `rds_multi_az` | bool | `false` | Haute disponibilité Multi-AZ |
| `rds_deletion_protection` | bool | `false` | Protection contre la suppression |
| `rds_publicly_accessible` | bool | `false` | 🔒 Accès public (NON recommandé) |

### Variables spécifiques S3

| Nom | Type | Défaut |
|-----|------|--------|
| `s3_versioning_enabled` | bool | `true` |

### Variables spécifiques Lambda

| Nom | Type | Défaut |
|-----|------|--------|
| `lambda_runtime` | string | `python3.11` |
| `lambda_handler` | string | `index.handler` |
| `lambda_filename` | string | `null` |

---

## 📤 Outputs

### Outputs généraux

- `resource_id` : ID de la ressource créée
- `resource_arn` : ARN de la ressource
- `resource_name` : Nom complet (avec préfixe environnement)
- `applied_tags` : Tous les tags appliqués
- `mandatory_tags` : Tags obligatoires
- `resource_type` : Type de ressource

### Outputs spécifiques

**EC2** :
- `ec2_public_ip` : IP publique
- `ec2_private_ip` : IP privée

**RDS** :
- `rds_endpoint` : Endpoint de connexion
- `rds_port` : Port
- `rds_secret_arn` : 🔐 ARN du secret AWS Secrets Manager
- `rds_secret_name` : 🔐 Nom du secret contenant les credentials
- `rds_master_username` : Nom d'utilisateur master

**S3** :
- `s3_bucket_name` : Nom du bucket
- `s3_bucket_domain` : Nom de domaine

**Lambda** :
- `lambda_function_name` : Nom de la fonction
- `lambda_invoke_arn` : ARN d'invocation

---

## ✅ Validations intégrées

Le module **refuse** de créer une ressource si :

1. ❌ Un tag obligatoire est manquant
2. ❌ Un tag obligatoire est vide (`""`)
3. ❌ Le type de ressource est invalide
4. ❌ L'environnement n'est pas `dev`, `staging` ou `prod`

**Exemple d'erreur** :

```bash
Error: owner tag is mandatory and cannot be empty
```

---

## 🔒 Sécurité

### ✅ Gestion sécurisée des mots de passe RDS (AWS Secrets Manager)

Le module utilise **AWS Secrets Manager** pour une gestion sécurisée des credentials.

**Par défaut**, un mot de passe aléatoire de 32 caractères est généré automatiquement :

```hcl
module "ma_database" {
  source = "../../modules/tagged-resources"

  resource_type = "rds"
  resource_name = "prod-db"

  # ... tags obligatoires ...

  # 🔐 Génération automatique (RECOMMANDÉ)
  rds_generate_random_password = true  # Par défaut
}
```

**Le secret contient** :
```json
{
  "username": "admin",
  "password": "***généré-32-caractères***",
  "engine": "postgres",
  "host": "prod-db.xxx.rds.amazonaws.com",
  "port": 5432,
  "dbname": "postgres",
  "dbInstanceIdentifier": "prod-db"
}
```

**Récupérer le mot de passe** :

```bash
# Via Terraform output
terraform output rds_secret_name

# Via AWS CLI
aws secretsmanager get-secret-value \
  --secret-id prod-db-rds-credentials \
  --query SecretString --output text | jq -r .password
```

**Dans votre application** :

```python
import boto3, json

client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='prod-db-rds-credentials')
creds = json.loads(secret['SecretString'])

# Utilisation
db_url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['dbname']}"
```

### 🔐 Chiffrement et sécurité

**Chiffrement activé par défaut** :
- ✅ **RDS** : Chiffrement au repos avec AWS KMS (`storage_encrypted = true`)
- ✅ **S3** : Chiffrement AES-256 activé automatiquement
- ✅ **Secrets Manager** : Chiffré avec AWS KMS

**Meilleures pratiques appliquées** :
- ✅ Pas d'accès public par défaut (`publicly_accessible = false`)
- ✅ Backups automatiques (7 jours en prod, configurable)
- ✅ Multi-AZ automatique en production (haute disponibilité)
- ✅ Protection contre la suppression en production
- ✅ Mises à jour mineures automatiques
- ✅ Logs CloudWatch activés (PostgreSQL/MySQL)

### 🔒 Terraform State

⚠️ **IMPORTANT** : Le Terraform state contient des secrets.

**Solution recommandée** : Backend S3 chiffré

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "mon-bucket-tfstate"
    key            = "terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true                    # Chiffrement du state
    dynamodb_table = "terraform-locks"       # Verrouillage
    kms_key_id     = "arn:aws:kms:..."      # Optionnel : KMS personnalisé
  }
}
```

**Ne JAMAIS committer** :
- ❌ `terraform.tfstate` (déjà dans `.gitignore`)
- ❌ `*.tfvars` avec des secrets (déjà dans `.gitignore`)
- ❌ Fichiers `.pem`, `.key`, `credentials.*`

---

## 📚 Exemples complets

Consultez le dossier [`terraform/environments/dev/`](../../environments/dev/) pour voir des exemples réels d'utilisation avec :
- EC2
- RDS
- S3
- Lambda

---

## 🛠️ Commandes Terraform

### Initialisation
```bash
cd terraform/environments/dev
terraform init
```

### Validation (vérifie les tags obligatoires)
```bash
terraform validate
```

### Planification (voir ce qui va être créé)
```bash
terraform plan
```

### Application (créer les ressources)
```bash
terraform apply
```

### Destruction
```bash
terraform destroy
```

---

## 🎯 Cas d'usage

### 1. Environnement de dev avec auto-shutdown
```hcl
module "dev_server" {
  source = "../../modules/tagged-resources"

  resource_type = "ec2"
  resource_name = "test-server"
  owner         = "Votre Nom"
  squad         = "Dev"
  cost_center   = "CC-000"
  environment   = "dev"
  auto_shutdown = true  # ← S'éteint automatiquement
}
```

### 2. Base de données de production
```hcl
module "prod_db" {
  source = "../../modules/tagged-resources"

  resource_type       = "rds"
  resource_name       = "main-db"
  owner               = "DBA Team"
  squad               = "Backend"
  cost_center         = "CC-PROD"
  environment         = "prod"
  rds_instance_class  = "db.r5.large"
  auto_shutdown       = false  # ← Jamais éteint
}
```

---

## 🔄 Feuille de route

- [ ] Ajouter support ECS/EKS
- [ ] Intégration AWS Config pour audit
- [ ] Lambda d'auto-cleanup des ressources non-tagguées
- [ ] Dashboard Grafana de visualisation des coûts par tags

---

## 📞 Support

Pour toute question, contactez l'équipe Cloud Governance.
