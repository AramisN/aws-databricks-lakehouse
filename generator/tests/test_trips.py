"""Tests for trips.build(): determinism and the per-trip state walk."""

import random
from pathlib import Path

from faker import Faker

from generator.entities import build as build_entities
from generator.trips import build as build_trips

ZONES_CSV = Path(__file__).parent / "sample" / "zones.csv"

RIDERS = 20
DRIVERS = 10
TRIPS = 50


# Builds one set of entities and trips for a given seed.
# e.g. _build(42) -> ([Trip(trip_id=1, ...), ... 50 trips], [TripEvent(...), ... events])
def _build(seed: int):
    rng = random.Random(seed)
    faker = Faker()
    faker.seed_instance(seed)
    entities = build_entities(
        rng, faker, riders=RIDERS, drivers=DRIVERS, zones_csv=ZONES_CSV
    )
    trips, events = build_trips(rng, TRIPS, entities)
    return trips, events


# Same seed, twice, should give back identical trips and events.
def test_same_seed_is_identical() -> None:
    trips_a, events_a = _build(42)
    trips_b, events_b = _build(42)
    assert trips_a == trips_b
    assert events_a == events_b


# Different seeds should give back different trips.
def test_different_seed_differs() -> None:
    trips_a, _ = _build(42)
    trips_b, _ = _build(99)
    assert trips_a != trips_b


# A completed trip's four timestamps should each come after the last.
def test_completed_trip_timestamps_move_forward() -> None:
    trips, _ = _build(42)
    completed = [t for t in trips if t.status == "completed"]
    assert completed, "expected at least one completed trip in this run"

    for trip in completed:
        assert trip.request_ts < trip.accept_ts
        assert trip.accept_ts < trip.start_ts
        assert trip.start_ts < trip.end_ts


# A cancelled trip should have no start_ts, no end_ts, and no completed event.
def test_cancelled_trip_has_no_start_end_or_completed_event() -> None:
    trips, events = _build(42)
    cancelled = [t for t in trips if t.status == "cancelled"]
    assert cancelled, "expected at least one cancelled trip in this run"

    for trip in cancelled:
        assert trip.start_ts is None
        assert trip.end_ts is None

    cancelled_ids = {t.trip_id for t in cancelled}
    for event in events:
        if event.trip_id in cancelled_ids:
            assert event.event_type != "completed"


# A completed trip should have request_ts, accept_ts, start_ts, and end_ts all set.
def test_completed_trip_has_all_four_timestamps() -> None:
    trips, _ = _build(42)
    completed = [t for t in trips if t.status == "completed"]
    assert completed, "expected at least one completed trip in this run"

    for trip in completed:
        assert trip.request_ts is not None
        assert trip.accept_ts is not None
        assert trip.start_ts is not None
        assert trip.end_ts is not None


# Every event's trip_id should point at a trip that actually exists.
def test_event_trip_ids_are_real() -> None:
    trips, events = _build(42)
    trip_ids = {t.trip_id for t in trips}
    assert all(event.trip_id in trip_ids for event in events)
