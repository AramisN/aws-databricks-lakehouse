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

# Locks down the VPC's default security group, which AWS creates
# wide-open by default and is easy to leave unused but reachable.
resource "aws_default_security_group" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name      = "${var.name_prefix}-default-sg"
    component = "network"
  }
}

# CloudWatch log group VPC flow logs are written to.
#checkov:skip=CKV_AWS_338: dev flow logs kept 14 days on purpose for cost, one-year retention not needed here
resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/aws/vpc-flow-logs/${var.name_prefix}"
  retention_in_days = 14
  kms_key_id        = var.kms_key_arn

  tags = {
    Name      = "${var.name_prefix}-flow-logs"
    component = "network"
  }
}

# Lets the VPC flow logs service assume a role to write into the log group.
data "aws_iam_policy_document" "flow_logs_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "flow_logs" {
  name               = "${var.name_prefix}-vpc-flow-logs"
  assume_role_policy = data.aws_iam_policy_document.flow_logs_trust.json

  tags = {
    Name      = "${var.name_prefix}-vpc-flow-logs"
    component = "network"
  }
}

data "aws_iam_policy_document" "flow_logs_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
    ]
    resources = ["${aws_cloudwatch_log_group.flow_logs.arn}:*"]
  }
}

resource "aws_iam_role_policy" "flow_logs" {
  name   = "vpc-flow-logs-write"
  role   = aws_iam_role.flow_logs.id
  policy = data.aws_iam_policy_document.flow_logs_permissions.json
}

# Flow logs for every ENI in the VPC, sent to the log group above.
resource "aws_flow_log" "this" {
  vpc_id               = aws_vpc.this.id
  traffic_type         = "ALL"
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.flow_logs.arn
  iam_role_arn         = aws_iam_role.flow_logs.arn

  tags = {
    Name      = "${var.name_prefix}-flow-log"
    component = "network"
  }
}
