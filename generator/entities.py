# Builds the zones, riders, drivers, and vehicles for the ride-hailing data.
#
# Everything uses the rng and faker that get passed in, nothing reads the
# clock and nothing calls random/Faker without seeding first. That's what
# makes the same seed produce the same rows every time.

import csv
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from faker import Faker

# Fixed date so the data doesn't change just because you ran it on a
# different day. Everything (signups, onboarding) is generated as some
# time before this date.
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


# e.g. Zone(zone_id=4, borough='Manhattan', name='Alphabet City')
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


# Everything build() produces, bundled together.
# e.g. Entities(zones=[Zone(...), ...], riders=[Rider(...), ...],
#               drivers=[Driver(...), ...], vehicles=[Vehicle(...), ...])
@dataclass
class Entities:
    zones: list[Zone]
    riders: list[Rider]
    drivers: list[Driver]
    vehicles: list[Vehicle]


# Reads the zones CSV into a list of Zone rows.
# e.g. load_zones(Path("generator/tests/sample/zones.csv"))
#   -> [Zone(zone_id=1, borough='EWR', name='Newark Airport'),
#       Zone(zone_id=2, borough='Queens', name='Jamaica Bay'), ...]
def load_zones(zones_csv: Path) -> list[Zone]:
    """Read the taxi zone lookup CSV into Zone rows."""
    zones = []
    with zones_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zone = Zone(
                zone_id=int(row["LocationID"]),
                borough=row["Borough"],
                name=row["Zone"],
            )
            zones.append(zone)

    zones.sort(key=lambda z: z.zone_id)
    return zones


# Picks a random timestamp somewhere in the lookback_days before reference.
# e.g. random_past_timestamp(rng, REFERENCE_DATE, 730)
#   -> a datetime value like 2025-12-12 13:45:57, somewhere in the last 2 years
def random_past_timestamp(
    rng: random.Random, reference: datetime, lookback_days: int
) -> datetime:
    """Pick a random timestamp somewhere in the lookback_days before reference."""
    max_seconds = lookback_days * 24 * 60 * 60
    seconds_back = rng.randint(0, max_seconds)
    return reference - timedelta(seconds=seconds_back)


# Builds the list of riders.
# e.g. build_riders(rng, faker, 5, [1, 2, 3, 4, 5, 6, 7, 8])
#   -> [Rider(rider_id=1, ...), Rider(rider_id=2, ...), ..., Rider(rider_id=5, ...)]
def build_riders(
    rng: random.Random, faker: Faker, count: int, zone_ids: list[int]
) -> list[Rider]:
    riders = []
    for rider_id in range(1, count + 1):
        rider = Rider(
            rider_id=rider_id,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            email=faker.email(),
            phone=faker.phone_number(),
            home_zone_id=rng.choice(zone_ids),
            signup_ts=random_past_timestamp(
                rng, REFERENCE_DATE, RIDER_SIGNUP_LOOKBACK_DAYS
            ),
        )
        riders.append(rider)

    riders.sort(key=lambda r: r.rider_id)
    return riders


# Builds the list of drivers.
# e.g. build_drivers(rng, faker, 3, [1, 2, 3, 4, 5, 6, 7, 8])
#   -> [Driver(driver_id=1, ...), Driver(driver_id=2, ...), Driver(driver_id=3, ...)]
def build_drivers(
    rng: random.Random, faker: Faker, count: int, zone_ids: list[int]
) -> list[Driver]:
    drivers = []
    for driver_id in range(1, count + 1):
        driver = Driver(
            driver_id=driver_id,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            email=faker.email(),
            phone=faker.phone_number(),
            # not a real license format, just something that looks plausible
            license_number=faker.bothify(text="??######").upper(),
            home_zone_id=rng.choice(zone_ids),
            rating=round(rng.uniform(3.5, 5.0), 2),
            status=rng.choice(DRIVER_STATUSES),
            onboarded_ts=random_past_timestamp(
                rng, REFERENCE_DATE, DRIVER_ONBOARD_LOOKBACK_DAYS
            ),
        )
        drivers.append(driver)

    drivers.sort(key=lambda d: d.driver_id)
    return drivers


# Builds one vehicle per driver.
# e.g. build_vehicles(rng, faker, [Driver(driver_id=1, ...), Driver(driver_id=2, ...)])
#   -> [Vehicle(vehicle_id=1, driver_id=1, ...), Vehicle(vehicle_id=2, driver_id=2, ...)]
def build_vehicles(
    rng: random.Random, faker: Faker, drivers: list[Driver]
) -> list[Vehicle]:
    # One vehicle per driver, in driver order.
    vehicles = []
    vehicle_id = 1
    for driver in drivers:
        make, model = rng.choice(VEHICLE_MAKES_MODELS)
        vehicle = Vehicle(
            vehicle_id=vehicle_id,
            driver_id=driver.driver_id,
            plate=faker.bothify(text="???-####").upper(),
            make=make,
            model=model,
            year=rng.randint(VEHICLE_YEAR_MIN, VEHICLE_YEAR_MAX),
        )
        vehicles.append(vehicle)
        vehicle_id += 1

    vehicles.sort(key=lambda v: v.vehicle_id)
    return vehicles


# Builds zones, riders, drivers, and vehicles together, in that order.
# e.g. build(rng, faker, riders=5, drivers=3, zones_csv=Path("generator/tests/sample/zones.csv"))
#   -> Entities(zones=[... 8 zones], riders=[... 5 riders], drivers=[... 3 drivers],
#               vehicles=[... 3 vehicles])
def build(
    rng: random.Random, faker: Faker, riders: int, drivers: int, zones_csv: Path
) -> Entities:
    """Build zones, riders, drivers, and vehicles using one seeded rng and faker.

    Order matters: zones are loaded first because riders and drivers pick a
    home zone from the list, and vehicles are built last because each one
    needs a driver to belong to.
    """
    zones = load_zones(zones_csv)
    zone_ids = [z.zone_id for z in zones]

    built_riders = build_riders(rng, faker, riders, zone_ids)
    built_drivers = build_drivers(rng, faker, drivers, zone_ids)
    built_vehicles = build_vehicles(rng, faker, built_drivers)

    return Entities(
        zones=zones,
        riders=built_riders,
        drivers=built_drivers,
        vehicles=built_vehicles,
    )
