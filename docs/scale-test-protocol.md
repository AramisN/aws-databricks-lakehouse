# Scale test protocol

This fixes what gets measured and how, before anything runs. Written first on
purpose. If each run answers a slightly different question, the numbers can't be
compared and the whole exercise is worth nothing.

## What I'm actually testing

Not whether AWS can handle the volume. It can. What I want to find is where this
particular setup starts to bend, and what has to change when it does. A rung
where nothing breaks is a result too, it just isn't an interesting one.

The claim I want to be able to make at the end is not "I moved forty million
rows". It's "at this volume this specific thing broke, here is what it looked
like in the metrics, here is what I changed, here is what it looked like after".
Anyone can say the first one. The second one only comes from having been there.

## The ladder

Four rungs, each roughly ten times the last. Sizes are in trips, since that's
what the generator takes and everything else follows from it.

| Rung | Trips | Purpose |
|------|-------|---------|
| 0 | 10,000 | Baseline. The current default. Proves the path works end to end. |
| 1 | 100,000 | First rung where file sizing starts to show. |
| 2 | 1,000,000 | Where I expect the generator's memory use to matter. |
| 3 | 10,000,000 | Where Postgres, the replication slot and the disk get tested. |

Events come out at some multiple of trips. I measure that ratio at rung 0 and use
it to predict the row counts higher up, rather than guessing now.

Rung 3 is the target. If it holds, a fourth rung at 40 million is worth trying,
but I'd rather get four clean rungs than reach for a bigger number and have
nothing recorded properly.

## What gets recorded at every rung

Same numbers every time, no exceptions.

Source side, from Postgres:

- rows per table after loading
- database size on disk
- write-ahead log retained by the replication slot, and how far it lags
- how long generating and loading took

Pipeline side, from DMS in CloudWatch:

- full load throughput, rows per second, at source and target
- change capture latency, source and target
- incoming changes
- CPU, freeable memory and swap on the replication instance

Landing side, from S3:

- number of files written per table
- file size spread, smallest, median, largest
- total bytes landed
- compression ratio against the source size

And for the run as a whole:

- wall clock from start to caught up
- dollars, taken from Cost Explorer after the fact rather than estimated
- every setting that differed from the previous rung

The metric names above are what I expect DMS to publish. I check them in the
console on rung 0 and correct this list if they differ, rather than writing a
script against names I assumed.

## Rules for a run to count

One thing changes at a time. If a rung needs both a bigger instance and a longer
batch interval, that's two runs, not one.

Settings get written down before the run starts, not reconstructed after.

Raw numbers go into a CSV in the repo, one row per run. The writeup reads from
it. If a number only exists in a screenshot, it isn't recorded.

Screenshots for the moments worth seeing, the way the Kinesis throttling test
did it. A graph of latency climbing is worth more than a sentence saying it did.

A run that fails still counts and still gets its row, with what failed in the
notes. Those are usually the useful ones.

## Stop conditions

Stop and tear down if any of these happen:

- the run has cost more than five dollars
- the source disk passes 80 percent used
- anything has been running over four hours without finishing
- I can't say what the current run is trying to answer

The last one matters most. Once a session turns into poking at things, the
numbers stop meaning anything and the money is being spent for nothing.

## What a finding looks like

A finding needs four parts, or it doesn't go in the writeup:

1. the symptom, with the metric that showed it
2. the volume it appeared at
3. what changed
4. the same metric afterwards

Anything without all four is a note, not a finding.

## Expected breakpoints

Written down now so I can check later how good my guesses were, which is its own
kind of useful.

The generator building everything in memory should be the first wall, somewhere
around rung 2, and it's fixed before the run rather than discovered during it.

Small files should show at rung 1, where the batch interval closes files before
they get anywhere near the size limit.

The replication slot filling the disk should show at rung 3, most likely if I
stop a task and leave the slot behind.

Replication instance memory is the one I'm least sure about. It might arrive
earlier than I think.

## Limits of all this

One source database, one replication instance, one account, one person watching.
No competing workloads, no other teams changing the schema underneath, nobody
paged at three in the morning. What comes out of this is real evidence about
ingestion behaviour at volume, and nothing at all about running a platform in
production. Worth saying plainly, because the difference is the first thing an
interviewer will probe.
