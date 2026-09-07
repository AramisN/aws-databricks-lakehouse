# ADR-0006: PII, GDPR, governance, and lineage

Status: Proposed
Date: 2026-09-01

## What I'm deciding

How personal data gets classified, protected, traced, and deleted across the three sources. The field-level map lives in the data contract. This ADR decides the machinery around it.

## The call

Unity Catalog is the one place classification, access, masking, and lineage are controlled. Direct identifiers live only in a restricted raw zone and never flow downstream. Analytics joins on surrogate keys like rider_id, which don't identify anyone on their own. To erase someone, I hard delete their rows and VACUUM the history past retention. Then a check proves they're gone across every layer.

## Where governance runs

Unity Catalog sits over every table, so classification and access and lineage come from one place instead of being wired up tool by tool. Columns carry tags from the PII map in the data contract, and those tags drive the masking rules. Access is role based, and one restricted role can read the raw identifiers. That role is there mainly for erasure and audits. Every other role sees the minimized views, so day to day analytics never touches a direct identifier.

## How each kind of field is handled

- restricted, direct identifiers like name and email and license number stay in the raw zone and never reach analytics.
- generalize, a birthdate becomes an age band and precise location becomes a zone in the transform into bronze.
- mask, when a direct identifier must sit in a table a Unity Catalog column mask hides it from every role but the restricted one.
- hash, a keyed hash for cases like the IP in the logs where I need to correlate but not keep the raw value.
- drop, the field never leaves raw at all.

## The hard part, erasure on a lakehouse

This is the part worth getting right, because a data lake fights deletion. A Delta DELETE only removes a record logically. Time travel still holds the old versions until VACUUM clears them past the retention window. So erasure isn't finished at the DELETE, it's finished once the history is vacuumed. That's why retention on personal data is kept short, short enough to hit the deletion deadline. Being able to do this at all is one reason I picked Delta, plain parquet on a lake can't.

I deliberately did not build a token vault or crypto-shredding. That technique is for data you can't reach to delete, like immutable backups or copies a third party holds. This project owns every copy and tears the whole thing down between sessions, so a hard delete reaches everything. Adding a vault would be one more load-bearing thing to secure and maintain, for compliance I already have without it. Knowing when not to reach for it matters as much as knowing it exists.

The streaming path works the same way. GPS pings land in restricted raw with short retention and get generalized to a zone downstream. A trip is erased by deleting its rows and vacuuming, nothing special.

## Encryption and secrets

Data is encrypted at rest with KMS and in transit with TLS. Credentials live in Secrets Manager, never in code or config. That matches the OIDC rule from ADR-0005, no long-lived keys lying around.

## Lineage

Unity Catalog records table and column lineage for anything that runs through it, so I can show where a field came from and where it went. dbt adds its own model graph and docs on top. Together they answer the question governance reviews always ask, prove where this number came from.

## What I'm giving up

Keeping direct identifiers out of analytics and running erasure across layers is real work a project without privacy rules would skip. Short retention on raw personal data means I can't hold a long raw history for reprocessing. Both are what doing GDPR properly costs, and that's the point.

## What would flip this

- Copies I can't reach enter the picture, immutable backups or data shared with a third party. Then crypto-shredding earns its place and I add per-subject keys.
- A native AWS build with no Databricks. Then Lake Formation carries tag-based access and masking, and lineage comes from Glue plus something like OpenLineage.
- Real subjects and a real regulator. Then the erasure deadline and audit logging get much stricter, and this ADR gets revisited hard.
