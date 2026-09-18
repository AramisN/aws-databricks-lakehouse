# CI, settings outside git

Everything here lives in GitHub's settings, not in a file. Checked against the
real repo on 2026-09-18, not written from memory.

| Setting | Value | Where |
|---|---|---|
| CI OIDC role | `CI_ROLE_ARN` repo variable, an IAM role ARN from `terraform/bootstrap`'s `ci_role_arn` output | Settings → Secrets and variables → Actions → Variables |
| Shared KMS key | `KMS_KEY_ARN` repo variable, the ARN from bootstrap's `kms_key_arn` output | Same place |
| Terraform state bucket | `TFSTATE_BUCKET` repo variable, the name from bootstrap's `state_bucket_name` output | Settings → Secrets and variables → Actions → Variables |
| `master` protection | Ruleset `protect-master`. Blocks deletion and force-push, requires a pull request, requires the `terraform` status check | Settings → Rules → Rulesets |
| Apply approval | `aws` Environment, required reviewer `AramisN`, restricted to `master`. Gates `terraform-apply.yml`'s apply job (ADR-0013) | Settings → Environments |
| GitHub secret scanning | Off, both scanning and push protection | Settings → Code security |
| gitleaks | Runs through `.pre-commit-config.yaml`, locally and in the `pre-commit` CI job. Separate from GitHub's own scanning above (ADR-0005) | `.pre-commit-config.yaml` |

Values aren't shown here on purpose. The account id was in this table until 2026-09-18, a public repo is no place for it even though it isn't a credential. All three of these are repo variables, visible in Settings to anyone with repo access but not to the public, same as the ARNs above already were.

## Worth knowing

Only `terraform` is a required status check on `master`. `python`, `CodeQL`,
and `pre-commit` all run on every PR, but none of them block a merge if they
fail. Every merge this project has done waited for all four anyway, that's a
habit, not something the ruleset enforces.

`required_approving_review_count` on the ruleset is 0. A pull request is
required, an actual approval on it is not.
