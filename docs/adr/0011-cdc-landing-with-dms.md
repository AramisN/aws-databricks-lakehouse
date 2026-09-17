# ADR-0011: Landing OLTP changes in the lake with DMS

Status: Proposed
Date: 2026-09-14

## What I'm deciding

How rows from the ride-hailing Postgres get into the lake once the network path
from ADR-0010 exists, what shape they land in, and the settings that decide
whether the raw zone ends up usable or a heap of tiny files.

## The call

One DMS replication task per source, running full load plus ongoing replication,
writing Parquet into the raw bucket. Each table lands under its own prefix, date
partitioned. Selection rules use wildcards over the schema rather than one rule
per table, so adding a table upstream doesn't mean editing the task.

On the Postgres side this needs logical replication, which the local compose
setup already turns on. DMS creates a replication slot and reads the write-ahead
log through it. Full load copies the existing rows. Then replication picks up
from the point the load started, so nothing is missed in between.

Every file carries an operation column saying whether the row was an insert, an
update or a delete, and a commit timestamp column. Full load rows carry the
operation column too, so full load output and change output have the same shape
and bronze can read both with one piece of code.

## File sizing

DMS closes a Parquet file when either a time limit or a size limit is hit,
whichever comes first. The defaults are 60 seconds and 32 MB. At low volume the
time limit always wins, so you get one small file per table per minute forever.
That's 1440 files a day per table doing nothing useful. That is the small-file
problem, and it is the thing that makes a lake slow to query and slow to merge
once there is real data in it.

So both get set on purpose rather than left alone. A longer interval means bigger
files and fewer of them, at the cost of the data being that much staler when it
lands. The right number depends on how fresh the tables need to be, and the scale
runs are what tell me where the line sits. I'd rather write down the tradeoff and
then measure it than guess once and move on.

Worth noting that AWS's own documentation is inconsistent here. The minimum file
size is described as being in kilobytes in one place and as defaulting to 32 MB
in another, which is the kind of thing that costs an afternoon if you take it at
face value. I set it and then check what actually lands in the bucket.

## Ordering and deduplication

DMS can preserve the order of transactions across tables by writing everything
into one sequence, which matters for a system rebuilding transactions exactly,
not for this one. Bronze merges one table at a time, and the order that matters
is the order of changes to a single row, which the log sequence number gives me
inside each table's files.

So the merge keys on the primary key and orders by the log sequence number, never
by a timestamp. Timestamps collide when two changes land in the same millisecond
and they can move backwards across a restart, the sequence number can't.

DMS does not promise exactly-once delivery, so duplicate rows can land. Making
the merge idempotent handles that, which it has to be anyway to survive a rerun.

## The replication slot risk

An open slot makes Postgres hold on to write-ahead log files until the consumer
has read past them. If the DMS task stops and the slot is left behind, Postgres
keeps everything and the disk fills up. At ten thousand rows nothing happens. At
the volumes the scale runs use, it fills a disk fast.

I'd rather hit this deliberately once, watch the disk climb, and write down what
it looked like. That beats meeting it for the first time on something that matters.

## Alternatives I turned down

**Kinesis as the DMS target instead of S3.** This was my first instinct and it's
wrong for a lake landing. A Kinesis target endpoint points at exactly one stream,
so every table shares one stream's throughput no matter how differently they
behave. Output is JSON only, so the raw zone loses Parquet and every read
afterwards costs more. DMS ignores transaction boundaries writing to a stream,
and Kinesis has no deduplication. So the consumer carries all of it. Batch apply
is not supported for stream targets either, so the mode meant to be faster is the
slower one. Kinesis earns its place when several independent consumers need the
change feed quickly, which is a fan-out problem I don't have. Phase 3 already
covers the streaming ground.

**CSV instead of Parquet.** Simpler to eyeball, worse in every other way. No
column pruning, no compression worth the name, no types.

**Change capture only, skipping the full load.** Then the lake has changes to
rows it has never seen, and bronze can't build a current picture without a
separate backfill. Full load plus changes is one task doing both.

**A nightly dump and reload instead of change capture.** This is what a lot of
places actually do and it would work at this size. It also throws away the
deletes, hides the intermediate states of a row, and doesn't teach me anything I
don't already know.

**Debezium and Kafka instead of DMS.** Debezium is the open-source change capture
platform most companies reach for outside AWS. It gives more control over the
change format and it's the tool I'd expect to meet in a job. It also means
running Kafka, or paying for a managed one, both a standing cost this project
can't carry. The AWS-native path is the one this repo is about instead.

## Cost

A dms.t3.micro replication instance runs somewhere near $0.02 an hour, so a
working session is small change. Storage for the scale runs is single-digit
gigabytes, a few cents a month, and deleted afterwards. Writing many small files
does cost per request, which is another reason the file sizing isn't only a
performance decision.

The instance is the thing that keeps charging if it's left up, so it lives in the
phase 4 stack with its own state and gets destroyed with everything else.

## What I'm giving up

Raw lands as plain Parquet, not Delta, so nothing in the raw zone can be updated
or deleted in place. That has consequences for erasure, which ADR-0012 deals
with.

There is no schema evolution handling here. A column added upstream will show up
in new files and bronze will have to cope. I'm leaving that for the phase where
bronze exists rather than pretending to solve it now.

One task, one source, one account. Nothing about this exercises the coordination
problems of many sources owned by different teams.

## What would flip this

- A real need for several consumers to see changes within seconds, which would
  make a stream target worth its downsides.
- Volumes past what one replication instance can keep up with, where serverless
  or a larger instance starts paying for itself.
- Databricks shipping ingestion that reads the source directly and makes the
  middle layer pointless. Worth checking before phase 5 rather than assuming.
