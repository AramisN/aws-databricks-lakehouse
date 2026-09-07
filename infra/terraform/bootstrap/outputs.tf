# Referenced by foundation/backend.tf to point its remote state here.
output "state_bucket_name" {
  description = "Name of the S3 bucket holding Terraform state for every other layer."
  value       = aws_s3_bucket.tfstate.bucket
}

output "kms_key_arn" {
  description = "ARN of the KMS key used to encrypt Terraform state."
  value       = aws_kms_key.tfstate.arn
}

output "ci_role_arn" {
  description = "ARN of the IAM role GitHub Actions assumes to run terraform plan."
  value       = aws_iam_role.ci_terraform_plan.arn
}
