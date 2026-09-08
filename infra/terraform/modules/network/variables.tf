variable "name_prefix" {
  description = "Prefix applied to every resource name in this module, e.g. \"adl-dev\"."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread private subnets across."
  type        = number
  default     = 2
}

variable "region" {
  description = "AWS region the VPC is created in."
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key used to encrypt the VPC flow logs CloudWatch log group."
  type        = string
}
