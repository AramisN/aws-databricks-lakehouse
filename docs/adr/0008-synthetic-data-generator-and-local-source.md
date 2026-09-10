# ADR-0008: The synthetic data generator and its local source

Status: Proposed
Date: 2026-09-08

## What I'm deciding

How Phase 2 makes its data. What builds the ride-hailing records, where the
database data lands, and how I plant real problems that the later checks can
catch.

## The call

One Python program generates the whole domain from a seed. It reads the data
contract and writes what the contract defines. The database tables, riders and
drivers and vehicles and trips and payments, go into a local Postgres in Docker.
That Postgres stands in for the ride company's own database, the on-prem system
a real DMS job would later copy from. The events and the logs go a different
way, decided in ADR-0009, so this record covers only the generator and the
database source.

The generator is the one place the data comes from. Run it with the same seed
and you get the same data back every time, so anyone can clone the repo and
rebuild the exact same records.

## Why one seeded generator, not a static dump

A fixed file of sample rows goes stale and hides how it was made. A seeded
program keeps it honest. Change the seed for a fresh world, or keep it to get
the same one back. This matters most for the data quality work, because the
checks downstream have to catch the same planted problems on every run or they
prove nothing. That is the testing and reproducibility point from Fundamentals,
put onto the source data itself.

## Why Postgres in Docker as the source

Real ride data with real people in it can't go in a public repo, and I wouldn't
want it there. A local Postgres lets me build the source for free and throw it
away in seconds while the shape still moves. It's also the right stand-in for
the DMS work later. A trip changes state across its life, requested then
accepted then started then finished, and that changing row is what change
capture reads. So the source is believable now, and the real DMS wiring waits
for the phase that builds the network tunnel back to it.

It runs Postgres 16, with the schema built from plain SQL files in the repo. I
skip the ORM because the schema is small and I'd rather read the SQL straight.

## Why the data is messy on purpose

Synthetic data comes out too clean, so left alone the checks would only catch
problems I forgot to remove. The generator plants real-looking mess instead,
late events, nulls where a field should be filled, duplicate rows, values out of
range. The mess is rate-controlled through flags like dup-rate and null-rate,
and it's on by default at low rates. It's seeded like everything else, so the
same run makes the same mess and the checks catch the same things each time.
Without that the whole data quality story would be for show.

## How PII is handled here

Every name and email and phone and license number is fake, made by Faker and
never tied to a real person. The generator writes each field where the real
source system would hold it, and that includes home_address, which the contract
only drops later above the raw layer. So the generator's job is to produce the
full messy PII-carrying source as it really is, while masking and hashing and
dropping stay with the layers above. Reading "drop" in the contract and having
the generator skip that field would be wrong, because the source system does
hold it.

The generator pins to a version of the data contract. A breaking change the
generator hasn't caught up with then shows as a failed check instead of quiet
bad data.

## Layout and teardown

A generator package holds the Python, a docker folder holds the Postgres compose
file, and Makefile targets make each step one command. make up starts Postgres,
make generate loads the data, make down stops it and drops the volume.
Teardown-first is the same habit as the Terraform in Phase 1, so nothing is left
running and the whole thing rebuilds from nothing.

## What I'm giving up

Synthetic data is still synthetic, and it can look like real ride-hailing
without breaking in the messy ways real data does. So a check that passes here
isn't proof it would pass in production, which is the trade I take for a public
repo. Loading a live Postgres is also slower than writing flat files, and it's
worth it because a real database is what the later change capture reads from.

## What would flip this

- More data than one machine and one Postgres can hold. Then the generator
  writes to files or object storage first, and a separate step loads the
  database.
- The schema outgrows what plain SQL by hand can keep clean. Then a light
  migration tool earns its place.
- A real dataset with usable, shareable PII under a clear license. That's
  unlikely, and it still wouldn't change the synthetic-first rule for anything
  public.
