# ADR-0005: Source control and CI

Status: Proposed
Date: 2026-09-01

## What I'm deciding

Where the code lives and what has to pass before it merges, and how it reaches AWS.

## The call

GitHub for the repo, GitHub Actions for CI. Work happens on short-lived branches and merges to a protected main through a pull request. CI checks and plans on every pull request, but it never applies to AWS. Apply stays a deliberate local step, because the infrastructure is ephemeral and only comes up for a session.

## Why GitHub Actions over CodePipeline

Actions lives next to the code and it's free on a public repo. There's no pipeline to stand up and pay for either. The work CI does here is formatting, linting, validating, planning, and scanning. Nothing about that needs a separate pipeline product. CodePipeline and CodeBuild are the AWS-native option. They earn their place when the deployment is complex, spans several accounts, or a shop standardizes on AWS tooling. None of that is true here, so Actions is the pragmatic pick.

When CI does need to touch AWS, it goes through OIDC and assumes a short-lived role. No long-lived AWS key sits anywhere in GitHub. That's the security line I care about most on this.

## What runs on a pull request

- Formatting and lint (terraform fmt and ruff), enforced again on the server so the local pre-commit hooks aren't the only guard.
- terraform validate, then terraform plan posted to the pull request so the change is visible before merge.
- A security scan on the Terraform with tfsec or checkov, so misconfigurations get caught early.
- Secret scanning with gitleaks.
- Python unit tests once there's Python worth testing.
- dbt build and test later, when the dbt project exists. The data-quality ADR owns what those tests are, this ADR just runs them.

## Why plan in CI but not apply

Applying from CI would mean either a broad standing role in AWS or a pipeline that spins up billable infrastructure on its own. Both fight the cost and security rules of this project. So CI proves the change is valid and shows the plan, and I run the apply myself with make when I actually want the environment up. It stays honest about the ephemeral model instead of pretending this is an always-on production pipeline.

## Branching and merges

Main is protected and can't be pushed to directly. Work lands through pull requests off short-lived branches, squash-merged so the history stays one clean commit per change. Even solo, the pull request is worth it. It runs the gates, and it makes the history read like real work.

## The repo is private until it's ready

It stays private through the build, then goes public once it's something worth reading. Nothing about the setup changes when it flips. The CI and the gates are the same either way.

## What would flip this

- A team or a production target. Then the apply moves into CI, behind a least-privilege OIDC role and an approval gate.
- The org standardizes on AWS-native tooling. Move the pipeline to CodePipeline and CodeBuild.
- Self-hosted git or GitLab in play. Same gates, different CI syntax.
