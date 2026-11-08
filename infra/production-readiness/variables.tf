variable "project_name" {
  type    = string
  default = "orbit"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "alert_email" {
  description = "Email address receiving ORBIT incident and cost alerts."
  type        = string

  validation {
    condition     = can(regex("^[^ @]+@[^ @]+\\.[^ @]+$", var.alert_email))
    error_message = "Provide a valid alert email address."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly AWS cost budget in USD."
  type        = number
  default     = 25

  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "Monthly budget must be greater than zero."
  }
}

variable "billing_alarm_threshold_pct" {
  description = "Percentage of monthly budget that triggers the billing alarm."
  type        = number
  default     = 80

  validation {
    condition = (
      var.billing_alarm_threshold_pct > 0 &&
      var.billing_alarm_threshold_pct <= 100
    )
    error_message = "Billing alarm threshold must be between 1 and 100."
  }
}

variable "github_repository" {
  description = "GitHub organization/user and repository."
  type        = string
  default     = "touc996-svg/orbit-cloud-automation"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Use the owner/repository format."
  }
}

variable "github_oidc_provider_arn" {
  description = "ARN of the already-existing GitHub Actions OIDC provider."
  type        = string

  validation {
    condition = can(regex(
      "^arn:[a-z0-9-]+:iam::[0-9]{12}:oidc-provider/token\\.actions\\.githubusercontent\\.com$",
      var.github_oidc_provider_arn
    ))
    error_message = "Provide the ARN of token.actions.githubusercontent.com."
  }
}

variable "github_environments" {
  type    = set(string)
  default = ["development", "staging", "production"]

  validation {
    condition = (
      length(var.github_environments) > 0 &&
      alltrue([
        for environment in var.github_environments :
        contains(["development", "staging", "production"], environment)
      ])
    )
    error_message = "Only development, staging and production are supported."
  }
}

variable "state_bucket_name" {
  description = "Existing Terraform remote state bucket name."
  type        = string

  validation {
    condition = (
      length(var.state_bucket_name) >= 3 &&
      length(var.state_bucket_name) <= 63 &&
      can(regex("^[a-z0-9][a-z0-9.-]*[a-z0-9]$", var.state_bucket_name))
    )
    error_message = "Provide a valid lowercase S3 bucket name."
  }
}

variable "lock_table_arn" {
  description = "ARN of the existing Terraform DynamoDB lock table."
  type        = string
}

variable "backup_kms_key_arn" {
  description = "Optional customer-managed KMS key for AWS Backup."
  type        = string
  default     = ""
}

variable "daily_backup_retention_days" {
  type    = number
  default = 35

  validation {
    condition     = var.daily_backup_retention_days >= 1
    error_message = "Daily backup retention must be at least one day."
  }
}

variable "weekly_backup_retention_days" {
  type    = number
  default = 90

  validation {
    condition     = var.weekly_backup_retention_days >= 1
    error_message = "Weekly backup retention must be at least one day."
  }
}
