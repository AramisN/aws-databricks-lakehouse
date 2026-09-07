output "vpc_id" {
  description = "ID of the VPC created by the network module."
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets created by the network module."
  value       = module.network.private_subnet_ids
}
