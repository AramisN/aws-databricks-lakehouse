from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GENERATOR_", env_file=".env")

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


settings = Settings()
