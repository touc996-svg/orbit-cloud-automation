variable "aws_region" {
  description = "AWS region in which ORBIT will create resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short lowercase identifier used in resource names and tags."
  type        = string
  default     = "orbit"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,12}$", var.project_name))
    error_message = "project_name must be 2-13 characters, start with a lowercase letter, and contain only lowercase letters, numbers, or hyphens."
  }
}

variable "environment" {
  description = "Environment tag for resources."
  type        = string
  default     = "portfolio"

  validation {
    condition     = contains(["dev", "test", "portfolio", "staging", "prod"], var.environment)
    error_message = "environment must be dev, test, portfolio, staging, or prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the ORBIT VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Two public subnet CIDR blocks."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Two private subnet CIDR blocks."
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "enable_vpc_flow_logs" {
  description = "Create CloudWatch Logs VPC Flow Logs resources. Disabled by default to avoid ongoing log charges."
  type        = bool
  default     = false
}

variable "flow_log_retention_days" {
  description = "CloudWatch log retention period when VPC Flow Logs are enabled."
  type        = number
  default     = 7

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365], var.flow_log_retention_days)
    error_message = "Choose a supported CloudWatch Logs retention period."
  }
}
