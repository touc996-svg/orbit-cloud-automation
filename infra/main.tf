locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
  artifacts_bucket   = "${var.project_name}-${data.aws_caller_identity.current.account_id}-${replace(var.aws_region, "-", "")}-artifacts"
}

module "network" {
  source = "./modules/network"

  project_name         = var.project_name
  vpc_cidr             = var.vpc_cidr
  availability_zones   = local.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

module "storage" {
  source = "./modules/storage"

  bucket_name  = local.artifacts_bucket
  project_name = var.project_name
}

module "observability" {
  source = "./modules/observability"

  project_name            = var.project_name
  vpc_id                  = module.network.vpc_id
  enable_vpc_flow_logs    = var.enable_vpc_flow_logs
  flow_log_retention_days = var.flow_log_retention_days
}
