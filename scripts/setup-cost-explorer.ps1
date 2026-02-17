# ========================================
# Activation de Cost Explorer et des Cost Allocation Tags
# A executer UNE SEULE FOIS sur le compte AWS
# ========================================

Write-Host "Activation des Cost Allocation Tags..." -ForegroundColor Cyan

# Activer les tags comme Cost Allocation Tags
# Note : les tags doivent d'abord apparaitre dans le systeme de facturation (~24h apres creation des ressources)
aws ce update-cost-allocation-tags-status `
    --cost-allocation-tags-status `
    TagKey=Owner,Status=Active `
    TagKey=Squad,Status=Active `
    TagKey=CostCenter,Status=Active `
    TagKey=Environment,Status=Active

if ($LASTEXITCODE -eq 0) {
    Write-Host "Cost Allocation Tags actives avec succes !" -ForegroundColor Green
} else {
    Write-Host "Erreur : les tags ne sont pas encore visibles dans le systeme de facturation." -ForegroundColor Yellow
    Write-Host "Attendez 24h apres la creation des ressources puis relancez ce script." -ForegroundColor Yellow
}

# Verification
Write-Host "`nVerification des tags actifs :" -ForegroundColor Cyan
aws ce list-cost-allocation-tags --status Active

Write-Host "`nTest Cost Explorer (couts du mois en cours) :" -ForegroundColor Cyan
$startDate = (Get-Date -Day 1).ToString("yyyy-MM-dd")
$endDate = (Get-Date).ToString("yyyy-MM-dd")
aws ce get-cost-and-usage `
    --time-period Start=$startDate,End=$endDate `
    --granularity MONTHLY `
    --metrics BlendedCost
