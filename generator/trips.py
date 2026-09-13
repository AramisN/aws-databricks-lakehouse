# Builds trips and their trip_events (the pos_update pings included).
#
# Same rule as entities.py: everything comes from the rng that gets passed
# in, so the same seed always produces the same trips. No faker parameter
# here on purpose - there's no name/email/phone to fake in a trip.
#
# The zones CSV doesn't have real coordinates, so each zone gets a made-up
# lat/lon (picked once, from the rng, and reused for every trip through
# that zone). It's enough to draw a plausible-looking path on a map, it's
# not real NYC geography.

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from generator.entities import REFERENCE_DATE, Entities

TRIP_LOOKBACK_DAYS = 90

ACCEPT_WAIT_SECONDS_RANGE = (10, 180)
ARRIVE_WAIT_SECONDS_RANGE = (60, 600)
TRIP_DURATION_SECONDS_RANGE = (180, 3600)
CANCEL_DECISION_SECONDS_RANGE = (5, 120)

CANCELLATION_RATE = 0.08
CANCEL_AFTER_ACCEPT_RATE = 0.6

DISTANCE_KM_RANGE = (0.8, 25.0)
BASE_FARE = Decimal("3.00")
PER_KM_RATE = Decimal("1.75")
CURRENCY = "USD"

# Mostly good ratings, like a real ride-hailing app.
RATING_POOL = [5, 5, 5, 5, 5, 4, 4, 4, 3, 3, 2, 1]

PING_INTERVAL_SECONDS = 45
AVG_SPEED_KMH = 25.0
JITTER_DEGREES = 0.002

# A rough NYC bounding box, wide enough to cover all five boroughs.
NYC_LAT_RANGE = (40.49, 40.92)
NYC_LON_RANGE = (-74.26, -73.68)

EVENT_REQUESTED = "requested"
EVENT_ACCEPTED = "accepted"
EVENT_STARTED = "started"
EVENT_POS_UPDATE = "pos_update"
EVENT_COMPLETED = "completed"
EVENT_CANCELLED = "cancelled"


# The four timestamp fields below are the contract for the SQL schema and
# load.py later, so renaming them means updating those too. Also worth
# knowing: request_ts is picked independently for every trip, so trip_id
# order and time order don't line up (trip 1 can happen after trip 500).
# That's fine for now but matters once something downstream assumes trips
# arrive in id order.
# A single trip record.
# e.g. trip_id=1, rider_id=3, driver_id=3, request_ts='2025-10-24 14:13:44',
#      accept_ts='2025-10-24 14:14:53', start_ts='2025-10-24 14:23:37',
#      end_ts='2025-10-24 15:10:00' (all four are datetime values),
#      pickup_zone_id=6, dropoff_zone_id=4, distance_km=2.48, duration_s=2783,
#      fare_amount=7.34, currency='USD', status='completed', rider_rating=5
@dataclass
class Trip:
    trip_id: int
    rider_id: int
    driver_id: int
    request_ts: datetime
    accept_ts: datetime | None
    start_ts: datetime | None
    end_ts: datetime | None
    pickup_zone_id: int
    dropoff_zone_id: int
    distance_km: Decimal
    duration_s: int | None
    fare_amount: Decimal
    currency: str
    status: str
    rider_rating: int | None


# One event in a trip's lifecycle, including the pos_update pings.
# e.g. event_id='998d48a9-8e8a-573a-8ace-e7c54d54154a' (a uuid value), trip_id=1,
#      event_type='requested', event_ts='2025-10-24 14:13:44' (a datetime value),
#      lat=40.6037, lon=-74.2348, speed_kmh=None
@dataclass
class TripEvent:
    event_id: UUID
    trip_id: int
    event_type: str
    event_ts: datetime
    lat: float | None
    lon: float | None
    speed_kmh: float | None


# Builds a UUID from the rng instead of calling uuid4().
# e.g. new_event_id(rng) -> UUID('998d48a9-8e8a-573a-8ace-e7c54d54154a')
def new_event_id(rng: random.Random) -> UUID:
    # Build the id from 16 random bytes off our own rng instead of calling
    # uuid4(), which reads from the OS and isn't reproducible.
    return UUID(bytes=rng.randbytes(16))


