# AWS region every bootstrap resource is created in.
variable "region" {
  description = "AWS region for the bootstrap resources."
  type        = string
  default     = "eu-central-1"
}

# Recorded in the owner tag on every resource.
variable "owner" {
  description = "Owner tag applied to every resource, a name or handle."
  type        = string
  default     = "aramisnsr"
}

# GitHub repo allowed to assume the CI role via OIDC.
variable "github_repo" {
  description = "GitHub repository allowed to assume the CI role, in \"owner/repo\" form."
  type        = string
  default     = "AramisN/aws-databricks-lakehouse"
}

# Base name for the state bucket; the account id gets appended for
# global uniqueness, per docs/conventions.md.
variable "state_bucket_name" {
  description = "Base name for the Terraform state bucket, before the account id suffix."
  type        = string
  default     = "adl-dev-tfstate"
}

# Name for the IAM role GitHub Actions assumes.
variable "ci_role_name" {
  description = "Name of the IAM role GitHub Actions assumes to run terraform plan."
  type        = string
  default     = "adl-dev-gha-terraform-plan"
}
