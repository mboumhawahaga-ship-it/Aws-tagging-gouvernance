# 📘 Guide de démarrage - Pour débutants

Ce guide vous explique **pas à pas** comment utiliser le système de tagging.

---

## 🎯 Objectif

**Avant** : Les développeurs créent des serveurs AWS sans organisation.
**Après** : Impossible de créer un serveur sans mettre les tags obligatoires !

---

## 📋 Prérequis

### 1. Installer Terraform

**Windows** :
```bash
# Avec Chocolatey
choco install terraform

# Ou téléchargez sur https://www.terraform.io/downloads
```

**Linux/Mac** :
```bash
# Ubuntu/Debian
sudo apt-get install terraform

# MacOS
brew install terraform
```

Vérifiez l'installation :
```bash
terraform --version
# Doit afficher : Terraform v1.6.x ou supérieur
```

### 2. Installer AWS CLI

**Windows** :
```bash
# Téléchargez sur https://aws.amazon.com/cli/
```

**Linux/Mac** :
```bash
# Ubuntu/Debian
sudo apt-get install awscli

# MacOS
brew install awscli
```

Vérifiez l'installation :
```bash
aws --version
# Doit afficher : aws-cli/2.x.x
```

### 3. Configurer AWS

```bash
aws configure
```

Vous devez entrer :
- **AWS Access Key ID** : Demandez à votre admin AWS
- **AWS Secret Access Key** : Demandez à votre admin AWS
- **Default region** : `eu-west-1` (Paris)
- **Default output format** : `json`

Testez la connexion :
```bash
aws sts get-caller-identity
# Doit afficher votre compte AWS
```

---

## 🚀 Utilisation en 5 étapes

### Étape 1 : Aller dans le dossier

```bash
cd aws-tagging-governance/terraform/environments/dev
```

### Étape 2 : Initialiser Terraform

```bash
terraform init
```

**Résultat attendu** :
```
Initializing modules...
Terraform has been successfully initialized!
```

### Étape 3 : Modifier les variables

Ouvrez le fichier [`main.tf`](../terraform/environments/dev/main.tf) et modifiez :

```hcl
module "web_server" {
  source = "../../modules/tagged-resources"

  resource_type = "ec2"
  resource_name = "test-server"

  # 👇 CHANGEZ CES VALEURS 👇
  owner       = "votre.nom@entreprise.com"  # ← Votre email
  squad       = "VotreEquipe"                # ← Votre équipe
  cost_center = "CC-XXX"                     # ← Votre code de coût
  environment = "dev"

  auto_shutdown = true
}
```

### Étape 4 : Voir ce qui va être créé

```bash
terraform plan
```

**Résultat attendu** :
```
Terraform will perform the following actions:

  # module.web_server.aws_instance.this[0] will be created
  + resource "aws_instance" "this" {
      + tags = {
          + "Owner"        = "votre.nom@entreprise.com"
          + "Squad"        = "VotreEquipe"
          + "CostCenter"   = "CC-XXX"
          + "Environment"  = "dev"
          + "AutoShutdown" = "true"
        }
    }

Plan: 1 to add, 0 to change, 0 to destroy.
```

### Étape 5 : Créer la ressource

```bash
terraform apply
```

Tapez `yes` quand on vous le demande.

**Résultat attendu** :
```
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:

web_server_ip = "54.123.45.67"
web_server_tags = {
  "Owner" = "votre.nom@entreprise.com"
  "Squad" = "VotreEquipe"
  ...
}
```

---

## ✅ Vérifier que ça marche

### Dans AWS Console

1. Allez sur https://console.aws.amazon.com/ec2/
2. Cliquez sur "Instances"
3. Trouvez votre instance `dev-test-server`
4. Cliquez sur l'onglet "Tags"
5. Vérifiez que tous les tags sont présents !

### En ligne de commande

```bash
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId, Tags]'
```

---

## 🧪 Tester la validation

Essayez de **supprimer** un tag obligatoire dans `main.tf` :

```hcl
module "web_server" {
  source = "../../modules/tagged-resources"

  resource_type = "ec2"
  resource_name = "test-server"

  # owner = "..."  ← ON COMMENTE CETTE LIGNE
  squad       = "VotreEquipe"
  cost_center = "CC-XXX"
}
```

Puis :
```bash
terraform plan
```

**Résultat attendu** :
```
❌ Error: owner tag is mandatory and cannot be empty
```

🎉 **La validation fonctionne !**

---

## 🧹 Détruire les ressources de test

**IMPORTANT** : Pour éviter les coûts, détruisez les ressources de test :

```bash
terraform destroy
```

Tapez `yes` pour confirmer.

---

## 📚 Exemples de cas d'usage

### Créer un serveur web

```hcl
module "mon_web_server" {
  source = "../../modules/tagged-resources"

  resource_type = "ec2"
  resource_name = "nginx-server"

  owner       = "dev@entreprise.com"
  squad       = "Frontend"
  cost_center = "CC-WEB"
  environment = "dev"

  ec2_instance_type = "t3.small"
  auto_shutdown     = true

  additional_tags = {
    Application = "Website"
    Port        = "80"
  }
}
```

### Créer une base de données

```hcl
module "ma_database" {
  source = "../../modules/tagged-resources"

  resource_type = "rds"
  resource_name = "postgres-main"

  owner       = "dba@entreprise.com"
  squad       = "Backend"
  cost_center = "CC-DB"
  environment = "prod"

  rds_engine         = "postgres"
  rds_instance_class = "db.t3.medium"

  additional_tags = {
    Backup     = "Daily"
    Encryption = "AES256"
  }
}
```

### Créer un bucket S3

```hcl
module "mon_bucket" {
  source = "../../modules/tagged-resources"

  resource_type = "s3"
  resource_name = "data-backup"

  owner       = "data@entreprise.com"
  squad       = "DataEngineering"
  cost_center = "CC-DATA"
  environment = "prod"

  s3_versioning_enabled = true

  additional_tags = {
    Retention = "7years"
    Public    = "false"
  }
}
```

---

## ❓ FAQ

### Q : Que se passe-t-il si j'oublie un tag ?
**R** : Terraform refuse de créer la ressource et affiche une erreur.

### Q : Puis-je créer des ressources sans ce module ?
**R** : Techniquement oui, mais c'est **fortement déconseillé**. Le module garantit la conformité.

### Q : Comment modifier les tags d'une ressource existante ?
**R** : Modifiez le code Terraform et lancez `terraform apply`.

### Q : Puis-je utiliser ce module en production ?
**R** : Oui, mais changez `environment = "prod"` et utilisez AWS Secrets Manager pour les mots de passe.

### Q : Comment voir tous mes tags ?
**R** : Utilisez le script : `bash scripts/validate-tags.sh`

---

## 🆘 Problèmes courants

### Erreur : "No valid credential sources found"

**Cause** : AWS CLI n'est pas configuré.
**Solution** : Lancez `aws configure`

### Erreur : "provider registry.terraform.io/hashicorp/aws"

**Cause** : Terraform n'est pas initialisé.
**Solution** : Lancez `terraform init`

### Erreur : "Error: Insufficient owner blocks"

**Cause** : Le tag `owner` est manquant.
**Solution** : Ajoutez `owner = "votre.email@entreprise.com"` dans le module.

---

## 📞 Besoin d'aide ?

- 📧 Email : cloud-governance@entreprise.com
- 💬 Slack : `#aws-governance`
- 📖 Documentation complète : [README.md](../README.md)

---

**Bon courage ! 🚀**