# Picks a random timestamp somewhere in the lookback_days before reference.
# e.g. random_past_timestamp(rng, REFERENCE_DATE, TRIP_LOOKBACK_DAYS)
#   -> a datetime value like 2025-10-24 14:13:44, somewhere in the last 90 days
def random_past_timestamp(
    rng: random.Random, reference: datetime, lookback_days: int
) -> datetime:
    max_seconds = lookback_days * 24 * 60 * 60
    seconds_back = rng.randint(0, max_seconds)
    return reference - timedelta(seconds=seconds_back)


# Assigns each zone a made-up lat/lon, reused for every trip through it.
# e.g. zone_coordinates(rng, entities)  # entities has 8 zones
#   -> {1: (40.68, -74.17), ..., 6: (40.6037, -74.2348), ..., 8: (40.75, -73.91)}
def zone_coordinates(
    rng: random.Random, entities: Entities
) -> dict[int, tuple[float, float]]:
    # Sort here instead of trusting entities.zones to already be sorted -
    # that way this function's output only depends on this rng and this
    # code, not on however entities.py happens to order its list.
    zones = sorted(entities.zones, key=lambda z: z.zone_id)

    coords = {}
    for zone in zones:
        lat = rng.uniform(*NYC_LAT_RANGE)
        lon = rng.uniform(*NYC_LON_RANGE)
        coords[zone.zone_id] = (lat, lon)
    return coords


# Builds the pos_update pings for one trip, from start to finish.
# e.g. build_pos_updates(rng, trip_id=1, start_ts=..., duration_s=2783,
#                         pickup=(40.6037, -74.2348), dropoff=(40.71, -74.19))
#   -> [TripEvent(event_type='pos_update', event_ts=start_ts + 45s, lat=..., lon=..., speed_kmh=...),
#       TripEvent(event_type='pos_update', event_ts=start_ts + 90s, ...), ...]
def build_pos_updates(
    rng: random.Random,
    trip_id: int,
    start_ts: datetime,
    duration_s: int,
    pickup: tuple[float, float],
    dropoff: tuple[float, float],
) -> list[TripEvent]:
    """One ping every PING_INTERVAL_SECONDS, moving from pickup to dropoff.

    A trip shorter than one interval just doesn't get any pings, which is
    fine.
    """
    pickup_lat, pickup_lon = pickup
    dropoff_lat, dropoff_lon = dropoff

    pings = []
    elapsed_s = PING_INTERVAL_SECONDS
    while elapsed_s < duration_s:
        fraction = elapsed_s / duration_s

        lat = pickup_lat + (dropoff_lat - pickup_lat) * fraction
        lat += rng.uniform(-JITTER_DEGREES, JITTER_DEGREES)

        lon = pickup_lon + (dropoff_lon - pickup_lon) * fraction
        lon += rng.uniform(-JITTER_DEGREES, JITTER_DEGREES)

        speed_kmh = AVG_SPEED_KMH * rng.uniform(0.6, 1.3)

        ping = TripEvent(
            event_id=new_event_id(rng),
            trip_id=trip_id,
            event_type=EVENT_POS_UPDATE,
            event_ts=start_ts + timedelta(seconds=elapsed_s),
            lat=lat,
            lon=lon,
            speed_kmh=speed_kmh,
        )
        pings.append(ping)
        elapsed_s += PING_INTERVAL_SECONDS

    return pings


