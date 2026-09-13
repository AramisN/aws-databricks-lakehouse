# AWS Databricks Lakehouse

A reference build of a lakehouse platform on AWS with Databricks. It uses S3 for storage, Unity Catalog for governance, and Delta Lake for the table format, with all the infrastructure managed in Terraform. The repo holds two things. The target design lives in the docs and ADRs, and the infrastructure-as-code that stands it up sits alongside it.

It's built in phases, and each one stands on its own. See below if you only want to run just one of them.

## Phases

- **Phase 1, AWS infrastructure.** Terraform for the VPC, the S3 data lake, IAM and OIDC, and the CI/CD around it. Needs an AWS account. Covered in [infra](infra/README.md) and [docs/adr](docs/adr/README.md).
- **Phase 2, the data generator.** A seeded Python program that builds a synthetic ride-hailing dataset and either loads it into Postgres or writes it out as NDJSON. It runs entirely on its own with Docker and [uv](https://docs.astral.sh/uv/) and nothing else, no AWS account needed. Full detail in [generator/README.md](generator/README.md).

If you're here for Phase 2 only, this is the whole path, start to finish:

```bash
uv sync
cp .env.example .env
docker compose up -d                             # Docker Desktop needs to be running first
docker compose exec -T db psql -U postgres -d rideshare < sql/schema.sql   # user/db from .env
uv run rides-generate --zones-csv generator/tests/sample/zones.csv --target postgres
```

That's a seed in, an OLTP dataset out, and nothing from Phase 1 required. [generator/README.md](generator/README.md) covers what it produces, the flags, and the deliberate mess it adds on purpose. It also covers the two snags worth knowing about before you hit them yourself.

## Documentation

Architecture decisions live in [docs/adr](docs/adr/README.md); start there for the why behind
the choices below. For how to bring the infrastructure up and down, see [infra](infra/README.md).

## Status: designed vs built

| Component               | Designed | Built | Notes                                             |
|--------------------------|:--------:|:-----:|----------------------------------------------------|
| VPC / networking          |    ✅    |  ✅   | 2-AZ VPC, private subnets, S3 gateway endpoint, locked default SG, VPC flow logs to CloudWatch |
| S3 data lake (raw/bronze/silver/gold + access-logs) | ✅ | ✅ | 5 buckets applied: versioned, KMS-encrypted, TLS-only policy, lifecycle rules, access logging |
| Databricks workspace      |    ✅    |  ❌   | Deployment model chosen (E2, unified login)          |
| Unity Catalog governance  |    ✅    |  ❌   | Catalog/schema structure drafted                     |
| IAM roles & cross-account trust | ✅ |  ✅   | Bootstrap OIDC role + state-access policy provisioned; cross-account not in scope yet (single account, ADR-0003) |
| CI/CD for infra (Terraform) | ✅   |  ✅   | GitHub Actions: fmt, validate, checkov, plan on every PR via OIDC. Apply stays a deliberate local step (ADR-0005) |
| dbt models                |    ❌    |  ❌   | Not yet started                                       |
| Monitoring & cost alerting |   ❌    |  ❌   | Not yet started                                       |

## Cost note

Bootstrap and foundation are both applied. That is a VPC with no NAT gateway, 5 S3 buckets, a KMS key, and CloudWatch flow logs. At this scale the buckets are near empty and no compute is running, so the real spend is a small fraction of a euro a month. That's just the S3, KMS, and CloudWatch minimums, with no NAT or compute charges. The next real cost will be Databricks DBU usage once compute is set up. See [docs/architecture/reference-architecture.md](docs/architecture/reference-architecture.md) for the sizing assumptions once they are filled in.
