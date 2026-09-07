# ADR-0007: Terraform structure and state

Status: Proposed
Date: 2026-09-01

## What I'm deciding

How the Terraform code is split up and where the state file lives. Also how tags get added to every resource.

## The call

Two parts that share some modules, bootstrap and foundation. Bootstrap makes the things the rest need first, the state bucket, its KMS key, and the GitHub OIDC role. Foundation makes the network and the lake buckets, and it keeps its state in the bucket that bootstrap made. State lives in S3 with a built-in lock and KMS encryption. Every resource gets the same set of tags from the provider, so I don't have to add them by hand.

## Why split it, not one big file

One config for everything means a single mistake can break everything, and the plan gets slow. Keeping bootstrap apart from foundation keeps the rare, high-power stuff away from the network and storage work I touch often. Modules for the VPC and the bucket mean I don't copy the same safe setup again and again. This is the "pick shared parts with care" point from Fundamentals, done in a small way.

## Why the S3 lock, not DynamoDB

Terraform 1.10 put a lock file inside the S3 backend, so the old DynamoDB lock table is not needed now. That is one less thing to make, pay for, and tear down. The state bucket keeps old versions and is encrypted with KMS, so a bad change can be rolled back and the state is safe at rest.

## The chicken and egg, and how I deal with it

Bootstrap makes the bucket that the state lives in, so on the first run bootstrap can't keep its own state there yet. Its state stays on my machine and out of git, and bootstrap almost never changes after the first run. Foundation and every part after it use the S3 backend from the start. This is the normal way to solve the loop, and I write it down in the infra README so it is not a surprise.

## Tags

The AWS provider adds a default set of tags, so every resource carries project, env, owner, managed-by, and an ephemeral flag without me adding them each time. The ephemeral flag is what a teardown run looks for. The full naming and tag list is in docs/conventions.md.

## What I'm giving up

Two parts mean two applies and passing a few outputs from one to the other. That is a bit more work than one config, and it is worth it for the smaller risk. Bootstrap's state stays local, which means that one part is not remote. That is a known and fine part of this way of working.

## What would flip this

- The project grows past a few parts. Then a tool like Terragrunt is worth it to keep the backends and inputs neat.
- A team needs to see bootstrap's state too. Then move bootstrap into the S3 backend after the first run.
- A company rule says use DynamoDB locking or another backend. Then match it.