# Finishes building a trip that gets cancelled, before or after acceptance.
# e.g. build_cancelled_trip(trip_id=2, rng, rider_id=5, driver_id=1,
#                            pickup_zone_id=7, dropoff_zone_id=3, request_ts=...,
#                            distance_km=Decimal('12.11'), fare_amount=Decimal('24.19'),
#                            events=[<the 'requested' event already added by build_trip>])
#   -> Trip(trip_id=2, ..., start_ts=None, end_ts=None, status='cancelled', rider_rating=None)
#   and appends an 'accepted' event (maybe) and a 'cancelled' event to `events`
def build_cancelled_trip(
    trip_id: int,
    rng: random.Random,
    rider_id: int,
    driver_id: int,
    pickup_zone_id: int,
    dropoff_zone_id: int,
    request_ts: datetime,
    distance_km: Decimal,
    fare_amount: Decimal,
    events: list[TripEvent],
) -> Trip:
    accept_ts = None
    if rng.random() < CANCEL_AFTER_ACCEPT_RATE:
        wait_seconds = rng.randint(*ACCEPT_WAIT_SECONDS_RANGE)
        accept_ts = request_ts + timedelta(seconds=wait_seconds)
        events.append(
            TripEvent(
                event_id=new_event_id(rng),
                trip_id=trip_id,
                event_type=EVENT_ACCEPTED,
                event_ts=accept_ts,
                lat=None,
                lon=None,
                speed_kmh=None,
            )
        )

    last_ts = accept_ts if accept_ts is not None else request_ts
    cancel_wait_seconds = rng.randint(*CANCEL_DECISION_SECONDS_RANGE)
    cancelled_ts = last_ts + timedelta(seconds=cancel_wait_seconds)
    events.append(
        TripEvent(
            event_id=new_event_id(rng),
            trip_id=trip_id,
            event_type=EVENT_CANCELLED,
            event_ts=cancelled_ts,
            lat=None,
            lon=None,
            speed_kmh=None,
        )
    )

    return Trip(
        trip_id=trip_id,
        rider_id=rider_id,
        driver_id=driver_id,
        request_ts=request_ts,
        accept_ts=accept_ts,
        start_ts=None,
        end_ts=None,
        pickup_zone_id=pickup_zone_id,
        dropoff_zone_id=dropoff_zone_id,
        distance_km=distance_km,
        duration_s=None,
        fare_amount=fare_amount,
        currency=CURRENCY,
        status="cancelled",
        rider_rating=None,
    )


# Finishes building a trip that runs all the way through to completion.
# e.g. build_completed_trip(trip_id=1, rng, rider_id=3, driver_id=3,
#                            pickup_zone_id=6, dropoff_zone_id=4,
#                            pickup=(40.6037, -74.2348), dropoff=(40.71, -74.19),
#                            request_ts=..., distance_km=Decimal('2.48'),
#                            fare_amount=Decimal('7.34'), events=[<the 'requested' event>])
#   -> Trip(trip_id=1, ..., status='completed', rider_rating=5)
#   and appends 'accepted', 'started', the pos_update pings, and 'completed' to `events`
def build_completed_trip(
    trip_id: int,
    rng: random.Random,
    rider_id: int,
    driver_id: int,
    pickup_zone_id: int,
    dropoff_zone_id: int,
    pickup: tuple[float, float],
    dropoff: tuple[float, float],
    request_ts: datetime,
    distance_km: Decimal,
    fare_amount: Decimal,
    events: list[TripEvent],
) -> Trip:
    accept_wait = rng.randint(*ACCEPT_WAIT_SECONDS_RANGE)
    accept_ts = request_ts + timedelta(seconds=accept_wait)
    events.append(
        TripEvent(
            event_id=new_event_id(rng),
            trip_id=trip_id,
            event_type=EVENT_ACCEPTED,
            event_ts=accept_ts,
            lat=None,
            lon=None,
            speed_kmh=None,
        )
    )

    arrive_wait = rng.randint(*ARRIVE_WAIT_SECONDS_RANGE)
    start_ts = accept_ts + timedelta(seconds=arrive_wait)
    duration_s = rng.randint(*TRIP_DURATION_SECONDS_RANGE)
    end_ts = start_ts + timedelta(seconds=duration_s)

    events.append(
        TripEvent(
            event_id=new_event_id(rng),
            trip_id=trip_id,
            event_type=EVENT_STARTED,
            event_ts=start_ts,
            lat=pickup[0],
            lon=pickup[1],
            speed_kmh=0.0,
        )
    )
    events.extend(
        build_pos_updates(rng, trip_id, start_ts, duration_s, pickup, dropoff)
    )
    events.append(
        TripEvent(
            event_id=new_event_id(rng),
            trip_id=trip_id,
            event_type=EVENT_COMPLETED,
            event_ts=end_ts,
            lat=dropoff[0],
            lon=dropoff[1],
            speed_kmh=None,
        )
    )

    return Trip(
        trip_id=trip_id,
        rider_id=rider_id,
        driver_id=driver_id,
        request_ts=request_ts,
        accept_ts=accept_ts,
        start_ts=start_ts,
        end_ts=end_ts,
        pickup_zone_id=pickup_zone_id,
        dropoff_zone_id=dropoff_zone_id,
        distance_km=distance_km,
        duration_s=duration_s,
        fare_amount=fare_amount,
        currency=CURRENCY,
        status="completed",
        rider_rating=rng.choice(RATING_POOL),
    )


