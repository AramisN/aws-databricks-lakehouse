# AWS provider for the bootstrap layer. default_tags applies the standard
# tag set (docs/conventions.md) to every resource this config creates.
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "aws-databricks-lakehouse"
      env        = "dev"
      owner      = var.owner
      managed_by = "terraform"
      ephemeral  = "false" # bootstrap resources are long-lived, teardown must skip them
    }
  }
}
