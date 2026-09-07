# Data contract, ride-hailing domain

This is the source of truth for the schema and the PII handling. Every phase reads from it, the generator, the dbt models, the streaming job, the governance rules. It's a living document, not an ADR, so it has no status. It changes as the schema settles, and those changes travel through pull requests like everything else.

## How to read the PII column

Class is what the field is.

- direct, identifies a person on its own
- quasi, identifies a person in combination with other fields
- location, precise enough to track someone
- financial, money data, sensitive but not identifying on its own
- none, safe

Handling is what happens to it past the raw layer.

- keep, safe to carry as-is
- restricted, stays in the raw zone only, visible to the restricted role, never carried downstream
- mask, hidden in analytics views through Unity Catalog when a direct identifier must sit in a table, visible only to the restricted role
- hash, deterministic hash for cases needing correlation without keeping the raw value
- generalize, coarsened, an age band instead of a birthdate, a zone instead of an address
- drop, not carried past raw at all

## OLTP, the DMS change-capture source

### riders

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| rider_id | bigint | PK | quasi | keep |
| first_name | text | | direct | restricted |
| last_name | text | | direct | restricted |
| email | text | | direct | restricted |
| phone | text | | direct | restricted |
| date_of_birth | date | | quasi | generalize to age band |
| home_zone_id | int | FK zones | location | keep, zone only |
| home_address | text | | direct | drop, zone kept instead |
| signup_ts | timestamp | | none | keep |
| status | text | | none | keep |

### drivers

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| driver_id | bigint | PK | quasi | keep |
| first_name | text | | direct | restricted |
| last_name | text | | direct | restricted |
| email | text | | direct | restricted |
| phone | text | | direct | restricted |
| license_number | text | | direct | restricted |
| vehicle_id | bigint | FK vehicles | none | keep |
| rating | numeric | | none | keep |
| onboarded_ts | timestamp | | none | keep |
| status | text | | none | keep |

### vehicles

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| vehicle_id | bigint | PK | none | keep |
| plate | text | | quasi | mask |
| make | text | | none | keep |
| model | text | | none | keep |
| year | int | | none | keep |
| capacity | int | | none | keep |

### trips, mutable, this is what CDC captures changing

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| trip_id | bigint | PK | none | keep |
| rider_id | bigint | FK riders | quasi | keep |
| driver_id | bigint | FK drivers | quasi | keep |
| request_ts | timestamp | | none | keep |
| accept_ts | timestamp | | none | keep |
| start_ts | timestamp | | none | keep |
| end_ts | timestamp | | none | keep |
| pickup_zone_id | int | FK zones | location | keep, zone only |
| dropoff_zone_id | int | FK zones | location | keep, zone only |
| distance_km | numeric | | none | keep |
| duration_s | int | | none | keep |
| fare_amount | numeric | | financial | keep |
| currency | char(3) | | none | keep |
| status | text | | none | keep |
| rider_rating | int | | none | keep |

### payments

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| payment_id | bigint | PK | none | keep |
| trip_id | bigint | FK trips | none | keep |
| rider_id | bigint | FK riders | quasi | keep |
| amount | numeric | | financial | keep |
| currency | char(3) | | none | keep |
| method | text | | none | keep |
| card_last4 | char(4) | | financial | keep, truncated, full card number never stored |
| status | text | | none | keep |
| paid_ts | timestamp | | none | keep |

## Event stream, Kinesis

### trip_events

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| event_id | uuid | PK | none | keep |
| trip_id | bigint | FK trips | none | keep |
| event_type | text | | none | keep, one of requested/accepted/started/pos_update/completed/cancelled |
| event_ts | timestamp | | none | keep |
| lat | double | | location | restricted in raw, generalize to zone downstream |
| lon | double | | location | restricted in raw, generalize to zone downstream |
| speed_kmh | double | | none | keep |

## Logs, S3 raw

### app_logs

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| log_ts | timestamp | | none | keep |
| service | text | | none | keep |
| level | text | | none | keep |
| actor_id | bigint | rider or driver | quasi | keep |
| session_id | text | | quasi | keep |
| ip_address | text | | direct | hash, dropped after short retention |
| message | text | | none | keep, scrubbed for PII before landing |

## Weather, Open-Meteo API

### weather

| Field | Type | Key | PII | Handling |
|---|---|---|---|---|
| zone_id | int | FK zones | none | keep |
| ts_hour | timestamp | | none | keep |
| temp_c | double | | none | keep |
| precip_mm | double | | none | keep |
| wind_kmh | double | | none | keep |
| weather_code | int | | none | keep |

Join key is zone_id plus ts_hour. No personal data here.

## Reference and real anchor

### zones
Taxi zone lookup, zone_id, name, borough. From the TLC zone table. No PII.

### tlc_hvfhv
Real Uber and Lyft trips, external Parquet, read only for the scale demo. Zone-based, no PII. Kept in its own schema, never joined into the synthetic domain.

## Join model

The trip is the hub. Riders, drivers, vehicles, and payments join to it by key. Trip events join by trip_id. Weather joins by pickup_zone_id and the hour of the trip. Logs join by actor_id and session. The gold trip fact is the trip plus its people, governed for PII, plus movement metrics derived from the events, plus the weather for that zone and hour.

## Right to erasure

A deletion request runs as a Delta DELETE against the synthetic tables, followed by VACUUM past the retention window so the old versions are actually gone, not just logically removed. No token vault is involved; this project owns every copy of the data, so a hard delete plus VACUUM reaches all of it. A reconciliation check confirms the person is absent across raw, bronze, silver, and gold before the request is marked done.

## Retention

Raw personal data lives in a restricted zone with a short retention window. The bronze, silver, and gold layers hold only masked, hashed, or generalized values, so the analytics side never sees direct identifiers.

## A note on scope

The data is synthetic, so this models the controls a real platform would need rather than satisfying an actual legal obligation. The point is to build and demonstrate the machinery, not to claim compliance.
