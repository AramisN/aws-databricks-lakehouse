# AWS provider for the streaming layer. default_tags applies the
# standard tag set (docs/conventions.md); ephemeral = true, since this is
# the stack meant to come down between sessions and stop shard billing.
provider "aws" {
  region = "eu-central-1"

  default_tags {
    tags = {
      project    = "aws-databricks-lakehouse"
      env        = "dev"
      owner      = "aramisnsr"
      managed_by = "terraform"
      ephemeral  = "true"
    }
  }
}
