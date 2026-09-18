# Provisioned mode means the shard count is the throughput ceiling, on
# purpose (ADR-0009). Left as a variable rather than hardcoded, because
# going from 1 shard to 2 and watching the resharding is part of the
# exercise.
variable "shard_count" {
  description = "Number of shards on the trip_events stream."
  type        = number
  default     = 2
}

# Both needed to read foundation's remote state below, which is what
# this stack normally gets bucket/key names from. Can't get these two
# the same way, reading foundation's state is what needs them.
variable "tfstate_bucket_name" {
  description = "Name of the S3 bucket holding foundation's Terraform state (bootstrap's state_bucket_name output)."
  type        = string
}

variable "tfstate_kms_key_arn" {
  description = "ARN of the KMS key encrypting the Terraform state bucket (bootstrap's kms_key_arn output)."
  type        = string
}
