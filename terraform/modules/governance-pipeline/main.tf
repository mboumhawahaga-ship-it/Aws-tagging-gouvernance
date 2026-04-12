locals {
  prefix = "${var.environment}-governance"

  common_tags = {
    ManagedBy   = "Terraform"
    Environment = var.environment
    Owner       = "CloudGovernance"
    Squad       = "Platform"
    CostCenter  = "INFRA"
  }
}

data "aws_caller_identity" "current" {}

# ========================================
# SECRETS MANAGER — Slack webhook
# ========================================

resource "aws_secretsmanager_secret" "slack_webhook" {
  count       = var.slack_webhook_url != "" ? 1 : 0
  name        = "${local.prefix}-slack-webhook"
  description = "Slack webhook URL pour les notifications de gouvernance"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret_version" "slack_webhook" {
  count     = var.slack_webhook_url != "" ? 1 : 0
  secret_id = aws_secretsmanager_secret.slack_webhook[0].id
  secret_string = jsonencode({
    webhook_url = var.slack_webhook_url
  })
}

# ========================================
# SNS TOPIC — notifications admin
# ========================================

resource "aws_sns_topic" "governance" {
  name              = "${local.prefix}-notifications"
  kms_master_key_id = "alias/aws/sns"
  tags              = local.common_tags
}

resource "aws_sns_topic_subscription" "admin_email" {
  topic_arn = aws_sns_topic.governance.arn
  protocol  = "email"
  endpoint  = var.admin_email
}

# ========================================
# CLOUDWATCH LOG GROUPS
# ========================================

resource "aws_cloudwatch_log_group" "scanner" {
  name              = "/aws/lambda/${local.prefix}-scanner"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "controller" {
  name              = "/aws/lambda/${local.prefix}-controller"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "executor" {
  name              = "/aws/lambda/${local.prefix}-executor"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

# ========================================
# IAM — SCANNER
# Lecture seule EC2/RDS/S3/Lambda + StartExecution Step Functions
# ========================================

resource "aws_iam_role" "scanner" {
  name = "${local.prefix}-scanner-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "scanner_logs" {
  role       = aws_iam_role.scanner.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "scanner" {
  name = "${local.prefix}-scanner-policy"
  role = aws_iam_role.scanner.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Lecture des ressources — AWS impose Resource = "*" sur les Describe/List
        Sid    = "ReadResources"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "rds:DescribeDBInstances",
          "rds:ListTagsForResource",
          "s3:ListAllMyBuckets",
          "s3:GetBucketTagging",
          "lambda:ListFunctions",
        ]
        Resource = "*"
      },
      {
        # ListTags Lambda — restreint aux fonctions du compte
        Sid      = "ReadLambdaTags"
        Effect   = "Allow"
        Action   = ["lambda:ListTags"]
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:*"
      },
      {
        # Lancer la Step Function — restreint à la state machine de gouvernance
        Sid      = "StartStateMachine"
        Effect   = "Allow"
        Action   = ["states:StartExecution"]
        Resource = aws_sfn_state_machine.governance.arn
      },
      {
        # X-Ray tracing
        Sid      = "XRayTracing"
        Effect   = "Allow"
        Action   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
        Resource = "*"
      }
    ]
  })
}

# ========================================
# IAM — CONTROLLER
# Lecture tags + publication SNS
# ========================================

resource "aws_iam_role" "controller" {
  name = "${local.prefix}-controller-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "controller_logs" {
  role       = aws_iam_role.controller.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "controller" {
  name = "${local.prefix}-controller-policy"
  role = aws_iam_role.controller.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Re-vérification des tags — AWS impose Resource = "*" sur Describe
        Sid    = "ReadTags"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "rds:ListTagsForResource",
          "s3:GetBucketTagging",
        ]
        Resource = "*"
      },
      {
        Sid      = "ReadLambdaTags"
        Effect   = "Allow"
        Action   = ["lambda:ListTags"]
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:*"
      },
      {
        # Notifications — restreint au topic de gouvernance uniquement
        Sid      = "PublishSNS"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.governance.arn
      },
      {
        # Slack webhook depuis Secrets Manager — restreint au secret de gouvernance
        Sid    = "ReadSlackSecret"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = var.slack_webhook_url != "" ? [
          aws_secretsmanager_secret.slack_webhook[0].arn
        ] : ["arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:none"]
      },
      {
        Sid      = "XRayTracing"
        Effect   = "Allow"
        Action   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
        Resource = "*"
      }
    ]
  })
}

# ========================================
# IAM — EXECUTOR
# Actions destructives — le plus restreint possible
# ========================================

