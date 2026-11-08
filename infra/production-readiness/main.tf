locals {
  state_bucket_arn = "arn:${data.aws_partition.current.partition}:s3:::${var.state_bucket_name}"

  incident_event_rule_arns = [
    aws_cloudwatch_event_rule.root_activity.arn,
    aws_cloudwatch_event_rule.failed_console_login.arn,
    aws_cloudwatch_event_rule.aws_health.arn,
  ]
}

# ------------------------------------------------------------
# 1. GITHUB ACTIONS OIDC AND LEAST-PRIVILEGE IAM ROLES
# ------------------------------------------------------------

data "aws_iam_policy_document" "github_trust" {
  for_each = var.github_environments

  statement {
    sid     = "GitHubActionsFederatedTrust"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repository}:environment:${each.value}"
      ]
    }
  }
}

resource "aws_iam_role" "github_plan" {
  for_each = var.github_environments

  name                 = "${var.project_name}-${each.value}-github-plan"
  assume_role_policy   = data.aws_iam_policy_document.github_trust[each.value].json
  max_session_duration = 3600

  tags = {
    Purpose     = "GitHub Actions Terraform Read Only"
    Environment = each.value
  }
}

data "aws_iam_policy_document" "github_plan" {
  for_each = var.github_environments

  statement {
    sid    = "InfrastructureReadOnlyDiscovery"
    effect = "Allow"

    actions = [
      "ec2:Describe*",
      "logs:Describe*",
      "logs:Get*",
      "logs:List*",
      "cloudwatch:Describe*",
      "cloudwatch:Get*",
      "cloudwatch:List*",
      "iam:Get*",
      "iam:List*",
      "backup:Describe*",
      "backup:List*",
      "events:Describe*",
      "events:List*",
      "sns:Get*",
      "sns:List*"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "TerraformStateBucketMetadata"
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:GetBucketVersioning",
      "s3:ListBucket"
    ]

    resources = [local.state_bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["orbit/*"]
    }
  }

  statement {
    sid    = "TerraformStateObjectAccess"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:GetObjectVersion"
    ]

    resources = ["${local.state_bucket_arn}/orbit/*"]
  }

  statement {
    sid    = "TerraformStateLockAccess"
    effect = "Allow"

    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
      "dynamodb:UpdateItem"
    ]

    resources = [var.lock_table_arn]
  }
}

resource "aws_iam_role_policy" "github_plan" {
  for_each = var.github_environments

  name   = "${var.project_name}-${each.value}-terraform-read-only"
  role   = aws_iam_role.github_plan[each.value].id
  policy = data.aws_iam_policy_document.github_plan[each.value].json
}

# ------------------------------------------------------------
# 2. CENTRALIZED INCIDENT ALERTS
# ------------------------------------------------------------

resource "aws_sns_topic" "incident_alerts" {
  name = "${var.project_name}-incident-alerts"
}

resource "aws_sns_topic_subscription" "incident_email" {
  topic_arn = aws_sns_topic.incident_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_event_rule" "root_activity" {
  name        = "${var.project_name}-root-account-activity"
  description = "Detect management API calls made with root credentials."

  event_pattern = jsonencode({
    "detail-type" = ["AWS API Call via CloudTrail"]
    detail = {
      userIdentity = {
        type = ["Root"]
      }
    }
  })
}

resource "aws_cloudwatch_event_rule" "failed_console_login" {
  name        = "${var.project_name}-failed-console-login"
  description = "Detect failed AWS console authentication."

  event_pattern = jsonencode({
    source        = ["aws.signin"]
    "detail-type" = ["AWS Console Sign In via CloudTrail"]
    detail = {
      eventSource = ["signin.amazonaws.com"]
      eventName   = ["ConsoleLogin"]
      responseElements = {
        ConsoleLogin = ["Failure"]
      }
    }
  })
}

resource "aws_cloudwatch_event_rule" "aws_health" {
  name        = "${var.project_name}-aws-health-events"
  description = "Detect AWS Health service events."

  event_pattern = jsonencode({
    source        = ["aws.health"]
    "detail-type" = ["AWS Health Event"]
  })
}

resource "aws_cloudwatch_event_target" "root_activity" {
  rule      = aws_cloudwatch_event_rule.root_activity.name
  target_id = "IncidentSNS"
  arn       = aws_sns_topic.incident_alerts.arn
}

resource "aws_cloudwatch_event_target" "failed_console_login" {
  rule      = aws_cloudwatch_event_rule.failed_console_login.name
  target_id = "IncidentSNS"
  arn       = aws_sns_topic.incident_alerts.arn
}

