# ========================================
# MODULE LAMBDA DE CLEANUP AUTOMATIQUE
# ========================================

locals {
  lambda_name = "${var.environment}-tag-cleanup"
  lambda_zip  = "${path.module}/lambda_function.zip"
}

# ========================================
# TOPIC SNS POUR LES NOTIFICATIONS
# ========================================

resource "aws_sns_topic" "cleanup_notifications" {
  name = "${local.lambda_name}-notifications"

  tags = {
    Name        = "${local.lambda_name}-notifications"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "email" {
  count = var.notification_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.cleanup_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# ========================================
# RÔLE IAM POUR LA LAMBDA
# ========================================

resource "aws_iam_role" "lambda_role" {
  name = "${local.lambda_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${local.lambda_name}-role"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

# Politique pour les logs CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Politique personnalisée pour gérer les ressources
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.lambda_name}-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # EC2
          "ec2:DescribeInstances",
          "ec2:TerminateInstances",
          "ec2:DescribeTags",
          # RDS
          "rds:DescribeDBInstances",
          "rds:DeleteDBInstance",
          "rds:ListTagsForResource",
          # S3
          "s3:ListAllMyBuckets",
          "s3:GetBucketTagging",
          "s3:DeleteBucket",
          "s3:ListBucket",
          "s3:DeleteObject",
          # Lambda
          "lambda:ListFunctions",
          "lambda:ListTags",
          "lambda:DeleteFunction",
          # Tag API
          "tag:GetResources",
          "tag:GetTagKeys",
          "tag:GetTagValues",
          # SNS
          "sns:Publish"
        ]
        Resource = "*"
      }
    ]
  })
}

# ========================================
# FONCTION LAMBDA
# ========================================

# Archive du code Lambda
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/cleanup"
  output_path = local.lambda_zip
  excludes    = ["__pycache__", "*.pyc", ".venv"]
}

resource "aws_lambda_function" "cleanup" {
  filename         = local.lambda_zip
  function_name    = local.lambda_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 300 # 5 minutes
  memory_size      = 256

  environment {
    variables = {
      GRACE_PERIOD_HOURS = var.grace_period_hours
      DRY_RUN            = var.dry_run ? "true" : "false"
      SNS_TOPIC_ARN      = aws_sns_topic.cleanup_notifications.arn
    }
  }

  tags = {
    Name        = local.lambda_name
    ManagedBy   = "Terraform"
    Environment = var.environment
    Owner       = "CloudGovernance"
    Squad       = "Platform"
    CostCenter  = "INFRA"
  }
}

# ========================================
# CLOUDWATCH LOGS
# ========================================

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${local.lambda_name}-logs"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

# ========================================
# PLANIFICATION EVENTBRIDGE (CRON)
# ========================================

resource "aws_cloudwatch_event_rule" "cleanup_schedule" {
  count = var.enable_schedule ? 1 : 0

  name                = "${local.lambda_name}-schedule"
  description         = "Déclenche le cleanup automatique selon le cron"
  schedule_expression = var.schedule_expression

  tags = {
    Name        = "${local.lambda_name}-schedule"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  count = var.enable_schedule ? 1 : 0

  rule      = aws_cloudwatch_event_rule.cleanup_schedule[0].name
  target_id = "lambda"
  arn       = aws_lambda_function.cleanup.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.enable_schedule ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cleanup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cleanup_schedule[0].arn
}