resource "aws_iam_role" "executor" {
  name = "${local.prefix}-executor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "executor_logs" {
  role       = aws_iam_role.executor.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "executor" {
  name = "${local.prefix}-executor-policy"
  role = aws_iam_role.executor.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # EC2 — uniquement les instances taguées ManagedBy=Terraform
        Sid    = "EC2Actions"
        Effect = "Allow"
        Action = [
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:TerminateInstances",
        ]
        Resource = "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:instance/*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/ManagedBy" = "Terraform"
          }
        }
      },
      {
        # RDS — restreint au compte et à la région
        Sid    = "RDSActions"
        Effect = "Allow"
        Action = [
          "rds:StopDBInstance",
          "rds:StartDBInstance",
          "rds:DeleteDBInstance",
          "rds:CreateDBSnapshot",
        ]
        Resource = [
          "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:db:*",
          "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:snapshot:governance-*",
        ]
      },
      {
        # S3 — bloquer accès public + versioning uniquement (pas de delete)
        Sid    = "S3SafeActions"
        Effect = "Allow"
        Action = [
          "s3:PutBucketPublicAccessBlock",
          "s3:PutBucketVersioning",
        ]
        Resource = "arn:aws:s3:::*"
      },
      {
        # Lambda — freeze/resume/delete restreint au compte
        Sid    = "LambdaActions"
        Effect = "Allow"
        Action = [
          "lambda:PutFunctionConcurrency",
          "lambda:DeleteFunctionConcurrency",
          "lambda:DeleteFunction",
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:*"
      },
      {
        Sid      = "XRayTracing"
        Effect   = "Allow"
        Action   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
        Resource = "*"
      }
    ]
  })
}

# ========================================
# LAMBDA ZIPS
# ========================================

data "archive_file" "scanner" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/scanner"
  output_path = "${path.module}/scanner.zip"
  excludes    = ["__pycache__", "*.pyc"]
}

data "archive_file" "controller" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/controller"
  output_path = "${path.module}/controller.zip"
  excludes    = ["__pycache__", "*.pyc"]
}

data "archive_file" "executor" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/executor"
  output_path = "${path.module}/executor.zip"
  excludes    = ["__pycache__", "*.pyc"]
}

# ========================================
# LAMBDA FUNCTIONS
# ========================================

resource "aws_lambda_function" "scanner" {
  function_name    = "${local.prefix}-scanner"
  role             = aws_iam_role.scanner.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  timeout          = 300
  memory_size      = 256
  filename         = data.archive_file.scanner.output_path
  source_code_hash = data.archive_file.scanner.output_base64sha256

  environment {
    variables = {
      STATE_MACHINE_ARN       = aws_sfn_state_machine.governance.arn
      POWERTOOLS_SERVICE_NAME = "${local.prefix}-scanner"
      LOG_LEVEL               = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.scanner]
  tags       = local.common_tags
}

resource "aws_lambda_function" "controller" {
  function_name    = "${local.prefix}-controller"
  role             = aws_iam_role.controller.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  timeout          = 60
  memory_size      = 128
  filename         = data.archive_file.controller.output_path
  source_code_hash = data.archive_file.controller.output_base64sha256

  environment {
    variables = {
      SNS_TOPIC_ARN           = aws_sns_topic.governance.arn
      ADMIN_EMAIL             = var.admin_email
      SLACK_SECRET_NAME       = var.slack_webhook_url != "" ? aws_secretsmanager_secret.slack_webhook[0].name : ""
      POWERTOOLS_SERVICE_NAME = "${local.prefix}-controller"
      LOG_LEVEL               = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.controller]
  tags       = local.common_tags
}

resource "aws_lambda_function" "executor" {
  function_name    = "${local.prefix}-executor"
  role             = aws_iam_role.executor.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  timeout          = 120
  memory_size      = 128
  filename         = data.archive_file.executor.output_path
  source_code_hash = data.archive_file.executor.output_base64sha256

  environment {
    variables = {
      DRY_RUN                 = tostring(var.dry_run)
      POWERTOOLS_SERVICE_NAME = "${local.prefix}-executor"
      LOG_LEVEL               = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.executor]
  tags       = local.common_tags
}

# ========================================
# IAM — STEP FUNCTIONS
# Peut invoquer controller et executor uniquement
# ========================================

resource "aws_iam_role" "step_functions" {
  name = "${local.prefix}-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "step_functions" {
  name = "${local.prefix}-sfn-policy"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeLambdas"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          aws_lambda_function.controller.arn,
          aws_lambda_function.executor.arn,
        ]
      },
      {
        Sid      = "XRayTracing"
        Effect   = "Allow"
        Action   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
        ]
        Resource = "*"
      }
    ]
  })
}

# ========================================
# STEP FUNCTIONS STATE MACHINE
# ========================================

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/states/${local.prefix}"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_sfn_state_machine" "governance" {
  name     = "${local.prefix}-pipeline"
  role_arn = aws_iam_role.step_functions.arn

  definition = templatefile("${path.module}/../../../terraform/modules/step-function/state_machine.asl.json", {
    controller_lambda_arn = aws_lambda_function.controller.arn
    executor_lambda_arn   = aws_lambda_function.executor.arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = true
    level                  = "ERROR"
  }

  tracing_configuration {
    enabled = true
  }

  tags = local.common_tags
}

# ========================================
# EVENTBRIDGE — déclenche le scanner
# ========================================

resource "aws_cloudwatch_event_rule" "scanner_schedule" {
  name                = "${local.prefix}-scanner-schedule"
  description         = "Déclenche le scanner de gouvernance selon le cron"
  schedule_expression = var.scan_schedule
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "scanner" {
  rule      = aws_cloudwatch_event_rule.scanner_schedule.name
  target_id = "governance-scanner"
  arn       = aws_lambda_function.scanner.arn
}

resource "aws_lambda_permission" "eventbridge_scanner" {
  statement_id  = "AllowEventBridgeInvokeScanner"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scanner.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scanner_schedule.arn
}
