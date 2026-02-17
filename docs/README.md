# 🏛️ AWS Tagging Governance

**Système complet de gouvernance de tagging pour AWS**

Forcez le respect des politiques de tagging sur toutes vos ressources AWS pour :
- 💰 Maîtriser les coûts par équipe
- 🔍 Améliorer la traçabilité
- 🤖 Automatiser la gestion du cycle de vie
- 📊 Visualiser les dépenses

---

## 📁 Structure du projet

```
aws-tagging-governance/
├── terraform/
│   ├── modules/
│   │   └── tagged-resources/     # ✅ Module de tagging réutilisable
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       ├── outputs.tf
│   │       ├── versions.tf
│   │       └── README.md
│   ├── environments/
│   │   ├── dev/                  # ✅ Exemples d'utilisation
│   │   │   ├── main.tf
│   │   │   ├── outputs.tf
│   │   │   └── terraform.tfvars.example
│   │   └── prod/
│   └── policies/                 # 🔜 AWS Config rules
├── lambda/
│   ├── cleanup/                  # 🔜 Auto-cleanup des ressources
│   └── notifications/            # 🔜 Alertes SNS
├── grafana/
│   └── dashboards/               # 🔜 Visualisation des coûts
├── scripts/
│   └── deploy.sh                 # 🔜 Script de déploiement
└── docs/
    ├── README.md
    └── architecture.md           # 🔜 Documentation architecture
```

**Légende** :
- ✅ = Créé
- 🔜 = À venir

---

## 🎯 Tags obligatoires

Toutes les ressources AWS **doivent** avoir ces tags :

| Tag | Type | Description | Exemple |
|-----|------|-------------|---------|
| `Owner` | string | Propriétaire de la ressource | `jean.dupont@entreprise.com` |
| `Squad` | string | Équipe responsable | `Data`, `Backend`, `DevOps` |
| `CostCenter` | string | Centre de coûts | `CC-123` |
| `AutoShutdown` | bool | Arrêt automatique hors heures ouvrées | `true` / `false` |
| `Environment` | string | Environnement | `dev`, `staging`, `prod` |

**Tags automatiques ajoutés** :
- `ManagedBy` : `Terraform`
- `CreatedAt` : Timestamp de création

---

## 🚀 Démarrage rapide

### 1. Installer Terraform

```bash
# Windows (avec Chocolatey)
choco install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### 2. Configurer AWS CLI

```bash
aws configure
# AWS Access Key ID: VOTRE_ACCESS_KEY
# AWS Secret Access Key: VOTRE_SECRET_KEY
# Default region: eu-west-1
```

### 3. Utiliser le module

```bash
cd terraform/environments/dev

# Initialiser Terraform
terraform init

# Voir ce qui va être créé
terraform plan

# Créer les ressources
terraform apply
```

---

## 📖 Guide d'utilisation

### Créer un serveur EC2

```hcl
module "mon_serveur" {
  source = "../../modules/tagged-resources"

  resource_type = "ec2"
  resource_name = "web-server"

  owner       = "votre.nom@entreprise.com"
  squad       = "VotreEquipe"
  cost_center = "CC-XXX"
  environment = "dev"

  auto_shutdown = true
}
```

### Créer une base de données RDS

```hcl
module "ma_base" {
  source = "../../modules/tagged-resources"

  resource_type = "rds"
  resource_name = "postgres-db"

  owner       = "votre.nom@entreprise.com"
  squad       = "VotreEquipe"
  cost_center = "CC-XXX"
  environment = "prod"

