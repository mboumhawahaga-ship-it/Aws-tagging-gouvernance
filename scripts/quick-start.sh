#!/bin/bash
# Script de démarrage rapide pour AWS Tagging Governance

set -e

echo "🚀 AWS Tagging Governance - Quick Start"
echo "========================================"
echo ""

# Vérifier que Terraform est installé
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform n'est pas installé."
    echo "📥 Installez-le : https://www.terraform.io/downloads"
    exit 1
fi

echo "✅ Terraform détecté : $(terraform version | head -n1)"

# Vérifier que AWS CLI est configuré
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI n'est pas installé."
    echo "📥 Installez-le : https://aws.amazon.com/cli/"
    exit 1
fi

echo "✅ AWS CLI détecté : $(aws --version)"

# Vérifier les credentials AWS
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS n'est pas configuré."
    echo "🔧 Configurez-le : aws configure"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "eu-west-1")

echo "✅ AWS Account: $AWS_ACCOUNT"
echo "✅ AWS Region: $AWS_REGION"
echo ""

# Aller dans le dossier dev
cd "$(dirname "$0")/../terraform/environments/dev"

echo "📂 Répertoire de travail : $(pwd)"
echo ""

# Initialiser Terraform
echo "🔧 Initialisation de Terraform..."
terraform init

echo ""
echo "✅ Initialisation terminée !"
echo ""
echo "📋 Prochaines étapes :"
echo ""
echo "1️⃣  Modifier les variables dans main.tf :"
echo "   - owner, squad, cost_center"
echo ""
echo "2️⃣  Valider la configuration :"
echo "   terraform validate"
echo ""
echo "3️⃣  Voir le plan d'exécution :"
echo "   terraform plan"
echo ""
echo "4️⃣  Créer les ressources :"
echo "   terraform apply"
echo ""
echo "💡 Astuce : Commencez par créer une seule ressource pour tester !"
echo ""
