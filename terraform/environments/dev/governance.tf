module "governance" {
  source = "../../modules/governance-pipeline"

  environment        = "dev"
  aws_region         = "eu-west-1"
  admin_email        = "votre.email@exemple.com" # ← CHANGEZ CETTE VALEUR
  slack_webhook_url  = ""                         # ← optionnel, laisser vide si pas de Slack
  dry_run            = true
  scan_schedule      = "rate(6 hours)"
  log_retention_days = 7
}
