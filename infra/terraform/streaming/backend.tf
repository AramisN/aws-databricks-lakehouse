# Remote state for this layer, in the bucket bootstrap created. Its own
# state key, separate from foundation's, so tearing this stack down to
# stop the shard billing never touches the VPC or the lake buckets.
# bucket and kms_key_id are left out, both contain the account id and
# this repo is public. Supply them at init time, same as foundation:
#   terraform init -backend-config="bucket=<bootstrap's state_bucket_name output>" \
#                   -backend-config="kms_key_id=<bootstrap's kms_key_arn output>"
terraform {
  backend "s3" {
    key          = "streaming/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
