# Loads the generator's Python objects into the Postgres tables from
# sql/schema.sql, using COPY rather than one INSERT per row - the
# difference that matters once trip_events gets into the hundreds of
# thousands of rows.
#
# Truncates every table first, so running this twice never fails on a
# duplicate key: regenerate from the same seed, reload, get the same
# tables back. The whole load is one transaction - a failure partway
# through leaves the tables exactly as they were, not half loaded.

import psycopg

from generator.config import db_settings
from generator.entities import Driver, Entities, Rider, Vehicle, Zone
from generator.trips import Trip, TripEvent

# Reverse FK order, so truncating all six together in one statement never
# trips a foreign key.
TABLES_IN_REVERSE_FK_ORDER = (
    "trip_events",
    "trips",
    "vehicles",
    "drivers",
    "riders",
    "zones",
)


# Opens a connection using the POSTGRES_* settings from config.py - never
# a hardcoded host or password.
# e.g. connect() -> a psycopg.Connection to localhost:5432/rideshare
def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=db_settings.host,
        port=db_settings.port,
        user=db_settings.user,
        password=db_settings.password,
        dbname=db_settings.db,
    )


# Empties every table in one statement, so FK order doesn't matter here and
# a second run of write() starts from a clean slate instead of erroring on
# duplicate primary keys.
def truncate_all(cur: psycopg.Cursor) -> None:
    tables = ", ".join(TABLES_IN_REVERSE_FK_ORDER)
    cur.execute(f"TRUNCATE {tables}")


# Copies the zone reference rows in.
def copy_zones(cur: psycopg.Cursor, zones: list[Zone]) -> None:
    with cur.copy("COPY zones (zone_id, borough, name) FROM STDIN") as copy:
        for zone in zones:
            copy.write_row((zone.zone_id, zone.borough, zone.name))


# Copies the rider rows in.
def copy_riders(cur: psycopg.Cursor, riders: list[Rider]) -> None:
    with cur.copy(
        "COPY riders (rider_id, first_name, last_name, email, phone, home_zone_id, "
        "signup_ts) FROM STDIN"
    ) as copy:
        for rider in riders:
            copy.write_row(
                (
                    rider.rider_id,
                    rider.first_name,
                    rider.last_name,
                    rider.email,
                    rider.phone,
                    rider.home_zone_id,
                    rider.signup_ts,
                )
            )


# Copies the driver rows in.
def copy_drivers(cur: psycopg.Cursor, drivers: list[Driver]) -> None:
    with cur.copy(
        "COPY drivers (driver_id, first_name, last_name, email, phone, license_number, "
        "home_zone_id, rating, status, onboarded_ts) FROM STDIN"
    ) as copy:
        for driver in drivers:
            copy.write_row(
                (
                    driver.driver_id,
                    driver.first_name,
                    driver.last_name,
                    driver.email,
                    driver.phone,
                    driver.license_number,
                    driver.home_zone_id,
                    driver.rating,
                    driver.status,
                    driver.onboarded_ts,
                )
            )


# Copies the vehicle rows in.
def copy_vehicles(cur: psycopg.Cursor, vehicles: list[Vehicle]) -> None:
    with cur.copy(
        "COPY vehicles (vehicle_id, driver_id, plate, make, model, year) FROM STDIN"
    ) as copy:
        for vehicle in vehicles:
            copy.write_row(
                (
                    vehicle.vehicle_id,
                    vehicle.driver_id,
                    vehicle.plate,
                    vehicle.make,
                    vehicle.model,
                    vehicle.year,
                )
            )


# Copies the trip rows in, corrupted or not - COPY doesn't care, it just
# needs the row to fit the column types, which the schema's nullable
# columns already allow for.
def copy_trips(cur: psycopg.Cursor, trips: list[Trip]) -> None:
    with cur.copy(
        "COPY trips (trip_id, rider_id, driver_id, request_ts, accept_ts, start_ts, "
        "end_ts, pickup_zone_id, dropoff_zone_id, distance_km, duration_s, fare_amount, "
        "currency, status, rider_rating) FROM STDIN"
    ) as copy:
        for trip in trips:
            copy.write_row(
                (
                    trip.trip_id,
                    trip.rider_id,
                    trip.driver_id,
                    trip.request_ts,
                    trip.accept_ts,
                    trip.start_ts,
                    trip.end_ts,
                    trip.pickup_zone_id,
                    trip.dropoff_zone_id,
                    trip.distance_km,
                    trip.duration_s,
                    trip.fare_amount,
                    trip.currency,
                    trip.status,
                    trip.rider_rating,
                )
            )


# Copies the trip event rows in, pos_update pings included.
def copy_trip_events(cur: psycopg.Cursor, events: list[TripEvent]) -> None:
    with cur.copy(
        "COPY trip_events (event_id, trip_id, event_type, event_ts, lat, lon, speed_kmh, "
        "pickup_zone_id) FROM STDIN"
    ) as copy:
        for event in events:
            copy.write_row(
                (
                    event.event_id,
                    event.trip_id,
                    event.event_type,
                    event.event_ts,
                    event.lat,
                    event.lon,
                    event.speed_kmh,
                    event.pickup_zone_id,
                )
            )


# The entry point: truncates every table, then loads all six collections in
# FK order (zones first, trip_events last), all inside one transaction.
# e.g. write(entities, messy_trips, messy_events) -> Postgres now holds
#      exactly those rows, or none of them, if anything failed partway through
def write(entities: Entities, trips: list[Trip], events: list[TripEvent]) -> None:
    with connect() as conn, conn.cursor() as cur:
        truncate_all(cur)
        copy_zones(cur, entities.zones)
        copy_riders(cur, entities.riders)
        copy_drivers(cur, entities.drivers)
        copy_vehicles(cur, entities.vehicles)
        copy_trips(cur, trips)
        copy_trip_events(cur, events)
