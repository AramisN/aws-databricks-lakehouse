# Account id is used to make the state bucket name globally unique.
data "aws_caller_identity" "current" {}

# KMS key that encrypts the Terraform state bucket. Rotation on so the
# key material ages out automatically without a manual rewrap.
resource "aws_kms_key" "tfstate" {
  description         = "Encrypts Terraform remote state for aws-databricks-lakehouse."
  enable_key_rotation = true
}

# Friendly alias so the key can be referenced by name instead of ARN.
resource "aws_kms_alias" "tfstate" {
  name          = "alias/adl-dev-tfstate"
  target_key_id = aws_kms_key.tfstate.key_id
}

# The bucket that holds every layer's Terraform state after bootstrap.
resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.state_bucket_name}-${data.aws_caller_identity.current.account_id}"
}

# Versioning so a bad apply's state can be rolled back to a prior version.
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Every object encrypted at rest with the KMS key above, not SSE-S3.
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.tfstate.arn
    }
    bucket_key_enabled = true
  }
}

# Belt-and-braces: no public access is ever allowed on this bucket.
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Denies any request to the bucket that isn't over TLS.
resource "aws_s3_bucket_policy" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.tfstate.arn,
          "${aws_s3_bucket.tfstate.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Fetches GitHub's current TLS certificate so the OIDC provider's
# thumbprint is always correct instead of a value copied by hand.
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

# GitHub's OIDC identity provider. One per AWS account; lets GitHub
# Actions runners request short-lived credentials with no stored key.
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

# Trust policy: only workflow runs from this exact repo, on any ref, can
# assume the role, and only via the GitHub OIDC provider / sts audience.
data "aws_iam_policy_document" "ci_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]
    }
  }
}

# The role GitHub Actions assumes. Kept plan-only: read access to AWS
# plus read/write on just the state bucket/key so it can lock and read
# state, no write access to any other resource.
resource "aws_iam_role" "ci_terraform_plan" {
  name               = var.ci_role_name
  assume_role_policy = data.aws_iam_policy_document.ci_trust.json
}

# Broad read-only access so `terraform plan` can describe any resource
# type across the account. No mutating permissions of any kind.
resource "aws_iam_role_policy_attachment" "ci_read_only" {
  role       = aws_iam_role.ci_terraform_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# Plan still needs to read state and take/release the S3-native lock,
# which ReadOnlyAccess alone doesn't cover (lock uses conditional writes).
data "aws_iam_policy_document" "ci_state_access" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.tfstate.arn,
      "${aws_s3_bucket.tfstate.arn}/*",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.tfstate.arn]
  }
}

resource "aws_iam_role_policy" "ci_state_access" {
  name   = "state-bucket-access"
  role   = aws_iam_role.ci_terraform_plan.id
  policy = data.aws_iam_policy_document.ci_state_access.json
}
