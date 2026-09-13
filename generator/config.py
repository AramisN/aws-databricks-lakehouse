from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# All the generator's settings, overridable via GENERATOR_ env vars or a .env file.
# e.g. GENERATOR_RIDERS=50 GENERATOR_SEED=7 uv run python -m generator.cli
#   -> Settings(seed=7, riders=50, drivers=200, trips=10_000, ...) instead of the defaults below
class Settings(BaseSettings):
    # extra="ignore": .env is shared with DBSettings below, so this class
    # has to ignore the POSTGRES_* keys in it rather than reject them -
    # pydantic-settings reads the whole .env file regardless of env_prefix,
    # and its default is to error on any key that isn't one of its own.
    model_config = SettingsConfigDict(
        env_prefix="GENERATOR_", env_file=".env", extra="ignore"
    )

    seed: int = 42

    riders: int = 1_000
    drivers: int = 200
    trips: int = 10_000

    zones_csv: Path = Path("data/reference/taxi_zone_lookup.csv")
    dup_rate: float = 0.01
    null_rate: float = 0.02
    late_rate: float = 0.05
    out_of_range_rate: float = 0.01

    target: str = "postgres"

    # Only used by --target kinesis. Defaults match what
    # infra/terraform/streaming actually creates (ADR-0009), so a plain
    # `rides-generate --target kinesis` works with no flags once that
    # stack is applied. partition_key_field picks which field on each
    # event becomes the Kinesis partition key, trip_id is close to
    # uniform since it's unique per trip. event_type concentrates load
    # instead, since pos_update dominates real event volume. That's the
    # one that actually forces a hot shard.
    stream_name: str = "adl-dev-trip-events"
    stream_region: str = "eu-central-1"
    partition_key_field: str = "trip_id"


settings = Settings()


# The Postgres connection settings. Kept separate from Settings above and
# unprefixed, on purpose: POSTGRES_USER/PASSWORD/DB are the same env vars
# compose.yaml passes to the db service itself, so the generator and the
# container it's talking to have to agree on the same names, not a
# GENERATOR_-prefixed duplicate of them.
# e.g. with POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres
#      POSTGRES_DB=rideshare set (from .env) -> DBSettings(host='localhost',
#      port=5432, user='postgres', password='postgres', db='rideshare')
class DBSettings(BaseSettings):
    # extra="ignore" for the same reason as Settings above: this file is
    # shared, so GENERATOR_* keys in it have to be ignored here too.
    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_", env_file=".env", extra="ignore"
    )

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    db: str = "rideshare"


db_settings = DBSettings()
