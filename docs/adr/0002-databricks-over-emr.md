# ADR-0002: Databricks over EMR for compute

Status: Proposed
Date: 2026-09-01

## What I'm deciding

What runs the transformation and processing work in the lakehouse. The real contest is Databricks against EMR, the two Spark-scale platforms that could own this layer.

## The call

Databricks is the compute and governance layer. EMR is recorded here as the alternative I weighed and turned down.

## Why

Governance settles it. Two of my pillars are GDPR and governance. Unity Catalog gives lineage, PII tagging, column masking, and access control as built-in features. On EMR I'd rebuild all of that from Lake Formation and Glue and custom code, which is plumbing that hides the data engineering. Delta Lake covers the data-quality pillar in the same move, since it brings ACID writes and schema enforcement to files that would otherwise sit as loose parquet.

The one thing that favors EMR is raw compute cost. No DBU markup, closer to the metal. At portfolio scale that markup is a few euros a session, so it doesn't outweigh the governance win. Databricks also matches where I'm putting my learning time, and the demand for it means the work compounds into something hireable.

Compute runs on EC2 in my own account and storage stays on S3, so this sits on top of AWS rather than replacing it.

## The counterargument

The case against Databricks is that it's the easy button, and that EMR would show more skill because I'd manage more of it myself. The governance requirement overrides that. Unity Catalog delivers the PII and lineage controls as defaults. Hand-building them on EMR is busywork, not a signal. I take the DBU markup on purpose, and I'd switch to EMR the moment compute cost at scale became the real constraint.

## What I'm avoiding

- Reaching for Databricks on a small SQL-only job that cheaper tools would handle.
- Leaving clusters running with no auto-termination, the usual way a personal account racks up a bill.
- Treating notebooks as production with no jobs or CI behind them.
- Skipping Unity Catalog for the old hive metastore, which throws away the main reason to be on the platform.

## What I'm giving up

The DBU markup over raw EMR Spark. A third-party control plane inside the trust boundary, which some regulated shops won't allow. Some lock-in to Delta and Unity Catalog. All fine at this scale, set against the governance payoff.

## What would flip this

- Compute cost at large scale becomes the dominant constraint. EMR's no-markup Spark wins.
- An employer bans third-party control planes. Move to EMR or a fully native AWS build.
- A team with deep EMR and Spark tooling is already in place. The ops-burden argument weakens.

## Not decided here

The serving-layer query engine and any event-driven glue like Lambda are their own decisions, in later ADRs.
