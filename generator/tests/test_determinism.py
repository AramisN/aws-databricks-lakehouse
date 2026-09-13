"""Proves entities.build() is deterministic, seed-sensitive, and referentially intact."""

import random
from pathlib import Path

from faker import Faker

from generator.entities import Entities, build

ZONES_CSV = Path(__file__).parent / "sample" / "zones.csv"

RIDERS = 50
DRIVERS = 10


# Builds one Entities result for a given seed, so each test is just its assertion.
# e.g. _build(42) -> Entities(zones=[... 8 zones], riders=[... 50 riders],
#                              drivers=[... 10 drivers], vehicles=[... 10 vehicles])
def _build(seed: int) -> Entities:
    rng = random.Random(seed)
    faker = Faker()
    faker.seed_instance(seed)
    return build(rng, faker, riders=RIDERS, drivers=DRIVERS, zones_csv=ZONES_CSV)


# Same seed, twice, should give back identical entities.
def test_same_seed_is_identical() -> None:
    first = _build(42)
    second = _build(42)
    assert first == second


# Different seeds should give back different entities.
def test_different_seed_differs() -> None:
    a = _build(42)
    b = _build(99)
    assert a != b


# Every rider/driver home_zone_id and vehicle driver_id should point at a real row.
def test_foreign_keys_resolve() -> None:
    result = _build(42)

    zone_ids = {zone.zone_id for zone in result.zones}
    driver_ids = {driver.driver_id for driver in result.drivers}

    assert all(rider.home_zone_id in zone_ids for rider in result.riders)
    assert all(driver.home_zone_id in zone_ids for driver in result.drivers)
    assert all(vehicle.driver_id in driver_ids for vehicle in result.vehicles)
