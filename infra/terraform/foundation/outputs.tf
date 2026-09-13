output "vpc_id" {
  description = "ID of the VPC created by the network module."
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets created by the network module."
  value       = module.network.private_subnet_ids
}

output "raw_bucket_name" {
  description = "Name of the raw layer S3 bucket."
  value       = module.raw_bucket.bucket_name
}

output "bronze_bucket_name" {
  description = "Name of the bronze layer S3 bucket."
  value       = module.bronze_bucket.bucket_name
}

output "silver_bucket_name" {
  description = "Name of the silver layer S3 bucket."
  value       = module.silver_bucket.bucket_name
}

output "gold_bucket_name" {
  description = "Name of the gold layer S3 bucket."
  value       = module.gold_bucket.bucket_name
}

output "access_logs_bucket_name" {
  description = "Name of the S3 access-logs bucket."
  value       = module.access_logs_bucket.bucket_name
}

# Passed straight through, not looked up. Foundation took this from
# bootstrap as a variable in the first place (ADR-0007), so re-exposing
# it here just gives streaming the same value through remote state
# instead of a second manual -var at plan time.
output "kms_key_arn" {
  description = "ARN of the shared KMS key (from bootstrap), passed through so other stacks can read it from this layer's state."
  value       = var.kms_key_arn
}
