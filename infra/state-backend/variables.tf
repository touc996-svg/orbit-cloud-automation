variable "aws_region" {
  description = "AWS region for the Terraform state backend."
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for Terraform state."
  type        = string

  validation {
    condition = (
      length(var.bucket_name) >= 3 &&
      length(var.bucket_name) <= 63 &&
      can(regex("^[a-z0-9][a-z0-9.-]*[a-z0-9]$", var.bucket_name))
    )
    error_message = "bucket_name must be a valid lowercase S3 bucket name."
  }
}

variable "lock_table_name" {
  description = "DynamoDB table used for Terraform state locking."
  type        = string
  default     = "orbit-terraform-locks"
}
