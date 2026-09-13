# generator

This is Phase 2, a seeded Python program that builds a synthetic ride-hailing
domain and either loads it into a local Postgres or writes the trip events
out as NDJSON (ADR-0008, ADR-0009). This is the whole reason Phase 2 doesn't
need AWS, everything here runs on your machine with Docker and uv.

## What it produces

Six collections, in this order (later ones reference earlier ones by id):

| Collection | Built by | What it is |
|---|---|---|
| zones | `entities.load_zones` | the taxi zone lookup, read from a CSV, not generated |
| riders | `entities.build_riders` | name, email, phone, a home zone |
| drivers | `entities.build_drivers` | same, plus a license number, rating, status |
| vehicles | `entities.build_vehicles` | one per driver |
| trips | `trips.build` | the state walk: requested → accepted → started → completed, or cancelled partway |
| trip_events | `trips.build` | `requested`/`accepted`/`started`/`pos_update`/`completed`/`cancelled`, one row per state change |

Then `mess.corrupt()` runs on the trips and events only (never the actors) and
`load.write()` or `files.write()` sends the result somewhere.

## Determinism

Same seed, same everything, byte for byte: `entities.build`, `trips.build`,
and `mess.corrupt` all take the same `random.Random` instance and never read
the clock or call anything unseeded. `generator/tests/test_determinism.py`
and `test_trips.py` prove this directly. Build twice with the same seed and
the output matches exactly; build with a different seed and it doesn't.

## The mess, on purpose

`mess.py` corrupts the clean trips and events at four independently
configurable rates, so the checks a later phase writes have real problems to
catch instead of already-clean data:

| Flag | What it does |
|---|---|
| `--dup-rate` | duplicates some rows, same data with a fresh id, not an exact primary-key copy (a real OLTP table would just reject that) |
| `--null-rate` | nulls out fields that are genuinely nullable (`accept_ts`, `start_ts`, `end_ts`, `duration_s`, `rider_rating` on trips; `lat`, `lon`, `speed_kmh` on events), never a key and never a required column |
| `--late-rate` | shifts some event timestamps 1–60 minutes later |
| `--out-of-range-rate` | pushes some trips' `fare_amount` negative and `rider_rating` outside 1–5 |

`generator/tests/test_mess_rates.py` checks the observed corruption frequency
lands within tolerance of the configured rate, and that rate 0 leaves the
data untouched.

## Running it standalone

You need Docker and [uv](https://docs.astral.sh/uv/), nothing else. No AWS
account, no cloud credentials, none of Phase 1 is required.

```bash
uv sync                                          # installs everything, generator included
cp .env.example .env                             # POSTGRES_USER/PASSWORD/DB, defaults are fine
docker compose up -d                             # starts Postgres 16, wal_level=logical
docker compose exec -T db psql -U postgres -d rideshare < sql/schema.sql
```

Docker Desktop has to actually be running before `docker compose up -d`. If it isn't, you'll
get `Cannot connect to the Docker daemon`, not a compose error. Start Docker and rerun.

The `-U postgres -d rideshare` above isn't a guess, it's `.env`, `POSTGRES_USER` and
`POSTGRES_DB` from the file you just copied. If you changed those, use your own values. Or
if you're not sure what's actually running, ask the container instead of guessing:
`docker compose exec db env | grep POSTGRES`.

The repo ships a small 8-zone fixture (`generator/tests/sample/zones.csv`),
so you can generate right away without downloading anything:

```bash
uv run rides-generate --zones-csv generator/tests/sample/zones.csv --target postgres
```

For realistic volumes, use the real NYC TLC zone lookup instead. It's not
committed, it's gitignored under `data/` since it's external reference data,
not something this repo generates:

```bash
mkdir -p data/reference
curl -o data/reference/taxi_zone_lookup.csv \
  https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
uv run rides-generate --target postgres   # zones_csv defaults to the path above
```

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--seed` | `42` | seeds the rng and Faker; same seed, same output |
| `--riders` | `1000` | how many riders to build |
| `--drivers` | `200` | how many drivers (and vehicles, one each) |
| `--trips` | `10000` | how many trips (and their events) |
| `--dup-rate` | `0.01` | see above |
| `--null-rate` | `0.02` | see above |
| `--late-rate` | `0.05` | see above |
| `--out-of-range-rate` | `0.01` | see above |
| `--target` | `postgres` | `postgres` or `files` (see below) |
| `--zones-csv` | `data/reference/taxi_zone_lookup.csv` | the taxi zone lookup CSV to read |

Every flag has a matching `GENERATOR_*` env var (`GENERATOR_SEED`,
`GENERATOR_RIDERS`, and so on) read from `.env` via `generator/config.py`,
if you'd rather set defaults once than pass flags every time.

## The two targets

- **`--target postgres`** (default). `load.write()` truncates all six
  tables (one statement, so FK order doesn't matter) and `COPY`s the data
  back in, zones first through trip_events last, in one transaction. Safe to
  run repeatedly, same seed in, same tables out, never a duplicate-key error.
- **`--target files`**. `files.write()` writes the trip events only, not
  the actors, since those stay Postgres-only (ADR-0008). It writes to
  `data/events.ndjson`, one JSON object per line. This is the local stand-in
  for Kinesis before that exists (ADR-0009).

## Tearing down

```bash
docker compose down -v   # -v drops the named volume, so Postgres starts clean next time
```

## Tests

```bash
uv run pytest generator/tests -v
uv run ruff check generator && uv run ruff format --check generator
uv run mypy generator
```
