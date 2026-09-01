# AWS Databricks Lakehouse

A reference implementation for a lakehouse platform on AWS using Databricks — combining S3-based
storage, Unity Catalog governance, and Delta Lake table formats with Terraform-managed
infrastructure. This repo captures both the target architecture (design docs, ADRs) and the
infrastructure-as-code needed to stand it up.

## Status: designed vs built

| Component               | Designed | Built | Notes                                             |
|--------------------------|:--------:|:-----:|----------------------------------------------------|
| VPC / networking          |    ✅    |  ❌   | Reference architecture drafted, no Terraform yet    |
| S3 data lake (bronze/silver/gold) | ✅ | ❌ | Bucket layout and lifecycle policies designed        |
| Databricks workspace      |    ✅    |  ❌   | Deployment model chosen (E2, unified login)          |
| Unity Catalog governance  |    ✅    |  ❌   | Catalog/schema structure drafted                     |
| IAM roles & cross-account trust | ✅ |  ❌   | Role boundaries defined, not yet provisioned         |
| CI/CD for infra (Terraform) | ✅   |  ❌   | Pipeline design only                                  |
| dbt models                |    ❌    |  ❌   | Not yet started                                       |
| Monitoring & cost alerting |   ❌    |  ❌   | Not yet started                                       |

## Cost note

No infrastructure has been provisioned yet, so current spend is $0. Once built, expect the
primary cost drivers to be Databricks DBU consumption (compute) and S3 storage/egress; see
[docs/architecture/reference-architecture.md](docs/architecture/reference-architecture.md) for
sizing assumptions once they're filled in.
