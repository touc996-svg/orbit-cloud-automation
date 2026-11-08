variable "project_name" {
  description = "Project identifier used in resource names."
  type        = string
}

variable "vpc_id" {
  description = "VPC identifier receiving flow-log configuration."
  type        = string
}

variable "enable_vpc_flow_logs" {
  description = "Whether to create VPC Flow Logs and their CloudWatch destination."
  type        = bool
  default     = false
}

variable "flow_log_retention_days" {
  description = "CloudWatch Logs retention period."
  type        = number
  default     = 7
}
