"""Builds the actor records: zones, riders, drivers, vehicles.

Everything here derives from the passed-in `rng` and `faker` — no wall-clock
reads, no unseeded randomness — so the same seed always produces the same
rows.
"""

import csv
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from faker import Faker

# Fixed so a run's synthetic "now" never depends on when it's actually run.
REFERENCE_DATE = datetime(2026, 1, 1, tzinfo=UTC)

RIDER_SIGNUP_LOOKBACK_DAYS = 730
DRIVER_ONBOARD_LOOKBACK_DAYS = 730

DRIVER_STATUSES = ("active", "inactive", "suspended")

VEHICLE_MAKES_MODELS = (
    ("Toyota", "Camry"),
    ("Toyota", "Corolla"),
    ("Honda", "Civic"),
    ("Honda", "Accord"),
    ("Ford", "Fusion"),
    ("Hyundai", "Elantra"),
    ("Nissan", "Altima"),
    ("Kia", "Optima"),
)

VEHICLE_YEAR_MIN = 2015
VEHICLE_YEAR_MAX = 2024


@dataclass
class Zone:
    zone_id: int
    borough: str
    name: str


@dataclass
class Rider:
    rider_id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    home_zone_id: int
    signup_ts: datetime


@dataclass
class Driver:
    driver_id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    license_number: str
    home_zone_id: int
    rating: float
    status: str
    onboarded_ts: datetime


@dataclass
class Vehicle:
    vehicle_id: int
    driver_id: int
    plate: str
    make: str
    model: str
    year: int


@dataclass
class Entities:
    zones: list[Zone] = field(default_factory=list)
    riders: list[Rider] = field(default_factory=list)
    drivers: list[Driver] = field(default_factory=list)
    vehicles: list[Vehicle] = field(default_factory=list)


# This is intended as an internal/helper function for this module.
def _load_zones(zones_csv: Path) -> list[Zone]:
    zones: list[Zone] = []
    with zones_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            zones.append(
                Zone(
                    zone_id=int(row["LocationID"]),
                    borough=row["Borough"],
                    name=row["Zone"],
                )
            )
    zones.sort(key=lambda zone: zone.zone_id)
    return zones


def _random_timestamp_before(
    rng: random.Random, reference: datetime, max_lookback_days: int
) -> datetime:
    offset_seconds = rng.randint(0, max_lookback_days * 24 * 60 * 60)
    return reference - timedelta(seconds=offset_seconds)


def _build_riders(
    rng: random.Random, faker: Faker, count: int, zone_ids: list[int]
) -> list[Rider]:
    riders = [
        Rider(
            rider_id=rider_id,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            email=faker.email(),
            phone=faker.phone_number(),
            home_zone_id=rng.choice(zone_ids),
            signup_ts=_random_timestamp_before(
                rng, REFERENCE_DATE, RIDER_SIGNUP_LOOKBACK_DAYS
            ),
        )
        for rider_id in range(1, count + 1)
    ]
    riders.sort(key=lambda rider: rider.rider_id)
    return riders


def _build_drivers(
    rng: random.Random, faker: Faker, count: int, zone_ids: list[int]
) -> list[Driver]:
    drivers = [
        Driver(
            driver_id=driver_id,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            email=faker.email(),
            phone=faker.phone_number(),
            license_number=faker.bothify(text="??######").upper(),
            home_zone_id=rng.choice(zone_ids),
            rating=round(rng.uniform(3.5, 5.0), 2),
            status=rng.choice(DRIVER_STATUSES),
            onboarded_ts=_random_timestamp_before(
                rng, REFERENCE_DATE, DRIVER_ONBOARD_LOOKBACK_DAYS
            ),
        )
        for driver_id in range(1, count + 1)
    ]
    drivers.sort(key=lambda driver: driver.driver_id)
    return drivers


def _build_vehicles(
    rng: random.Random, faker: Faker, drivers: list[Driver]
) -> list[Vehicle]:
    vehicles = []
    for vehicle_id, driver in enumerate(drivers, start=1):
        make, model = rng.choice(VEHICLE_MAKES_MODELS)
        vehicles.append(
            Vehicle(
                vehicle_id=vehicle_id,
                driver_id=driver.driver_id,
                plate=faker.bothify(text="???-####").upper(),
                make=make,
                model=model,
                year=rng.randint(VEHICLE_YEAR_MIN, VEHICLE_YEAR_MAX),
            )
        )
    vehicles.sort(key=lambda vehicle: vehicle.vehicle_id)
    return vehicles


# This is the public orchestration function
def build(
    rng: random.Random,
    faker: Faker,
    riders: int,
    drivers: int,
    zones_csv: Path,
) -> Entities:
    """Build zones, riders, drivers, and vehicles from one seeded rng/faker.

    Order matters for determinism: zones load first (riders/drivers sample
    from them), then riders, then drivers, then vehicles (one per driver).
    """
    zones = _load_zones(zones_csv)
    zone_ids = [zone.zone_id for zone in zones]

    built_riders = _build_riders(rng, faker, riders, zone_ids)
    built_drivers = _build_drivers(rng, faker, drivers, zone_ids)
    built_vehicles = _build_vehicles(rng, faker, built_drivers)

    return Entities(
        zones=zones,
        riders=built_riders,
        drivers=built_drivers,
        vehicles=built_vehicles,
    )
