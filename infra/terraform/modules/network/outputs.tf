output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.this.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets, one per AZ."
  value       = aws_subnet.private[*].id
}

output "private_route_table_id" {
  description = "ID of the route table associated with the private subnets."
  value       = aws_route_table.private.id
}
