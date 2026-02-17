# Dossier Sensible - Gestion des Secrets

Ce dossier centralise les informations sensibles du projet.

## Fichiers

| Fichier | Description | Dans Git ? |
|---------|-------------|------------|
| `.env` | Secrets reels (credentials AWS, mots de passe) | NON (gitignored) |
| `.env.example` | Template sans valeurs sensibles | OUI |

## Autres fichiers sensibles du projet

Ces fichiers sont proteges par `.gitignore` mais restent dans leurs dossiers respectifs
(deplacer ces fichiers casserait les outils qui les utilisent) :

| Fichier | Pourquoi sensible | Protection |
|---------|-------------------|------------|
| `terraform/environments/dev/terraform.tfstate` | Contient mots de passe RDS, ARN secrets | `.gitignore` (*.tfstate) |
| `terraform/environments/dev/terraform.tfstate.backup` | Copie de sauvegarde du state | `.gitignore` (*.tfstate.*) |
| `terraform/environments/dev/*.tfvars` | Variables avec valeurs sensibles | `.gitignore` (*.tfvars) |

## Utilisation

```bash
# 1. Copier le template
cp sensible/.env.example sensible/.env

# 2. Editer avec vos vraies valeurs
nano sensible/.env

# 3. Lancer Docker Compose (il lira automatiquement sensible/.env)
docker-compose up -d
```

## Bonne pratique recommandee

Pour les fichiers Terraform state, la meilleure protection est d'utiliser un **backend distant** (S3 + DynamoDB) au lieu de fichiers locaux. Voir `docs/SECURITY.md`.
