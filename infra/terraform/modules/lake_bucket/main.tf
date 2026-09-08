# The bucket itself.
#checkov:skip=CKV_AWS_144: single region by design, see ADR-0003, replication not wanted
#checkov:skip=CKV2_AWS_62: no event consumer yet, will add when one exists
#checkov:skip=CKV_AWS_18: this IS the access-log target, cannot log to itself
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name

  tags = {
    Name      = var.bucket_name
    component = var.component
  }
}

# Versioning so objects can be recovered and lifecycle rules have
# noncurrent versions to act on.
resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Every object encrypted at rest with the shared lake KMS key.
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# No public access is ever allowed on a lake bucket.
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Denies any request that isn't over TLS, plus whatever extra
# statements the caller needs (e.g. the S3 logging service principal
# on the access-logs bucket).
resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid       = "DenyInsecureTransport"
          Effect    = "Deny"
          Principal = "*"
          Action    = "s3:*"
          Resource = [
            aws_s3_bucket.this.arn,
            "${aws_s3_bucket.this.arn}/*",
          ]
          Condition = {
            Bool = {
              "aws:SecureTransport" = "false"
            }
          }
        }
      ],
      var.extra_policy_statements
    )
  })
}

# Lifecycle rules for the bucket. Always present, even with nothing to
# expire, so incomplete multipart uploads get cleaned up; the expiry
# rule for raw's short retention window is added only when requested.
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  dynamic "rule" {
    for_each = var.expire_days > 0 ? [1] : []
    content {
      id     = "expire-after-${var.expire_days}-days"
      status = "Enabled"

      filter {}

      expiration {
        days = var.expire_days
      }

      noncurrent_version_expiration {
        noncurrent_days = var.expire_days
      }
    }
  }
}

# Access logging to a separate hardened bucket, when one is configured.
resource "aws_s3_bucket_logging" "this" {
  count  = var.logging_target_bucket != "" ? 1 : 0
  bucket = aws_s3_bucket.this.id

  target_bucket = var.logging_target_bucket
  target_prefix = "${var.component}/"
}
