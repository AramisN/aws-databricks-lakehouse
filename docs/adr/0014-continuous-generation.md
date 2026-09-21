# ADR-0014: The generator runs continuously and feeds both outputs

Status: Proposed
Date: 2026-09-18
Supersedes: part of ADR-0008, on the generator being a single run over a fixed
dataset

## What I'm deciding

How the source keeps producing data after the first load, and which program
writes the events.

## The call

Two modes in one program.

`seed` keeps what ADR-0008 built. Truncate, generate from a seed, load, exit.
Same data for the same seed.

`run` is new and does not truncate. It creates trips at a set rate and walks
each one through its states, updating rows as it goes. At the same time it
deletes a small share of trips and emits their GPS events to Kinesis, running
until someone stops it.

Both modes generate in batches. Memory is bounded by the batch size, not by how
many rows the run produces.

## One program, both outputs

Today the Kinesis producer invents its own trips and the loader invents its
own. Nothing in the stream matches anything in the database. Joining them would
return nothing.

In a real platform the same service writes the trip row and emits the events for
that trip, so they always agree. `run` does the same, so one trip gets one row
and one stream of events about it.

This isn't only about tidiness. Anomaly detection needs the events and the trip
record to be about the same trip, and silver cannot join two sets of invented
data.

If a Kinesis-only load test is needed later, it should be a flag on this program
rather than a second source of data.

## Why `seed` stays

The tests use it, and the DMS full load needs a fixed starting dataset before
change capture has anything to read. The data quality work also rests on the
same seed producing the same planted mess every time, which a continuous run
cannot give.

## Determinism

`seed` stays reproducible. `run` is seeded too, but it's driven by wall clock
and by how long it runs. The same seed and the same duration give the same
data. Nothing weaker than that should be claimed.

## Deletes

`run` deletes a small share of rows on purpose. Change capture needs deletes to
carry, and the erasure model in ADR-0012 needs something to erase. Without them
neither can be shown working.

## What I'm giving up

A row and its events are written separately, so a failure between the two leaves
the database with a trip the stream never mentioned. Real platforms solve this
with an outbox, and that is more machinery than this needs. The gap is small
and visible in the data, and it's worth naming rather than hiding.

`run` only runs while a session is up. The platform is not always on, and the
repo should say so rather than imply otherwise.

Running both writes from one process means the stream rate and the database rate
are tied together. A test that needs them to diverge would need a second mode.

## What would flip this

- Needing the stream and the database to fail independently, which would make an
  outbox worth building.
- The generator becoming the bottleneck in the scale runs, which would push
  generation out to more than one process.
