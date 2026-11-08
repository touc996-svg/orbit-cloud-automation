output "bucket_name" {
  description = "S3 artifacts bucket name."
  value       = aws_s3_bucket.this.bucket
}

output "bucket_arn" {
  description = "S3 artifacts bucket ARN."
  value       = aws_s3_bucket.this.arn
}
