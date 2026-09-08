# Account id used to make bucket names globally unique, matching the
# convention bootstrap uses for the state bucket.
data "aws_caller_identity" "current" {}

# The VPC and private subnets this environment runs in.
module "network" {
  source = "../modules/network"

  name_prefix = "adl-dev"
  region      = "eu-central-1"
  kms_key_arn = var.kms_key_arn
}

# Every other bucket sends S3 access logs here. Not given a
# logging_target_bucket itself, since a log bucket logging to itself
# would loop.
module "access_logs_bucket" {
  source = "../modules/lake_bucket"

  bucket_name = "adl-dev-access-logs-${data.aws_caller_identity.current.account_id}"
  kms_key_arn = var.kms_key_arn
  component   = "access-logs"
  expire_days = 30

  extra_policy_statements = [
    {
      Sid       = "AllowS3LoggingServicePrincipal"
      Effect    = "Allow"
      Principal = { Service = "logging.s3.amazonaws.com" }
      Action    = "s3:PutObject"
      Resource  = "arn:aws:s3:::adl-dev-access-logs-${data.aws_caller_identity.current.account_id}/*"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }
  ]
}

# The four medallion-layer buckets. Raw gets a short retention window
# per the data contract's erasure requirements; the rest keep
# everything. All four send access logs to the bucket above.
module "raw_bucket" {
  source = "../modules/lake_bucket"

  bucket_name           = "adl-dev-raw-${data.aws_caller_identity.current.account_id}"
  kms_key_arn           = var.kms_key_arn
  component             = "raw"
  expire_days           = 7
  logging_target_bucket = module.access_logs_bucket.bucket_name
}

module "bronze_bucket" {
  source = "../modules/lake_bucket"

  bucket_name           = "adl-dev-bronze-${data.aws_caller_identity.current.account_id}"
  kms_key_arn           = var.kms_key_arn
  component             = "bronze"
  logging_target_bucket = module.access_logs_bucket.bucket_name
}

module "silver_bucket" {
  source = "../modules/lake_bucket"

  bucket_name           = "adl-dev-silver-${data.aws_caller_identity.current.account_id}"
  kms_key_arn           = var.kms_key_arn
  component             = "silver"
  logging_target_bucket = module.access_logs_bucket.bucket_name
}

module "gold_bucket" {
  source = "../modules/lake_bucket"

  bucket_name           = "adl-dev-gold-${data.aws_caller_identity.current.account_id}"
  kms_key_arn           = var.kms_key_arn
  component             = "gold"
  logging_target_bucket = module.access_logs_bucket.bucket_name
}
