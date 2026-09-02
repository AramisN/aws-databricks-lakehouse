# ADR-0001: AWS and Databricks lakehouse

**Status:** Proposed, waiting on my sign-off
**Date:** 2026-09-01

## What I'm deciding

This picks the cloud and the platform and the core tools. Everything else inherits from it, so it
comes first.

## The call

One cloud and one platform, built properly. AWS for everything, with Databricks as the lakehouse
layer on top. The storage pattern is a lakehouse, Delta tables on S3. Not a warehouse, and not a
bare data lake. Supporting tools are dbt and Airflow, plus Python and Terraform. GCP and Azure and
Snowflake are all out of scope here.

## Why AWS

The cert and the account are already here. The DEA is AWS-specific too, so the repo actually
backs up the credential. AWS also has the widest install base, which means the skills carry to the
most job listings. Every piece I need is native to AWS, from S3 storage to the VPC networking that
carries the hard part of the story.

## Why a lakehouse, not a warehouse or a plain lake

This is the choice most likely to get questioned, so here's the short version. A warehouse is
great at SQL and fights you on streaming and ML and open formats. A plain lake on S3 is cheap and
open but has no ACID guarantees, so quality and governance become my problem. Delta on S3 gives
one storage layer for SQL and streaming and ML, with transactions and schema enforcement built in.
That lines up with two of my pillars, data quality and governance. That's the real reason to pick
it.

## Why Databricks

Short version here, the full argument is ADR-0002. It's the lakehouse platform from the people who
built Spark, and it runs inside my AWS account rather than replacing it. Unity Catalog handles
governance and PII tagging natively, which EMR would make me build by hand.

## The tools

| Tool      | What I didn't pick   | Why                                                                                    |
|-----------|-----------------------|-----------------------------------------------------------------------------------------|
| dbt       | SQLMesh               | Biggest install base, runs against Databricks SQL, gives tests and docs and lineage in one place |
| Airflow   | Dagster, Prefect      | Most widely used orchestrator so the skill transfers, self-hosted to dodge the MWAA monthly floor |
| Python    | Scala, SQL only       | One language across Spark, dbt, the Airflow DAGs, the data generator, and the ML piece  |
| Terraform | OpenTofu, CDK         | What most companies actually run, and OpenTofu is close enough to switch to later if I need it |

## Cost discipline

This is a design constraint, not a footnote. Build it, prove it works, then tear it down. The
billing alarm is hard capped at 20 euros. Real teams work this way and most portfolios pretend cost
doesn't exist.

## What I'm giving up

Lock-in, to AWS and to Delta and Unity Catalog. And no multi-cloud range on show. Both are fine for
a first project. Depth beats breadth here, and a later project can add another cloud.

## What would flip this

- Target jobs are mostly Azure or GCP. Rebuild the same pattern there, the lakehouse idea travels.
- An employer bans third-party control planes. Go native AWS with Iceberg on EMR or Athena, drop
  Databricks.
- Pure SQL analytics, no streaming and no ML. Skip the platform, run Athena over a Glue catalog.
- Company standard is CDK or Pulumi. Match it, the reason for using IaC holds either way.
