# Infra

How to bring this environment's Terraform up and down.

## Layers

Two layers, applied in order.

1. **`terraform/bootstrap`** : run once, by hand, on your machine. It makes the state bucket, its KMS key, and the GitHub OIDC role that CI logs in as. Its own state stays local and out of git (see ADR-0007). Bootstrap can't keep its state in the bucket, because bootstrap is the thing that makes that bucket in the first place.
2. **`terraform/foundation`** : the VPC and the five lake buckets (raw, bronze, silver, gold, access-logs). Its state lives in the S3 backend that bootstrap made. Shared pieces live in `terraform/modules/`, each with its own README.

## Bringing a layer up

```bash
cd infra/terraform/<layer>
terraform init
terraform plan   # foundation needs: -var "kms_key_arn=<bootstrap's kms_key_arn output>"
terraform apply  # same -var as above, for foundation
```

Bootstrap's outputs (`terraform output`) feed foundation's `kms_key_arn` variable. Foundation is tied to bootstrap only through that one value, nothing more (ADR-0007).

## Bringing a layer down

```bash
cd infra/terraform/<layer>
terraform destroy
```

Tear `foundation` down before `bootstrap`, the reverse of the order you brought them up. Bootstrap holds the state bucket that foundation's own state lives in, so it has to go last.

## CI

`.github/workflows/terraform.yml` runs `fmt`, `init`, `validate`, a checkov scan (`.checkov.yaml` and `.checkov.baseline` at the repo root), and `plan` on every pull request against `foundation`. It logs in through the bootstrap OIDC role, so there are no long lived AWS keys. CI never applies. That stays a deliberate local step (ADR-0005).

## Naming and tags

See [docs/conventions.md](../docs/conventions.md).
