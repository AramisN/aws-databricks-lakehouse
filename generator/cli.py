import random
from pathlib import Path

import typer
from faker import Faker

from generator import entities, files, load, mess, stream
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
        settings.target,
        help="Where the data goes, postgres, files, or kinesis, which "
        "streams the existing events.ndjson instead of regenerating it.",
    ),
    zones_csv: Path = typer.Option(
        settings.zones_csv, help="Path to the taxi zone lookup CSV."
    ),
    partition_key: str = typer.Option(
        settings.partition_key_field,
        "--partition-key",
        help="Only used by --target kinesis. Field to partition records "
        "on, trip_id spreads evenly, event_type forces a hot shard "
        "since pos_update dominates.",
    ),
) -> None:
    """Generate the ride-hailing domain and load it into `target`."""
    # kinesis never regenerates anything, it only sends the NDJSON file
    # --target files already wrote. It skips the build pipeline below
    # entirely and goes straight to stream.py.
    if target == "kinesis":
        sent_so_far = {"count": 0}

        # Only worth a line when FailedRecordCount is actually nonzero.
        # This is the throughput-exceeded exercise happening live, not
        # routine noise.
        def _on_attempt(attempt: int, count: int, failed: int) -> None:
            if failed:
                typer.echo(
                    f"  put_records attempt {attempt}: {failed}/{count} records "
                    "failed (FailedRecordCount), retrying"
                )

        # A running total every 20 batches, so a multi-million-record run
        # shows it's actually moving instead of going quiet for minutes.
        def _on_batch(batch_number: int, count: int, failed: int) -> None:
            sent_so_far["count"] += count
            if batch_number % 20 == 0:
                typer.echo(
                    f"batch {batch_number}: {sent_so_far['count']} events sent so far"
                )

        result_summary = stream.send(
            files.DEFAULT_EVENTS_PATH,
            settings.stream_name,
            settings.stream_region,
            partition_key,
            on_batch=_on_batch,
            on_attempt=_on_attempt,
        )
        typer.echo(
            f"sent {result_summary['sent']} events from {files.DEFAULT_EVENTS_PATH} "
            f"to {settings.stream_name} in {result_summary['batches']} batches, "
            f"partitioned on {partition_key}"
        )
        return

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
