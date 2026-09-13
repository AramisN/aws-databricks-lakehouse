# Writes trip_events out as NDJSON, one JSON object per line - the local
# stand-in for Kinesis before that actually exists (ADR-0009). Nothing else
# gets written here: zones/riders/drivers/vehicles/trips are the OLTP side
# and only ever go to Postgres (ADR-0008, load.py); --target files only
# changes where the events end up.

import json
from dataclasses import asdict
from pathlib import Path

from generator.trips import TripEvent

DEFAULT_EVENTS_PATH = Path("data/events.ndjson")


# Turns one event into a JSON line. dataclasses.asdict() doesn't know how
# to serialize the UUID or the datetime, so those two get converted by hand
# first.
# e.g. _event_to_json_line(event) -> '{"event_id": "998d48a9-...", "trip_id": 1,
#      "event_type": "requested", "event_ts": "2025-10-24T14:13:44+00:00",
#      "lat": 40.6037, "lon": -74.2348, "speed_kmh": null}'
def _event_to_json_line(event: TripEvent) -> str:
    row = asdict(event)
    row["event_id"] = str(event.event_id)
    row["event_ts"] = event.event_ts.isoformat()
    return json.dumps(row)


# Writes every event as one NDJSON line, in the order given. Overwrites
# whatever was already at path - same "regenerate from the same seed, get
# the same output back" idea as load.py's truncate-then-load.
# e.g. write(messy_events) -> data/events.ndjson, one JSON object per line,
#      4093 lines for 4093 events
def write(events: list[TripEvent], path: Path = DEFAULT_EVENTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(_event_to_json_line(event))
            f.write("\n")
