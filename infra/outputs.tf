output "vpc_id" {
  description = "ID of the ORBIT VPC."
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets."
  value       = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets."
  value       = module.network.private_subnet_ids
}

output "s3_artifacts_bucket_name" {
  description = "Name of the private S3 artifacts bucket."
  value       = module.storage.bucket_name
}
