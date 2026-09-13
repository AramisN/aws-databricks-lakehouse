import random
from pathlib import Path

import typer
from faker import Faker

from generator import entities, files, load, mess
from generator import trips as trip_gen
from generator.config import settings

app = typer.Typer()


# The "generate" CLI command: builds entities and trips, messes them up, then
# prints a summary of the final (messy) counts.
# e.g. uv run python -m generator.cli --seed 42 --riders 5 --drivers 3 --trips 4 \
#        --zones-csv generator/tests/sample/zones.csv
#   -> built 8 zones, 5 riders, 3 drivers, 3 vehicles, 4 trips, 192 trip events
#   (192 instead of the clean 190 - mess.corrupt() duplicated 2 events, at the
#   default dup_rate)
@app.command()
def generate(
    seed: int = typer.Option(settings.seed, help="Seed for the rng and Faker."),
    riders: int = typer.Option(settings.riders, help="Number of riders to generate."),
    drivers: int = typer.Option(
        settings.drivers, help="Number of drivers to generate."
    ),
    trips: int = typer.Option(settings.trips, help="Number of trips to generate."),
    dup_rate: float = typer.Option(
        settings.dup_rate, help="Fraction of rows duplicated."
    ),
    null_rate: float = typer.Option(
        settings.null_rate, help="Fraction of fields nulled out."
    ),
    late_rate: float = typer.Option(
        settings.late_rate, help="Fraction of events delivered late."
    ),
    out_of_range_rate: float = typer.Option(
        settings.out_of_range_rate, help="Fraction of values pushed out of range."
    ),
    target: str = typer.Option(
        settings.target, help="Where to write the generated data."
    ),
    zones_csv: Path = typer.Option(
        settings.zones_csv, help="Path to the taxi zone lookup CSV."
    ),
) -> None:
    """Generate the ride-hailing domain and load it into `target`."""
    rng = random.Random(seed)
    faker = Faker()
    faker.seed_instance(seed)

    result = entities.build(rng, faker, riders, drivers, zones_csv)
    trip_list, trip_events = trip_gen.build(rng, trips, result)
    messy_trips, messy_events = mess.corrupt(
        rng, trip_list, trip_events, dup_rate, null_rate, late_rate, out_of_range_rate
    )

    summary = (
        f"built {len(result.zones)} zones, {len(result.riders)} riders, "
        f"{len(result.drivers)} drivers, {len(result.vehicles)} vehicles, "
        f"{len(messy_trips)} trips, {len(messy_events)} trip events"
    )

    if target == "postgres":
        load.write(result, messy_trips, messy_events)
        summary += ", loaded into postgres"
    elif target == "files":
        files.write(messy_events)
        summary += f", events written to {files.DEFAULT_EVENTS_PATH}"

    typer.echo(summary)


if __name__ == "__main__":
    app()
