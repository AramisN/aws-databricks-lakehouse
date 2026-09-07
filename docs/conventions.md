# Conventions

Naming and tagging rules for the whole project. Plain on purpose, and it is what makes teardown and cost tracking work.

## Naming

Short prefix `adl` for aws-databricks-lakehouse. The pattern is `adl-<env>-<component>` with an optional `-<detail>`. Env is `dev` for now.

Examples: `adl-dev-vpc`, `adl-dev-raw`, `adl-dev-bronze`.

S3 bucket names have to be unique across all of AWS and all lowercase, so they get a suffix. Either the account id or a short random string, for example `adl-dev-raw-<account-id>`.

## Tags

Every resource carries these. The AWS provider adds them through default_tags, so no one has to remember:

- `project` = aws-databricks-lakehouse
- `env` = dev
- `owner` = the repo owner's handle
- `managed_by` = terraform
- `ephemeral` = true
- `component` = the part or service, like network, raw, bronze

`ephemeral = true` marks anything a teardown run is allowed to delete. Long-lived things like the state bucket get `ephemeral = false`, so a teardown never touches them.

## Parts

- `bootstrap`, run once, holds the state bucket, the KMS key, and the OIDC role. State stays local.
- `foundation`, the network and the lake buckets. State in S3.
- Compute and governance parts come later, each in its own phase.

## Environments

One environment, `dev`, for now. The naming leaves room for `stg` or `prod` later without renaming everything.
