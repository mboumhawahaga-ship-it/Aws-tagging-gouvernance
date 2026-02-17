#!/bin/bash
# Script de validation des tags sur les ressources AWS existantes

set -e

echo "🔍 Validation des tags AWS"
echo "=========================="
echo ""

# Tags obligatoires
REQUIRED_TAGS=("Owner" "Squad" "CostCenter" "Environment")

# Fonction pour vérifier les tags d'une ressource
check_resource_tags() {
    local resource_arn=$1
    local resource_type=$2

    # Récupérer les tags
    tags=$(aws resourcegroupstaggingapi get-resources \
        --resource-arn-list "$resource_arn" \
        --query 'ResourceTagMappingList[0].Tags' \
        --output json)

    # Vérifier chaque tag obligatoire
    missing_tags=()
    for tag in "${REQUIRED_TAGS[@]}"; do
        if ! echo "$tags" | jq -e ".[] | select(.Key == \"$tag\")" > /dev/null 2>&1; then
            missing_tags+=("$tag")
        fi
    done

    # Afficher le résultat
    if [ ${#missing_tags[@]} -eq 0 ]; then
        echo "✅ $resource_type : $resource_arn"
    else
        echo "❌ $resource_type : $resource_arn"
        echo "   Tags manquants : ${missing_tags[*]}"
    fi
}

# Vérifier les instances EC2
echo "🖥️  Instances EC2 :"
instances=$(aws ec2 describe-instances \
    --query 'Reservations[].Instances[].InstanceId' \
    --output text)

if [ -z "$instances" ]; then
    echo "   Aucune instance trouvée"
else
    for instance_id in $instances; do
        instance_arn="arn:aws:ec2:$(aws configure get region):$(aws sts get-caller-identity --query Account --output text):instance/$instance_id"
        check_resource_tags "$instance_arn" "EC2"
    done
fi
echo ""

# Vérifier les buckets S3
echo "🪣 Buckets S3 :"
buckets=$(aws s3api list-buckets --query 'Buckets[].Name' --output text)

if [ -z "$buckets" ]; then
    echo "   Aucun bucket trouvé"
else
    for bucket in $buckets; do
        # S3 utilise un format différent
        tags=$(aws s3api get-bucket-tagging --bucket "$bucket" 2>/dev/null || echo "{}")

        missing_tags=()
        for tag in "${REQUIRED_TAGS[@]}"; do
            if ! echo "$tags" | jq -e ".TagSet[] | select(.Key == \"$tag\")" > /dev/null 2>&1; then
                missing_tags+=("$tag")
            fi
        done

        if [ ${#missing_tags[@]} -eq 0 ]; then
            echo "✅ S3 : $bucket"
        else
            echo "❌ S3 : $bucket"
            echo "   Tags manquants : ${missing_tags[*]}"
        fi
    done
fi
echo ""

# Vérifier les fonctions Lambda
echo "⚡ Fonctions Lambda :"
functions=$(aws lambda list-functions --query 'Functions[].FunctionArn' --output text)

if [ -z "$functions" ]; then
    echo "   Aucune fonction trouvée"
else
    for func_arn in $functions; do
        check_resource_tags "$func_arn" "Lambda"
    done
fi
echo ""

echo "✅ Validation terminée !"
