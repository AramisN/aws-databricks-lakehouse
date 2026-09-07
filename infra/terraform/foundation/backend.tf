# Remote state for this layer, in the bucket bootstrap created.
terraform {
  backend "s3" {
    bucket       = "adl-dev-tfstate-537408064652"
    key          = "foundation/terraform.tfstate"
    region       = "eu-central-1"
    kms_key_id   = "arn:aws:kms:eu-central-1:537408064652:key/3f1c52b1-f091-4ead-b64d-6b93551ab9e8"
    encrypt      = true
    use_lockfile = true
  }
}
