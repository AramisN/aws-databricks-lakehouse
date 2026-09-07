# ARN of the KMS key bootstrap created, used to encrypt the lake
# buckets. Passed in rather than looked up by alias, so foundation
# doesn't depend on bootstrap's internals (ADR-0007).
variable "kms_key_arn" {
  description = "ARN of the shared KMS key (from bootstrap) used to encrypt the lake buckets."
  type        = string
}
