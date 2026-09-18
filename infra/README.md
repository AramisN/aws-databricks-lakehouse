# Infra

How to bring this environment's Terraform up and down.

## Layers

Two layers, applied in order, plus one optional third that sits beside them.

1. **`terraform/bootstrap`** runs once, by hand, on your machine. It makes the state bucket, its KMS key, and the GitHub OIDC role that CI logs in as. Its own state stays local and out of git (see ADR-0007). Bootstrap can't keep its state in the bucket, because bootstrap is the thing that makes that bucket in the first place.
2. **`terraform/foundation`** is the VPC and the five lake buckets (raw, bronze, silver, gold, access-logs). Its state lives in the S3 backend that bootstrap made. Shared pieces live in `terraform/modules/`, each with its own README.
3. **`terraform/streaming`** is the Kinesis stream, the Firehose delivery stream that lands it in the raw bucket, and the two IAM roles that scope who can write to the stream and who can read it (ADR-0009). It's its own stack, not part of foundation, on purpose. `terraform destroy` here kills the stream and stops the shard billing without touching the VPC or any bucket. It reads the raw bucket's name and the shared KMS key ARN out of foundation's state through a `terraform_remote_state` data source, rather than taking either as a variable.

## Bringing a layer up

```bash
cd infra/terraform/<layer>
terraform init -backend-config="bucket=<bootstrap's state_bucket_name output>" \
               -backend-config="kms_key_id=<bootstrap's kms_key_arn output>"
terraform plan   # foundation needs: -var "kms_key_arn=<bootstrap's kms_key_arn output>"
                 # streaming needs:  -var "tfstate_bucket_name=<bootstrap's state_bucket_name output>"
                 #                   -var "tfstate_kms_key_arn=<bootstrap's kms_key_arn output>"
terraform apply  # same -var flags as the plan above
```

`bucket` and `kms_key_id` aren't in the backend blocks, both would put the account id in a public repo. `terraform init` takes them as flags instead. Bootstrap's outputs (`terraform output`) feed all of these. Streaming doesn't take `kms_key_arn`, it reads foundation's state for that; it does need the two `tfstate_*` variables to reach that state in the first place, since foundation's own bucket and key aren't in `streaming/main.tf` either. Same lightweight coupling foundation itself has with bootstrap (ADR-0007).

## Bringing a layer down

```bash
cd infra/terraform/<layer>
terraform destroy
```

Tear `foundation` down before `bootstrap`, the reverse of the order you brought them up. Bootstrap holds the state bucket that foundation's own state lives in, so it has to go last. `streaming` is the exception, tear it down whenever, independent of the other two. That independence is the entire reason it's a separate stack.

## CI

`.github/workflows/terraform.yml` runs `fmt`, `init`, `validate`, a checkov scan (`.checkov.yaml` and `.checkov.baseline` at the repo root), and `plan` on every pull request against `foundation`. It logs in through the bootstrap OIDC role, so there are no long lived AWS keys.

`.github/workflows/terraform-apply.yml` applies `foundation` or `streaming`, triggered by hand from the Actions tab, never automatically. It plans, posts the plan, then waits for approval on the `aws` GitHub Environment before applying that exact plan. Nothing applies unless someone starts the workflow and approves it (ADR-0013).

The role ARN, the KMS key, the environment's approval rule, and everything else that lives in GitHub settings rather than a file are in [docs/ci.md](../docs/ci.md).

## Naming and tags

See [docs/conventions.md](../docs/conventions.md).
