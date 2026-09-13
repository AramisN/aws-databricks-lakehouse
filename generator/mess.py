# Deliberately corrupts clean trips and events, so the data quality checks
# built later have real problems to catch instead of already-clean data.
#
# Runs after entities.py and trips.py, never inside them, that boundary is
# what lets "clean generation is correct" and "corruption happens at the
# right rate" get tested separately. Everything here comes from the rng
# that gets passed in, and every function returns new lists rather than
# changing the rows it was given, so the original clean data stays around
# for comparison.

import random
from dataclasses import replace
from datetime import timedelta

from generator.trips import Trip, TripEvent, new_event_id

# Only these fields get nulled out - they're the ones already typed as
# optional in Trip/TripEvent, so nulling them can't violate a key or a
# not-null column.
NULLABLE_TRIP_FIELDS = ("accept_ts", "start_ts", "end_ts", "duration_s", "rider_rating")
NULLABLE_EVENT_FIELDS = ("lat", "lon", "speed_kmh")

LATE_SHIFT_SECONDS_RANGE = (60, 3600)
BAD_RATING_CHOICES = (0, -1, 6, 7)


# Duplicates some trips: same data, a fresh trip_id, appended right after
# the original. Not an exact copy - a real OLTP table has a primary key on
# trip_id, so two rows sharing one would just get rejected on load, which
# isn't the duplicate-row problem this is supposed to simulate. A real
# duplicate looks like the same event recorded twice under different ids
# (a retried webhook, a re-processed message), not one row inserted twice.
# e.g. duplicate_trips(rng, trips, 0.2) on 1000 trips -> about 1200 back,
#      roughly 200 of them a copy of another trip with a new trip_id
def duplicate_trips(rng: random.Random, trips: list[Trip], rate: float) -> list[Trip]:
    next_id = max((trip.trip_id for trip in trips), default=0) + 1
    result = []
    for trip in trips:
        result.append(trip)
        if rng.random() < rate:
            result.append(replace(trip, trip_id=next_id))
            next_id += 1
    return result


# Duplicates some events the same way: same data, a fresh event_id (a new
# uuid off the rng, same as trips.new_event_id builds one), appended right
# after the original.
# e.g. duplicate_events(rng, events, 0.2) on 1000 events -> about 1200 back,
#      roughly 200 of them a copy of another event with a new event_id
def duplicate_events(
    rng: random.Random, events: list[TripEvent], rate: float
) -> list[TripEvent]:
    result = []
    for event in events:
        result.append(event)
        if rng.random() < rate:
            result.append(replace(event, event_id=new_event_id(rng)))
    return result


# Nulls out some of the given nullable fields, only on rows where the field
# currently holds a real value.
# e.g. null_out_fields(rng, trips, 0.2, NULLABLE_TRIP_FIELDS) -> the same
#      trips back, with about 20% of the previously-set accept_ts/start_ts/
#      end_ts/duration_s/rider_rating values now None
def null_out_fields(
    rng: random.Random, rows: list, rate: float, nullable_fields: tuple
) -> list:
    result = []
    for row in rows:
        changes: dict[str, None] = {}
        for field_name in nullable_fields:
            if getattr(row, field_name) is not None and rng.random() < rate:
                changes[field_name] = None
        result.append(replace(row, **changes) if changes else row)
    return result


# Shifts some events' timestamps later, simulating a late or out-of-order delivery.
# e.g. apply_late_shifts(rng, events, 0.2) -> the same events back, with
#      about 20% of them carrying an event_ts pushed 1-60 minutes later
def apply_late_shifts(
    rng: random.Random, events: list[TripEvent], rate: float
) -> list[TripEvent]:
    result = []
    for event in events:
        if rng.random() < rate:
            shift_seconds = rng.randint(*LATE_SHIFT_SECONDS_RANGE)
            event = replace(
                event, event_ts=event.event_ts + timedelta(seconds=shift_seconds)
            )
        result.append(event)
    return result


# Pushes some trips' fare_amount negative, and rider_rating outside 1-5 when set.
# e.g. push_out_of_range(rng, trips, 0.2) -> the same trips back, with about
#      20% now carrying a negative fare_amount (and a bad rider_rating, for
#      the ones that had one)
def push_out_of_range(rng: random.Random, trips: list[Trip], rate: float) -> list[Trip]:
    result = []
    for trip in trips:
        if rng.random() < rate:
            new_fare = (
                -trip.fare_amount if trip.fare_amount > 0 else trip.fare_amount - 1
            )
            new_rating = (
                rng.choice(BAD_RATING_CHOICES)
                if trip.rider_rating is not None
                else None
            )
            trip = replace(trip, fare_amount=new_fare, rider_rating=new_rating)
        result.append(trip)
    return result


# The main entry point: applies all four corruptions and returns new lists,
# leaving the clean trips and events you passed in untouched.
# e.g. corrupt(rng, trips, events, dup_rate=0.01, null_rate=0.02,
#              late_rate=0.05, out_of_range_rate=0.01)
#   -> (messy_trips, messy_events), each a bit longer or different from the
#      originals, at roughly those rates
def corrupt(
    rng: random.Random,
    trips: list[Trip],
    events: list[TripEvent],
    dup_rate: float,
    null_rate: float,
    late_rate: float,
    out_of_range_rate: float,
) -> tuple[list[Trip], list[TripEvent]]:
    messy_trips = null_out_fields(rng, trips, null_rate, NULLABLE_TRIP_FIELDS)
    messy_trips = push_out_of_range(rng, messy_trips, out_of_range_rate)
    messy_trips = duplicate_trips(rng, messy_trips, dup_rate)

    messy_events = null_out_fields(rng, events, null_rate, NULLABLE_EVENT_FIELDS)
    messy_events = apply_late_shifts(rng, messy_events, late_rate)
    messy_events = duplicate_events(rng, messy_events, dup_rate)

    return messy_trips, messy_events
