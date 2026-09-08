variable "bucket_name" {
  description = "Name of the S3 bucket."
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key used to encrypt objects in this bucket."
  type        = string
}

variable "component" {
  description = "Medallion layer this bucket holds, e.g. raw, bronze, silver, gold."
  type        = string
}

variable "expire_days" {
  description = "Days after which current and noncurrent object versions expire. 0 means no expiry."
  type        = number
  default     = 0
}

variable "logging_target_bucket" {
  description = "Name of the bucket to send S3 access logs to. Empty string disables logging."
  type        = string
  default     = ""
}

variable "extra_policy_statements" {
  description = "Additional bucket policy statements (as objects) merged into this bucket's policy, e.g. for the S3 logging service principal."
  type        = list(any)
  default     = []
}
