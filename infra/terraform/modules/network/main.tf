# Availability zones available in the target region, used to spread
# private subnets across az_count zones.
data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "region-name"
    values = [var.region]
  }
}

# The VPC. DNS support/hostnames on so private endpoints and internal
# service discovery resolve correctly.
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name      = "${var.name_prefix}-vpc"
    component = "network"
  }
}

# One private subnet per AZ, carved as /24s out of the VPC CIDR.
resource "aws_subnet" "private" {
  count             = var.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name      = "${var.name_prefix}-private-${data.aws_availability_zones.available.names[count.index]}"
    component = "network"
  }
}

# Shared route table for every private subnet. No default route out,
# since there's no NAT gateway or internet gateway in this layer yet.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name      = "${var.name_prefix}-private-rt"
    component = "network"
  }
}

resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# S3 gateway endpoint so private subnets can reach S3 (the lake buckets)
# without a NAT gateway or any internet route.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name      = "${var.name_prefix}-s3-endpoint"
    component = "network"
  }
}
