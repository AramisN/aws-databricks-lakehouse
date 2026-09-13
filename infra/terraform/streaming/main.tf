# Account id, same convention as bootstrap and foundation.
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# Foundation's state, read-only. This is the actual coupling between the
# two stacks. Streaming pulls the raw bucket name and the shared KMS key
# ARN out of foundation's outputs instead of hardcoding one and prompting
# for the other, which is the reason foundation exposes them in the
# first place.
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket     = "adl-dev-tfstate-537408064652"
    key        = "foundation/terraform.tfstate"
    region     = "eu-central-1"
    kms_key_id = "arn:aws:kms:eu-central-1:537408064652:key/3f1c52b1-f091-4ead-b64d-6b93551ab9e8"
  }
}

locals {
  raw_bucket_name = data.terraform_remote_state.foundation.outputs.raw_bucket_name
  raw_bucket_arn  = "arn:aws:s3:::${local.raw_bucket_name}"
  raw_prefix      = "streaming/trip_events/"
  kms_key_arn     = data.terraform_remote_state.foundation.outputs.kms_key_arn
}

# This stream runs in provisioned mode instead of on-demand, so the
# shard count is a real ceiling instead of something AWS hides
# (ADR-0009). It's encrypted with the AWS-managed aws/kinesis key rather
# than a key of our own, since a customer-managed key buys nothing extra
# for what this stream needs to do and just adds a second key to manage.
resource "aws_kinesis_stream" "trip_events" {
  name             = "adl-dev-trip-events"
  shard_count      = var.shard_count
  retention_period = 24

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Name      = "adl-dev-trip-events"
    component = "streaming"
  }
}

# Trust policy for the producer role. Left open to any principal in this
# account rather than one named user, since who is actually allowed to
# assume it is an IAM grant made outside this repo. That grant is not
# something Terraform should hardcode to one person's login.
data "aws_iam_policy_document" "producer_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
}

# Scoped to exactly one thing, writing records to this one stream. The
# generator doesn't actually assume this role for the exercise, it runs
# under the same AWS profile as everything else. The role documents the
# production pattern instead, the tight version of "who can write here."
resource "aws_iam_role" "producer" {
  name               = "adl-dev-streaming-producer"
  assume_role_policy = data.aws_iam_policy_document.producer_trust.json

  tags = {
    Name      = "adl-dev-streaming-producer"
    component = "streaming"
  }
}

data "aws_iam_policy_document" "producer_permissions" {
  statement {
    effect    = "Allow"
    actions   = ["kinesis:PutRecord", "kinesis:PutRecords"]
    resources = [aws_kinesis_stream.trip_events.arn]
  }
}

resource "aws_iam_role_policy" "producer_permissions" {
  name   = "kinesis-put-records"
  role   = aws_iam_role.producer.id
  policy = data.aws_iam_policy_document.producer_permissions.json
}

# Standard service trust for Firehose, with the account-id condition so
# only a Firehose delivery stream running in this account can assume it;
# not one from somewhere else pointed at the same role name.
data "aws_iam_policy_document" "firehose_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "firehose" {
  name               = "adl-dev-streaming-firehose"
  assume_role_policy = data.aws_iam_policy_document.firehose_trust.json

  tags = {
    Name      = "adl-dev-streaming-firehose"
    component = "streaming"
  }
}

# Read access to the one stream, write access to the one bucket prefix,
# nothing wider. The bucket-level statement is only what Firehose needs
# to check the bucket exists and list it; the actual object writes are
# scoped down to the streaming/trip_events/ prefix in the statement below.
data "aws_iam_policy_document" "firehose_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:GetRecords",
      "kinesis:GetShardIterator",
      "kinesis:ListShards",
    ]
    resources = [aws_kinesis_stream.trip_events.arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:GetBucketLocation", "s3:ListBucket"]
    resources = [local.raw_bucket_arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetObject",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
    ]
    resources = ["${local.raw_bucket_arn}/${local.raw_prefix}*"]
  }

  # The raw bucket is encrypted with the lake's own KMS key (from
  # bootstrap), not the aws/kinesis one above, so writing an object there
  # needs its own grant.
  statement {
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [local.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "firehose_permissions" {
  name   = "kinesis-read-raw-write"
  role   = aws_iam_role.firehose.id
  policy = data.aws_iam_policy_document.firehose_permissions.json
}

# Reads the stream, lands the events as files under the raw bucket's
# streaming/trip_events/ prefix. Gzip keeps the landed files small; the
# default buffer (5 MiB or 300 seconds, whichever comes first) is left as
# is, since neither latency nor file count matters yet at this volume.
resource "aws_kinesis_firehose_delivery_stream" "trip_events_to_raw" {
  name        = "adl-dev-trip-events-to-raw"
  destination = "extended_s3"

  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.trip_events.arn
    role_arn           = aws_iam_role.firehose.arn
  }

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose.arn
    bucket_arn = local.raw_bucket_arn
    prefix     = local.raw_prefix

    compression_format = "GZIP"
  }

  tags = {
    Name      = "adl-dev-trip-events-to-raw"
    component = "streaming"
  }
}
