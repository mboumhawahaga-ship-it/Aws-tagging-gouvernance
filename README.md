# AWS Tagging Governance

![Quality & Security Check](https://github.com/mboumhawahaga-ship-it/Aws-tagging-gouvernance/actions/workflows/ci-quality.yml/badge.svg)

**Systeme complet de gouvernance de tagging pour AWS**

Forcez le respect des politiques de tagging sur toutes vos ressources AWS pour :
- Maitriser les couts par equipe
- Ameliorer la tracabilite
- Automatiser la gestion du cycle de vie
- Visualiser les depenses

---

## Structure du projet

```
aws-tagging-governance/
├── .github/workflows/
│   └── ci-quality.yml              # CI/CD : Flake8 + Terraform fmt/validate
├── terraform/
│   ├── modules/
│   │   ├── tagged-resources/       # Module de tagging reutilisable
│   │   ├── cleanup-lambda/         # Module Lambda de nettoyage
│   │   └── metrics-lambda/         # Module Lambda de metriques
│   ├── environments/
│   │   └── dev/                    # Environnement de dev
│   └── policies/                   # AWS Config rules (a venir)
├── lambda/
│   ├── cleanup/                    # Auto-cleanup des ressources non conformes
│   └── metrics/                    # Collecte de metriques CloudWatch
├── grafana/
│   ├── dashboards/                 # Dashboard de visualisation des couts
│   └── provisioning/               # Configuration automatique datasources
├── sensible/                       # Secrets centralises (gitignored)
│   ├── .env                        # Variables d'environnement (NON commite)
│   └── .env.example                # Template a copier
├── scripts/                        # Scripts d'automatisation
├── docs/                           # Documentation detaillee
│   ├── GUIDE_DEMARRAGE.md          # Guide pas-a-pas pour debutants
│   ├── SECURITY.md                 # Bonnes pratiques securite
│   └── JOURNAL_DE_BORD.md          # Journal de diagnostic et solutions
└── docker-compose.yml              # Grafana local + CloudWatch
```

---

## Tags obligatoires

Toutes les ressources AWS **doivent** avoir ces tags :

| Tag | Type | Description | Exemple |
|-----|------|-------------|---------|
| `Owner` | string | Email du proprietaire | `jean.dupont@entreprise.com` |
| `Squad` | string | Equipe responsable | `Data`, `Backend`, `DevOps` |
| `CostCenter` | string | Centre de couts | `CC-123` |
| `AutoShutdown` | bool | Arret automatique hors heures | `true` / `false` |
| `Environment` | string | Environnement | `dev`, `staging`, `prod` |

**Tags automatiques ajoutes** :
- `ManagedBy` : `Terraform`
- `CreatedAt` : Timestamp de creation (stable via `time_static`)

---

## Demarrage rapide

```bash
# 1. Cloner le projet
git clone https://github.com/VOTRE-USERNAME/aws-tagging-governance.git
cd aws-tagging-governance

# 2. Configurer les secrets
cp sensible/.env.example sensible/.env
# Editez sensible/.env avec vos credentials AWS

# 3. Deployer l'infrastructure
cd terraform/environments/dev
terraform init
terraform plan     # Voir ce qui va etre cree
terraform apply    # Creer les ressources

# 4. Lancer le dashboard Grafana (optionnel)
cd ../../..
docker-compose up -d
# Ouvrir http://localhost:3000
```

---

## Fonctionnalites

### Module Terraform de tagging
- Tags obligatoires avec validation stricte (regex email, valeurs autorisees)
- Support EC2, RDS, S3, Lambda
- Chiffrement automatique (RDS, S3)
- Generation de mots de passe RDS via Secrets Manager

### Lambda de cleanup automatique
- Scanne EC2, RDS, S3, Lambda pour la conformite
- Periode de grace de 24h avant suppression
- Mode DRY_RUN par defaut (simulation sans suppression)
- Notifications SNS avec rapport detaille

### Lambda de metriques
- Collecte les taux de conformite des tags
- Interroge Cost Explorer par Squad/CostCenter
- Publie dans CloudWatch (namespaces custom)
- Execution automatique toutes les 6 heures

### Dashboard Grafana
- Visualisation de la conformite des tags
- Couts par equipe et projet
- Nombre de ressources et economies estimees

### CI/CD (GitHub Actions)
- Lint Python avec Flake8
- Formatage Terraform (`terraform fmt -check`)
- Validation Terraform (`terraform validate`)

---

## Documentation

- [Guide de demarrage](docs/GUIDE_DEMARRAGE.md) - Pas-a-pas pour debutants
- [Securite](docs/SECURITY.md) - Bonnes pratiques et checklist
- [Journal de bord](docs/JOURNAL_DE_BORD.md) - Diagnostic d'erreurs et solutions
- [Module tagged-resources](terraform/modules/tagged-resources/README.md) - Documentation du module

---

## Commandes utiles

```bash
# Valider la syntaxe Terraform
terraform validate

# Formatter le code Terraform
terraform fmt -recursive

# Verifier les tags d'une instance EC2
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId, Tags]'

# Tester la Lambda de cleanup (mode simulation)
aws lambda invoke --function-name dev-tag-cleanup output.json && cat output.json
```

---

## Licence

MIT License
