# AWS provider for the foundation layer. default_tags applies the
# standard tag set (docs/conventions.md); ephemeral = true here, unlike
# bootstrap, since this layer is torn down between sessions.
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