# Builds one trip and its events: picks rider/driver/zones, then branches
# to a cancelled or a completed trip.
# e.g. build_trip(trip_id=1, rng, entities, zone_coords)
#   -> (Trip(trip_id=1, ..., status='completed', ...), [TripEvent('requested', ...),
#       TripEvent('accepted', ...), TripEvent('started', ...), ...,
#       TripEvent('completed', ...)])
def build_trip(
    trip_id: int,
    rng: random.Random,
    entities: Entities,
    zone_coords: dict[int, tuple[float, float]],
) -> tuple[Trip, list[TripEvent]]:
    rider_id = rng.choice(entities.riders).rider_id
    driver_id = rng.choice(entities.drivers).driver_id
    pickup_zone_id = rng.choice(entities.zones).zone_id
    dropoff_zone_id = rng.choice(entities.zones).zone_id
    pickup = zone_coords[pickup_zone_id]
    dropoff = zone_coords[dropoff_zone_id]

    request_ts = random_past_timestamp(rng, REFERENCE_DATE, TRIP_LOOKBACK_DAYS)

    # distance_km is the planned route distance, known as soon as the trip
    # is requested, so it's set the same way whether the trip completes or
    # gets cancelled. fare_amount is the quoted fare based on it.
    distance_km = Decimal(str(round(rng.uniform(*DISTANCE_KM_RANGE), 2)))
    fare_amount = round(BASE_FARE + PER_KM_RATE * distance_km, 2)

    events = [
        TripEvent(
            event_id=new_event_id(rng),
            trip_id=trip_id,
            event_type=EVENT_REQUESTED,
            event_ts=request_ts,
            lat=pickup[0],
            lon=pickup[1],
            speed_kmh=None,
        )
    ]

    if rng.random() < CANCELLATION_RATE:
        trip = build_cancelled_trip(
            trip_id,
            rng,
            rider_id,
            driver_id,
            pickup_zone_id,
            dropoff_zone_id,
            request_ts,
            distance_km,
            fare_amount,
            events,
        )
    else:
        trip = build_completed_trip(
            trip_id,
            rng,
            rider_id,
            driver_id,
            pickup_zone_id,
            dropoff_zone_id,
            pickup,
            dropoff,
            request_ts,
            distance_km,
            fare_amount,
            events,
        )

    return trip, events


# Builds all the trips and their events for one generator run.
# e.g. build(rng, trips=4, entities)  # entities from entities.build() above
#   -> ([Trip(trip_id=1, ...), Trip(trip_id=2, ...), Trip(trip_id=3, ...),
#        Trip(trip_id=4, ...)],
#       [TripEvent(trip_id=1, event_type='requested', ...), ... 190 events total])
def build(
    rng: random.Random, trips: int, entities: Entities
) -> tuple[list[Trip], list[TripEvent]]:
    """Build `trips` trips and their trip_events using one seeded rng.

    Each trip walks through requested -> accepted -> started -> pos_update
    (zero or more) -> completed, unless it gets cancelled first, which can
    happen before or after acceptance. Timestamps only move forward within
    a trip.
    """
    zone_coords = zone_coordinates(rng, entities)

    built_trips = []
    built_events = []
    for trip_id in range(1, trips + 1):
        trip, events = build_trip(trip_id, rng, entities, zone_coords)
        built_trips.append(trip)
        built_events.extend(events)

    built_trips.sort(key=lambda t: t.trip_id)
    built_events.sort(key=lambda e: (e.trip_id, e.event_ts))
    return built_trips, built_events
