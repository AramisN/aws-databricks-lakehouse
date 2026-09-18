# Remote state for this layer, in the bucket bootstrap created. bucket
# and kms_key_id are deliberately left out, both contain the account id
# and this repo is public. Supply them at init time instead:
#   terraform init -backend-config="bucket=<bootstrap's state_bucket_name output>" \
#                   -backend-config="kms_key_id=<bootstrap's kms_key_arn output>"
terraform {
  backend "s3" {
    key          = "foundation/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
