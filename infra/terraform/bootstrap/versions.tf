# Pins the Terraform CLI and provider versions so plans are reproducible
# across machines and CI.
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # No backend block here on purpose: bootstrap creates the state bucket
  # itself, so it can't yet store its own state remotely. State for this
  # layer stays local and out of git (see infra/README.md).
}
