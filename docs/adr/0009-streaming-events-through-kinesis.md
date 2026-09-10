# ADR-0009: Streaming the trip events through Kinesis

Status: Proposed
Date: 2026-09-08

## What I'm deciding

Where the trip events go once the generator makes them, and how I meet real
streaming problems in Phase 2 without running up a bill.

## The call

The same generator sends the trip events into a real Kinesis Data Stream on AWS,
in provisioned mode with two shards. Those events are the pos_update GPS pings
and the trip state changes named in the contract. The generator runs on my
machine and pushes to the stream, so the producer side is real even though
nothing else is deployed yet. A Firehose delivery stream then reads Kinesis and
lands the raw events as files in the raw zone bucket, which gives a working path
from a live event to the lake. The OLTP tables stay in the local Postgres from
ADR-0008, so this record covers only the event side.

Kinesis was already the streaming choice back in the dataset ADR, and it fits
the rest of the stack well. It's managed, there are no brokers of my own to run,
and it's billed per shard so I can keep two and then stop. Kafka would give the
same ideas of a partitioned log with ordering inside a key, so the concepts
carry over either way.

I picked provisioned over on-demand on purpose. Provisioned is where you set the
shard count and can push straight into its limit, which is the whole point here.
On-demand hides that ceiling and costs more to leave sitting idle.

## Why stream at all

A ride platform can't wait for a nightly batch to catch up. It needs the
driver's dot moving on the map now, an ETA within seconds, and a fast catch on a
fake or impossible trip. That steady flood of GPS pings is too much and too fast
for the OLTP database. Its shape is different too, so it belongs on a stream
instead. That is the honest reason the platform streams, rather than a feature
added to look busy.

## The real point, hitting the failure modes early

I want the streaming trouble here in a small cheap setup, not on the clean happy
path. One shard takes a thousand records a second. The pings from enough live
trips push past that, and the stream answers with a throughput error. I then fix
the producer the right way, sending records in batches and backing off and
retrying. After that I split the stream from one shard to two and watch how the
resharding behaves. Then I break it on purpose again by keying the events on
pickup zone, so downtown swamps one shard while the other sits idle. That skew
is exactly a hot shard. I catch it in the metrics and re-key by trip_id so the
load spreads evenly, and the skew clears.

This comes straight out of Designing Data-Intensive Applications, the
partitioning chapter on skew and hot spots and the streaming chapter on
partitioned logs and ordering. I would rather meet these failures here where I
can watch them and fix them, than run into them first on something that matters.

## Cost

Provisioned shards run about $0.015 per shard-hour, so two shards cost near $0.03
an hour while the stream is up. A two hour experiment is a few cents in total.
Firehose is billed by the gigabyte landed, and at this volume that comes to
pennies as well. Two shards left running for a whole month would reach about $22
and trip the 20 euro alarm, so teardown-first is the rule here too. Tearing down
deletes both the stream and the Firehose, so nothing keeps charging once I stop.

## Security and governance

There are no AWS keys in the repo, and there never will be. The producer on my
machine takes a short-lived role through my normal AWS login. That role can do
exactly one thing, write to this single stream. Firehose runs under its own role
that reads the stream and writes the raw bucket and nothing wider than that. The
stream is encrypted at rest with a KMS key and tagged like everything else.
Every event carries lat and lon, which the contract marks as restricted location
data. Those values stay in the raw zone and only become a coarse zone further
down, and the pipeline holds to that from the very first event. The producer
runs outside AWS for now, so it reaches Kinesis over TLS on the public endpoint.
That is the normal setup for a client outside the network. A private interface
endpoint inside the Phase 1 VPC is the right move once a producer or consumer
runs inside AWS. I'm noting it for that phase rather than pretending a local
script needs it.

## What I'm giving up

Two shards is tiny next to a real platform. The point here is not scale but cheap
practice at the failure modes, so the throughput won't match production while the
patterns and the fixes stay the same at any size. Firehose landing buffers events
into files, so it isn't true low-latency delivery. That's fine because the lake
reads in micro-batches anyway. A custom consumer with its own checkpointing and
dedup would show more skill, and I'm holding that back for when Spark reads the
stream in a later phase.

## What would flip this

- Throughput that two shards can't fake convincingly. Then I move to on-demand
  mode or add shards and accept the higher bill for that run.
- A need to prove consumer-side guarantees now, like exactly-once or ordered
  handling. Then a real consumer with checkpointing takes Firehose's place.
- Cost creeping up from things left running. The alarm is the backstop, and
  teardown-first is meant to stop it happening in the first place.
