provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      ManagedBy   = "Terraform"
      Environment = "production-readiness"
    }
  }
}

provider "aws" {
  alias  = "billing"
  region = "us-east-1"
}

data "aws_partition" "current" {}

data "aws_caller_identity" "current" {}
