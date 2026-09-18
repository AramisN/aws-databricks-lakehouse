# CI, settings outside git

Everything here lives in GitHub's settings, not in a file. Checked against the
real repo on 2026-09-18, not written from memory.

| Setting | Value | Where |
|---|---|---|
| CI OIDC role | `CI_ROLE_ARN` repo variable, `arn:aws:iam::537408064652:role/adl-dev-gha-terraform-plan` | Settings → Secrets and variables → Actions → Variables |
| Shared KMS key | `KMS_KEY_ARN` repo variable, `arn:aws:kms:eu-central-1:537408064652:key/3f1c52b1-f091-4ead-b64d-6b93551ab9e8` | Same place |
| `master` protection | Ruleset `protect-master`. Blocks deletion and force-push, requires a pull request, requires the `terraform` status check | Settings → Rules → Rulesets |
| Apply approval | `aws` Environment, required reviewer `AramisN`, restricted to `master`. Gates `terraform-apply.yml`'s apply job (ADR-0013) | Settings → Environments |
| GitHub secret scanning | Off, both scanning and push protection | Settings → Code security |
| gitleaks | Runs through `.pre-commit-config.yaml`, locally and in the `pre-commit` CI job. Separate from GitHub's own scanning above (ADR-0005) | `.pre-commit-config.yaml` |

## Worth knowing

Only `terraform` is a required status check on `master`. `python`, `CodeQL`,
and `pre-commit` all run on every PR, but none of them block a merge if they
fail. Every merge this project has done waited for all four anyway, that's a
habit, not something the ruleset enforces.

`required_approving_review_count` on the ruleset is 0. A pull request is
required, an actual approval on it is not.