  rds_engine         = "postgres"
  rds_instance_class = "db.t3.small"
}
```

Voir plus d'exemples dans [`terraform/modules/tagged-resources/README.md`](terraform/modules/tagged-resources/README.md)

---

## ✅ Ce qui a été créé

### ✅ Module Terraform de tagging

**Fichiers** :
- [`terraform/modules/tagged-resources/main.tf`](terraform/modules/tagged-resources/main.tf) - Logique de création des ressources
- [`terraform/modules/tagged-resources/variables.tf`](terraform/modules/tagged-resources/variables.tf) - Variables avec validation
- [`terraform/modules/tagged-resources/outputs.tf`](terraform/modules/tagged-resources/outputs.tf) - Outputs pour récupérer les infos
- [`terraform/modules/tagged-resources/versions.tf`](terraform/modules/tagged-resources/versions.tf) - Versions Terraform/AWS

**Fonctionnalités** :
- ✅ Tags obligatoires avec validation stricte
- ✅ Support EC2, RDS, S3, Lambda
- ✅ Chiffrement automatique (S3)
- ✅ Versioning S3 par défaut
- ✅ Monitoring activé en prod (EC2)
- ✅ IAM Roles automatiques (Lambda)

### ✅ Exemples d'utilisation

**Fichiers** :
- [`terraform/environments/dev/main.tf`](terraform/environments/dev/main.tf) - 4 exemples de ressources
- [`terraform/environments/dev/outputs.tf`](terraform/environments/dev/outputs.tf) - Affichage des résultats
- [`terraform/environments/dev/terraform.tfvars.example`](terraform/environments/dev/terraform.tfvars.example) - Template de variables

---

## 🔜 Prochaines étapes

### Phase 2 : Gouvernance automatisée

- [ ] **AWS Config Rules** : Détection des ressources non conformes
- [ ] **Lambda de cleanup** : Suppression automatique des ressources mal tagguées
- [ ] **SNS Notifications** : Alertes en cas de non-conformité

### Phase 3 : Visualisation

- [ ] **Grafana Dashboard** : Visualisation des coûts par tags
- [ ] **Rapports mensuels** : Facturation par équipe/projet
- [ ] **Alertes budgétaires** : Notification si dépassement

### Phase 4 : Extensions

- [ ] Support ECS/EKS/Fargate
- [ ] Support ElastiCache/DynamoDB
- [ ] Intégration avec Terraform Cloud
- [ ] API de validation des tags

---

## 📚 Documentation

- [Module Terraform - README](terraform/modules/tagged-resources/README.md) - Documentation complète du module
- [Exemples Dev](terraform/environments/dev/) - Exemples d'utilisation
- [Architecture](docs/architecture.md) - 🔜 Schéma d'architecture

---

## 🛠️ Commandes utiles

### Terraform

```bash
# Initialiser
terraform init

# Valider la syntaxe
terraform validate

# Formatter le code
terraform fmt -recursive

# Planifier les changements
terraform plan

# Appliquer les changements
terraform apply

# Détruire les ressources
terraform destroy
```

### AWS CLI - Vérifier les tags

```bash
# Lister les instances EC2 avec leurs tags
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId, Tags]'

# Lister les buckets S3 avec leurs tags
aws s3api list-buckets --query 'Buckets[].Name' | xargs -I {} aws s3api get-bucket-tagging --bucket {}

# Lister les ressources sans tag Owner
aws resourcegroupstaggingapi get-resources --tag-filters Key=Owner,Values=
```

---

## ⚠️ Bonnes pratiques

### ✅ À faire

- Toujours utiliser le module pour créer des ressources
- Mettre des emails dans le tag `Owner`
- Utiliser `auto_shutdown=true` en dev/staging
- Documenter les tags additionnels

### ❌ À éviter

- Créer des ressources manuellement via la console AWS
- Laisser des tags vides
- Utiliser des noms d'équipe ambigus
- Oublier de détruire les ressources de test

---

## 🤝 Contribution

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Commitez vos changements (`git commit -m 'Ajout fonctionnalité X'`)
4. Push vers la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

---

## 📞 Support

- 📧 Email : cloud-governance@entreprise.com
- 💬 Slack : `#aws-governance`
- 📖 Wiki : [Confluence - AWS Tagging](https://confluence.entreprise.com/aws-tagging)

---

## 📄 Licence

MIT License - Voir [LICENSE](LICENSE)

---

**Fait avec ❤️ par l'équipe Cloud Governance**
