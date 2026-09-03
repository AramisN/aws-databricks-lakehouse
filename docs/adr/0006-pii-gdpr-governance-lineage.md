# ADR-0006: PII, GDPR, governance, and lineage

Status: Proposed
Date: 2026-09-01

## What I'm deciding

How personal data gets classified, protected, traced, and deleted across the three sources. The field-level map lives in the data contract. This ADR decides the machinery around it.

## The call

Unity Catalog is the one place classification, access, masking, and lineage are controlled. Raw personal data sits in a restricted area that almost no one can read. Everything downstream sees it masked, hashed, or generalized. To erase someone, I delete the record and destroy the token mapping that ties it back to them, then prove it's gone across every layer.

## Where governance runs

Unity Catalog sits over every table, so classification and access and lineage come from one place instead of being wired up tool by tool. Columns carry tags from the PII map in the data contract, and those tags drive the masking rules. Access is role based, and one restricted role can read raw personal data. That role is there mainly for erasure and audits. Every other role sees the masked and generalized views, so day to day analytics never touches a raw identifier.

## How each kind of field is handled

- mask, a Unity Catalog column mask hides the value and shows it only to the restricted role.
- generalize, a birthdate becomes an age band and an address becomes a zone, done in the transform into bronze.
- hash, join-key identifiers get a deterministic hash so joins still work and the raw value can't be read back.
- token, the raw value moves to a restricted vault and the table keeps only a token.
- drop, the field never leaves the raw layer.

## The hard part, erasure on a lakehouse

This is the part worth getting right, because a data lake fights deletion. A Delta DELETE only removes the record logically. Time travel still holds the old versions until VACUUM clears them past the retention window. So erasure isn't finished at the DELETE, it's finished once the history is vacuumed. That's why retention on personal data has to be short enough to hit the deletion deadline.

The lever I lean on is the token vault. Identifiers are tokenized, so destroying a person's mapping makes every token that points at them meaningless. That holds even in copies I can't easily reach. The DELETE and VACUUM then clean the tables themselves. A reconciliation check confirms the person is gone from raw, bronze, silver, and gold before the request is closed.

The streaming path works the same way. GPS points in the event stream are tokenized at the raw boundary and generalized to a zone downstream, so a trip can be erased without digging through raw pings.

## Encryption and secrets

Data is encrypted at rest with KMS and in transit with TLS. Credentials live in Secrets Manager, never in code or config. That matches the OIDC rule from ADR-0005, no long-lived keys lying around.

## Lineage

Unity Catalog records table and column lineage for anything that runs through it, so I can show where a field came from and where it went. dbt adds its own model graph and docs on top. Together they answer the question governance reviews always ask, prove where this number came from.

## What I'm giving up

Tokenization and masking add steps to every model and a vault to maintain, so there's real work here that a project without privacy rules would skip. Short retention on raw personal data means I can't keep a long raw history for reprocessing. Both are what doing GDPR properly costs, and that's the point.

## What would flip this

- A native AWS build with no Databricks. Then Lake Formation carries tag-based access and masking, and lineage comes from Glue plus something like OpenLineage.
- A rule that personal data can't land unencrypted even in the restricted zone. Then tokenize at ingestion, before anything gets written.
- Real subjects and a real regulator. Then the erasure deadline and audit logging get much stricter, and this ADR gets revisited hard.
