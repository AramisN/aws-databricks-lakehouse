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
