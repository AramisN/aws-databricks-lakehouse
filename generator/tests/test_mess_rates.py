"""Tests for mess.corrupt(): does the observed corruption frequency land near
the configured rate, and does rate 0 leave the data untouched."""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from generator.mess import corrupt
from generator.trips import Trip, TripEvent

ROW_COUNT = 2000
RATE = 0.2
TOLERANCE = 0.05

BASE_TS = datetime(2026, 1, 1, tzinfo=UTC)


# Builds ROW_COUNT identical, fully-populated trips, so every nullable
# field starts out set and every trip has a positive fare to corrupt.
def _make_trips(count: int) -> list[Trip]:
    trips = []
    for trip_id in range(1, count + 1):
        trip = Trip(
            trip_id=trip_id,
            rider_id=1,
            driver_id=1,
            request_ts=BASE_TS,
            accept_ts=BASE_TS + timedelta(minutes=1),
            start_ts=BASE_TS + timedelta(minutes=5),
            end_ts=BASE_TS + timedelta(minutes=20),
            pickup_zone_id=1,
            dropoff_zone_id=2,
            distance_km=Decimal("5.00"),
            duration_s=900,
            fare_amount=Decimal("12.00"),
            currency="USD",
            status="completed",
            rider_rating=5,
        )
        trips.append(trip)
    return trips


# Builds ROW_COUNT identical, fully-populated trip events.
def _make_events(count: int) -> list[TripEvent]:
    events = []
    for i in range(1, count + 1):
        event = TripEvent(
            event_id=UUID(int=i),
            trip_id=1,
            event_type="pos_update",
            event_ts=BASE_TS + timedelta(seconds=i),
            lat=40.7,
            lon=-74.0,
            speed_kmh=25.0,
            pickup_zone_id=1,
        )
        events.append(event)
    return events


def test_zero_rate_gives_clean_data() -> None:
    trips = _make_trips(ROW_COUNT)
    events = _make_events(ROW_COUNT)
    rng = random.Random(1)

    messy_trips, messy_events = corrupt(rng, trips, events, 0.0, 0.0, 0.0, 0.0)

    assert messy_trips == trips
    assert messy_events == events


def test_dup_rate_matches_observed_frequency() -> None:
    trips = _make_trips(ROW_COUNT)
    events = _make_events(ROW_COUNT)
    rng = random.Random(2)

    messy_trips, messy_events = corrupt(rng, trips, events, RATE, 0.0, 0.0, 0.0)

    trip_dup_fraction = (len(messy_trips) - len(trips)) / len(trips)
    event_dup_fraction = (len(messy_events) - len(events)) / len(events)

    assert abs(trip_dup_fraction - RATE) < TOLERANCE
    assert abs(event_dup_fraction - RATE) < TOLERANCE


def test_null_rate_matches_observed_frequency() -> None:
    trips = _make_trips(ROW_COUNT)
    rng = random.Random(3)

    messy_trips, _ = corrupt(rng, trips, [], 0.0, RATE, 0.0, 0.0)

    # rider_rating is one of five independently-rolled nullable fields, so
    # checking it alone still gives an unbiased read on the configured rate.
    nulled = sum(1 for trip in messy_trips if trip.rider_rating is None)
    fraction = nulled / len(messy_trips)

    assert abs(fraction - RATE) < TOLERANCE


def test_late_rate_matches_observed_frequency() -> None:
    events = _make_events(ROW_COUNT)
    rng = random.Random(4)

    _, messy_events = corrupt(rng, [], events, 0.0, 0.0, RATE, 0.0)

    shifted = sum(
        1
        for original, messy in zip(events, messy_events)
        if messy.event_ts != original.event_ts
    )
    fraction = shifted / len(events)

    assert abs(fraction - RATE) < TOLERANCE


def test_out_of_range_rate_matches_observed_frequency() -> None:
    trips = _make_trips(ROW_COUNT)
    rng = random.Random(5)

    messy_trips, _ = corrupt(rng, trips, [], 0.0, 0.0, 0.0, RATE)

    negative_fares = sum(1 for trip in messy_trips if trip.fare_amount < 0)
    fraction = negative_fares / len(messy_trips)

    assert abs(fraction - RATE) < TOLERANCE
