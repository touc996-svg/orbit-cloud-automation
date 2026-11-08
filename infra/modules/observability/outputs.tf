output "vpc_flow_logs_enabled" {
  description = "Whether VPC Flow Logs are enabled."
  value       = var.enable_vpc_flow_logs
}

output "vpc_flow_log_group_name" {
  description = "CloudWatch log group name when Flow Logs are enabled."
  value       = try(aws_cloudwatch_log_group.vpc_flow_logs[0].name, null)
}