resource "aws_cloudwatch_event_target" "aws_health" {
  rule      = aws_cloudwatch_event_rule.aws_health.name
  target_id = "IncidentSNS"
  arn       = aws_sns_topic.incident_alerts.arn
}

data "aws_iam_policy_document" "incident_topic" {
  statement {
    sid     = "AllowEventBridgePublish"
    effect  = "Allow"
    actions = ["sns:Publish"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    resources = [aws_sns_topic.incident_alerts.arn]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = local.incident_event_rule_arns
    }
  }

  statement {
    sid     = "AllowBudgetsPublish"
    effect  = "Allow"
    actions = ["sns:Publish"]

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    resources = [aws_sns_topic.incident_alerts.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_sns_topic_policy" "incident_alerts" {
  arn    = aws_sns_topic.incident_alerts.arn
  policy = data.aws_iam_policy_document.incident_topic.json
}

# ------------------------------------------------------------
# 3. DISASTER RECOVERY AND AWS BACKUP
# ------------------------------------------------------------

data "aws_iam_policy_document" "backup_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "${var.project_name}-aws-backup"
  assume_role_policy = data.aws_iam_policy_document.backup_assume_role.json
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "restore" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

resource "aws_backup_vault" "orbit" {
  name        = "${var.project_name}-production-backup-vault"
  kms_key_arn = var.backup_kms_key_arn != "" ? var.backup_kms_key_arn : null

  tags = {
    Purpose = "Disaster Recovery"
  }
}

resource "aws_backup_plan" "orbit" {
  name = "${var.project_name}-production-backup-plan"

  rule {
    rule_name         = "DailyBackup"
    target_vault_name = aws_backup_vault.orbit.name
    schedule          = "cron(0 5 * * ? *)"
    start_window      = 60
    completion_window = 180

    lifecycle {
      delete_after = var.daily_backup_retention_days
    }
  }

  rule {
    rule_name         = "WeeklyBackup"
    target_vault_name = aws_backup_vault.orbit.name
    schedule          = "cron(0 6 ? * SUN *)"
    start_window      = 60
    completion_window = 180

    lifecycle {
      delete_after = var.weekly_backup_retention_days
    }
  }

  tags = {
    Purpose = "Disaster Recovery"
  }
}

resource "aws_backup_selection" "daily_resources" {
  name         = "${var.project_name}-daily-backup-selection"
  plan_id      = aws_backup_plan.orbit.id
  iam_role_arn = aws_iam_role.backup.arn

  selection_tag {
    type  = "STRINGEQUALS"
    key   = "ORBITBackup"
    value = "daily"
  }

  depends_on = [
    aws_iam_role_policy_attachment.backup,
    aws_iam_role_policy_attachment.restore
  ]
}

# ------------------------------------------------------------
# 4. COST MONITORING AND CLOUDWATCH BILLING ALARM
# ------------------------------------------------------------

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly-cost-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
    subscriber_sns_topic_arns  = [aws_sns_topic.incident_alerts.arn]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
    subscriber_sns_topic_arns  = [aws_sns_topic.incident_alerts.arn]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

resource "aws_sns_topic" "billing_alerts" {
  provider = aws.billing
  name     = "${var.project_name}-billing-alerts"
}

resource "aws_sns_topic_subscription" "billing_email" {
  provider  = aws.billing
  topic_arn = aws_sns_topic.billing_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_policy_document" "billing_topic" {
  statement {
    sid     = "AllowCloudWatchBillingAlarm"
    effect  = "Allow"
    actions = ["sns:Publish"]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }

    resources = [aws_sns_topic.billing_alerts.arn]

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values = [
        "arn:${data.aws_partition.current.partition}:cloudwatch:us-east-1:${data.aws_caller_identity.current.account_id}:alarm:*"
      ]
    }
  }
}

resource "aws_sns_topic_policy" "billing_alerts" {
  provider = aws.billing
  arn      = aws_sns_topic.billing_alerts.arn
  policy   = data.aws_iam_policy_document.billing_topic.json
}

resource "aws_cloudwatch_metric_alarm" "estimated_charges" {
  provider = aws.billing

  alarm_name          = "${var.project_name}-estimated-monthly-charges"
  alarm_description   = "Estimated AWS charges have reached the configured budget threshold."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600
  statistic           = "Maximum"

  threshold = (
    var.monthly_budget_usd *
    var.billing_alarm_threshold_pct / 100
  )

  dimensions = {
    Currency = "USD"
  }

  alarm_actions = [
    aws_sns_topic.billing_alerts.arn
  ]

  treat_missing_data = "notBreaching"

  depends_on = [
    aws_sns_topic_policy.billing_alerts
  ]
}
