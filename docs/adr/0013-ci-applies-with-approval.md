# ADR-0013: CI applies to AWS, manually triggered with approval

Status: Accepted
Date: 2026-09-18
Supersedes: part of ADR-0005, on CI applying to AWS

## What I'm deciding

Whether a Terraform apply against AWS can run from GitHub Actions, and under what control. ADR-0005 said no, apply stays a local step. This changes that.

## The call

A manual `workflow_dispatch` workflow, `terraform-apply.yml`, plans and applies `foundation` or `streaming` on request. The apply job runs under the `aws` GitHub Environment, which requires a reviewer to approve the run before it executes. Nothing applies unless I start the workflow and approve it.

## Why this doesn't break ADR-0005's reason

ADR-0005 kept apply local because the infrastructure is ephemeral and only comes up for a session. That property survives here completely. A manual trigger behind a required approval is exactly as deliberate as running `terraform apply` on my laptop, nothing happens on its own.

What changes is that the apply is now recorded. It's tied to a commit and to the exact plan that was reviewed in the workflow run, instead of happening locally with no trace of what was applied or why.

## What I'm giving up

A local apply never needs AWS credentials sitting in GitHub as a trust relationship at all. This does, through the same OIDC role CI already uses to plan. The blast radius of a compromised Actions run goes up, even behind the approval gate.

## What would flip this

- The approval step turns into a rubber stamp, clicked without reading the plan. Then this is worse than the local step it replaced, and applying goes back to ADR-0005's model.
- A second person joins the project. Then the recorded, reviewable apply is worth more, not less, and this becomes the only way anything gets applied.
