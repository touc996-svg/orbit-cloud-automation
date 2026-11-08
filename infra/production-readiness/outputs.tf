output "github_plan_role_arns" {
  description = "Read-only GitHub Actions role ARN for each environment."
  value = {
    for environment, role in aws_iam_role.github_plan :
    environment => role.arn
  }
}

output "incident_alert_topic_arn" {
  value = aws_sns_topic.incident_alerts.arn
}

output "billing_alert_topic_arn" {
  value = aws_sns_topic.billing_alerts.arn
}

output "backup_vault_arn" {
  value = aws_backup_vault.orbit.arn
}

output "backup_plan_id" {
  value = aws_backup_plan.orbit.id
}

output "monthly_budget_name" {
  value = aws_budgets_budget.monthly.name
}
