# ========================================
# MODULE LAMBDA DE COLLECTE DE METRIQUES
# Publie des metriques CloudWatch custom
# pour alimenter le dashboard Grafana
# ========================================

locals {
  lambda_name = "${var.environment}-tag-metrics"
  lambda_zip  = "${path.module}/lambda_function.zip"
}

# ========================================
# ROLE IAM POUR LA LAMBDA
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
    Owner       = "CloudGovernance"
    Squad       = "Platform"
    CostCenter  = "INFRA"
  }
}

# Politique pour les logs CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Politique personnalisee : lecture des ressources + publication metriques + Cost Explorer
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.lambda_name}-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # Lecture EC2
          "ec2:DescribeInstances",
          "ec2:DescribeTags",
          # Lecture RDS
          "rds:DescribeDBInstances",
          "rds:ListTagsForResource",
          # Lecture S3
          "s3:ListAllMyBuckets",
          "s3:GetBucketTagging",
          # Lecture Lambda
          "lambda:ListFunctions",
          "lambda:ListTags",
          # Tag API
          "tag:GetResources",
          "tag:GetTagKeys",
          "tag:GetTagValues",
          # Publication metriques CloudWatch
          "cloudwatch:PutMetricData",
          # Lecture Cost Explorer
          "ce:GetCostAndUsage",
          "ce:GetTags"
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
  source_dir  = "${path.module}/../../../lambda/metrics"
  output_path = local.lambda_zip
  excludes    = ["__pycache__", "*.pyc", ".venv"]
}

resource "aws_lambda_function" "metrics" {
  filename         = local.lambda_zip
  function_name    = local.lambda_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.12"
  architectures    = ["arm64"]
  timeout          = 120
  memory_size      = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
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
    Owner       = "CloudGovernance"
    Squad       = "Platform"
    CostCenter  = "INFRA"
  }
}

# ========================================
# PLANIFICATION EVENTBRIDGE
# ========================================

resource "aws_cloudwatch_event_rule" "metrics_schedule" {
  count = var.enable_schedule ? 1 : 0

  name                = "${local.lambda_name}-schedule"
  description         = "Collecte de metriques toutes les 6 heures"
  schedule_expression = var.schedule_expression

  tags = {
    Name        = "${local.lambda_name}-schedule"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  count = var.enable_schedule ? 1 : 0

  rule      = aws_cloudwatch_event_rule.metrics_schedule[0].name
  target_id = "lambda"
  arn       = aws_lambda_function.metrics.arn

  depends_on = [aws_lambda_permission.allow_eventbridge]
}

resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.enable_schedule ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.metrics.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.metrics_schedule[0].arn
}
