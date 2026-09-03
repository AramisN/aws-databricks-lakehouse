# ADR-0004: Ride-hailing as the dataset domain

Status: Proposed
Date: 2026-09-01

## What I'm deciding

What domain the platform models. Where the data comes from, and how much of it I generate myself.

## The call

A ride-hailing marketplace. The OLTP data and the event stream and the logs are all synthetic. A seeded script I control generates them. Weather comes from a free live API. For the big Spark job I use a real public rideshare dataset.

## Why this domain

I wanted each source to need the tool it feeds, so the stack doesn't look padded. Riders and drivers and trips sit in a database that changes all the time, which is what change capture is for. GPS and trip-state events come in fast and never stop, and that's the case for streaming. Weather is outside data the platform pulls on a schedule. All three meet at the trip, so the joined tables mean something. One thing they can show is whether rain moves demand and trip times in a given zone. The fraud angle comes from the same data. Trips that move too fast to be real, faked locations, fares that don't add up.

Then privacy. A real name attached to exact pickup and dropoff points is heavy personal data. That makes the GDPR work matter instead of being for show.

## Why synthetic for the core

I can't get real ride-hailing data with real personal details, and I wouldn't put real personal data in a public repo anyway. Making my own is the only way to show PII handling and deletion on data I'm allowed to share. It also means anyone can clone the repo and rebuild the exact same data from the seed, which is worth something on its own.

## The sources

| Source | What it carries | Lands via | Real or synthetic |
|---|---|---|---|
| OLTP, Postgres | riders, drivers, vehicles, trips, payments | DMS CDC into raw | Synthetic |
| Event stream | trip state changes and GPS pings | Kinesis into raw | Synthetic |
| Logs | app and auth logs | FluentBit to S3 raw | Synthetic |
| Weather API | conditions by zone and hour | scheduled pull into raw | Real, Open-Meteo |
| TLC HVFHV | Uber and Lyft trips at volume | read from S3 for the scale demo | Real, NYC TLC |

## The real anchor, kept apart

NYC TLC publishes real Uber and Lyft trips as Parquet, and it's on the AWS Open Data registry. I use it for one thing, the large Spark job over tens of millions of rows. It stays in its own schema so it never mixes with the synthetic data. TLC gives location by zone, not exact coordinates. That's to protect riders. So the exact GPS is mine and synthetic, and the real data joins at zone level. That gap is a useful thing to be able to explain.

## What I'm giving up

Synthetic data is cleaner than real production data, so my quality checks are only catching problems I planted. I handle that by seeding real-looking mess. Late events, nulls, duplicates, values out of range, enough that the tests earn their keep.

## What would flip this

- A domain with a better interview story. The pipeline shape doesn't care about the domain, so switching is cheap now and costly later.
- A real dataset with usable PII under a clear licence. Unlikely, and it still wouldn't change the synthetic-first rule for a public repo.
