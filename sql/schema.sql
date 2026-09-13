-- The six tables from the data contract (docs/architecture/data-contract.md),
-- in dependency order so the foreign keys can be created inline: zones
-- first, then riders/drivers/vehicles, then trips, then trip_events.
--
-- Column names and types match the generator's dataclasses field for field
-- (generator/entities.py, generator/trips.py) - load.py maps one to the
-- other by name, so a mismatch here fails at load, not silently.
--
-- Nullability matches what generator/mess.py is allowed to null out: only
-- trips.accept_ts, start_ts, end_ts, duration_s, rider_rating, and
-- trip_events.lat, lon, speed_kmh are nullable. Everything else is NOT
-- NULL, same as every other column mess.py never touches.

CREATE TABLE zones (
    zone_id  int  PRIMARY KEY,
    borough  text NOT NULL,
    name     text NOT NULL
);

CREATE TABLE riders (
    rider_id     bigint      PRIMARY KEY,
    first_name   text        NOT NULL,
    last_name    text        NOT NULL,
    email        text        NOT NULL,
    phone        text        NOT NULL,
    home_zone_id int         NOT NULL REFERENCES zones (zone_id),
    signup_ts    timestamptz NOT NULL
);

CREATE INDEX idx_riders_home_zone_id ON riders (home_zone_id);

CREATE TABLE drivers (
    driver_id      bigint      PRIMARY KEY,
    first_name     text        NOT NULL,
    last_name      text        NOT NULL,
    email          text        NOT NULL,
    phone          text        NOT NULL,
    license_number text        NOT NULL,
    home_zone_id   int         NOT NULL REFERENCES zones (zone_id),
    rating         numeric(3, 2) NOT NULL,
    status         text        NOT NULL,
    onboarded_ts   timestamptz NOT NULL
);

CREATE INDEX idx_drivers_home_zone_id ON drivers (home_zone_id);

CREATE TABLE vehicles (
    vehicle_id bigint PRIMARY KEY,
    driver_id  bigint NOT NULL REFERENCES drivers (driver_id),
    plate      text   NOT NULL,
    make       text   NOT NULL,
    model      text   NOT NULL,
    year       int    NOT NULL
);

CREATE INDEX idx_vehicles_driver_id ON vehicles (driver_id);

CREATE TABLE trips (
    trip_id         bigint         PRIMARY KEY,
    rider_id        bigint         NOT NULL REFERENCES riders (rider_id),
    driver_id       bigint         NOT NULL REFERENCES drivers (driver_id),
    request_ts      timestamptz    NOT NULL,
    accept_ts       timestamptz,
    start_ts        timestamptz,
    end_ts          timestamptz,
    pickup_zone_id  int            NOT NULL REFERENCES zones (zone_id),
    dropoff_zone_id int            NOT NULL REFERENCES zones (zone_id),
    distance_km     numeric(6, 2)  NOT NULL,
    duration_s      int,
    fare_amount     numeric(10, 2) NOT NULL,
    currency        char(3)        NOT NULL,
    status          text           NOT NULL,
    rider_rating    int
);

CREATE INDEX idx_trips_rider_id ON trips (rider_id);
CREATE INDEX idx_trips_driver_id ON trips (driver_id);
CREATE INDEX idx_trips_pickup_zone_id ON trips (pickup_zone_id);
CREATE INDEX idx_trips_dropoff_zone_id ON trips (dropoff_zone_id);

CREATE TABLE trip_events (
    event_id   uuid        PRIMARY KEY,
    trip_id    bigint      NOT NULL REFERENCES trips (trip_id),
    event_type text        NOT NULL,
    event_ts   timestamptz NOT NULL,
    lat        double precision,
    lon        double precision,
    speed_kmh  double precision
);

CREATE INDEX idx_trip_events_trip_id ON trip_events (trip_id);
