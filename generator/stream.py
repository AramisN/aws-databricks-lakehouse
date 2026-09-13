# Sends the NDJSON events file to the Kinesis stream from
# infra/terraform/streaming (ADR-0009). This never regenerates anything,
# it only reads data/events.ndjson, the same file --target files writes.
# That's the whole reason that target exists, it decouples streaming from
# generation. The producer can be re-run against the same events with a
# different partition key without touching the generator at all.
#
# put_records has three real limits this has to respect, 500 records a
# call, 5 MB a call, 1 MB a record. It can also return 200 at the HTTP
# level with some records failed, FailedRecordCount in the response, not
# an exception. A producer that only checks the HTTP status silently
# drops data. This resends the failed ones with backoff until they land
# or the retries run out.

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import boto3
from mypy_boto3_kinesis.client import KinesisClient
from mypy_boto3_kinesis.type_defs import PutRecordsRequestEntryTypeDef

MAX_RECORDS_PER_CALL = 500
MAX_BYTES_PER_CALL = 5 * 1024 * 1024
MAX_BYTES_PER_RECORD = 1024 * 1024

DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_BASE_SECONDS = 1.0


# Reads the NDJSON file one line at a time instead of loading it all into
# a list first, so a multi-million-line file doesn't have to fit in
# memory just to be streamed.
# e.g. list(read_events(Path("data/events.ndjson")))
#   -> [{"event_id": "998d48a9-...", "trip_id": 1, ..., "pickup_zone_id": 6}, ...]
def read_events(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


# Turns one event into the shape put_records wants, the raw bytes to
# send and the partition key pulled out of whichever field the caller
# picked. Which field actually spreads or concentrates load depends on
# how skewed its real values are, trip_id is close to unique per event
# so it spreads evenly, event_type concentrates hard since pos_update
# dominates real volume.
# e.g. to_kinesis_record({"trip_id": 1, "pickup_zone_id": 6, ...}, "trip_id")
#   -> {"Data": b'{"trip_id": 1, ...}', "PartitionKey": "1"}
def to_kinesis_record(
    event: dict[str, Any], partition_key_field: str
) -> PutRecordsRequestEntryTypeDef:
    return {
        "Data": json.dumps(event).encode("utf-8"),
        "PartitionKey": str(event[partition_key_field]),
    }


# Kinesis counts the partition key's own bytes against both the
# per-record and per-call limits, not just the data payload. Data is
# always bytes here. to_kinesis_record is the only thing that builds
# these records, and it always encodes to bytes rather than a file-like
# object.
def _record_size(record: PutRecordsRequestEntryTypeDef) -> int:
    data = record["Data"]
    assert isinstance(data, bytes)
    return len(data) + len(record["PartitionKey"].encode("utf-8"))


# The shared batching logic, working off an iterator instead of a list so
# a multi-million-record run never has to hold more than one batch in
# memory. A record over 1 MB on its own is a hard error, not something a
# smaller batch could ever fix. That one raises instead of getting
# silently dropped into a batch of its own.
def _batch_records(
    records: Iterator[PutRecordsRequestEntryTypeDef],
) -> Iterator[list[PutRecordsRequestEntryTypeDef]]:
    current: list[PutRecordsRequestEntryTypeDef] = []
    current_size = 0

    for record in records:
        size = _record_size(record)
        if size > MAX_BYTES_PER_RECORD:
            raise ValueError(
                f"record for partition key {record['PartitionKey']!r} is {size} "
                "bytes, over the 1 MB Kinesis limit"
            )

        over_count = len(current) >= MAX_RECORDS_PER_CALL
        over_size = current_size + size > MAX_BYTES_PER_CALL
        if current and (over_count or over_size):
            yield current
            current = []
            current_size = 0

        current.append(record)
        current_size += size

    if current:
        yield current


# Splits records into batches that fit put_records' real limits. Takes
# and returns plain lists, this is the one to reach for in a test or
# anywhere the records already fit comfortably in memory; send() below
# uses _batch_records directly on a generator instead, for the case
# where they don't.
# e.g. chunk_records([record] * 1200) -> [ [500 records], [500 records], [200 records] ]
def chunk_records(
    records: list[PutRecordsRequestEntryTypeDef],
) -> list[list[PutRecordsRequestEntryTypeDef]]:
    return list(_batch_records(iter(records)))


# Sends one batch (already <=500 records) and retries only the records
# that individually failed, with exponential backoff between attempts.
# put_records can come back with FailedRecordCount > 0 even at a 200, so
# checking that field matters more than the HTTP status. Returns how
# many records were still failing once max_retries ran out, 0 on a clean
# send.
# on_attempt(attempt_number, records_in_attempt, failed_count) fires
# after every raw put_records call, successful or not. A caller can
# watch FailedRecordCount happen live instead of only seeing the final
# tally.
def put_records_with_retry(
    client: KinesisClient,
    stream_name: str,
    records: list[PutRecordsRequestEntryTypeDef],
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    on_attempt: Callable[[int, int, int], None] = lambda *_: None,
) -> int:
    pending = records
    for attempt in range(max_retries + 1):
        response = client.put_records(StreamName=stream_name, Records=pending)
        failed_count = response["FailedRecordCount"]
        on_attempt(attempt + 1, len(pending), failed_count)
        if failed_count == 0:
            return 0

        # Records and results line up by index; a failed one carries an
        # ErrorCode, a succeeded one carries a SequenceNumber instead.
        pending = [
            record
            for record, result in zip(pending, response["Records"], strict=True)
            if "ErrorCode" in result
        ]
        if attempt < max_retries:
            sleep(backoff_base_seconds * (2**attempt))

    return len(pending)


# This is the entry point. It reads events.ndjson and puts every event
# on the stream, batched and with partial-failure retry. Auth comes from
# boto3's default credential chain, the lakehouse profile. That's the
# same as every other AWS call in this repo, nothing hardcoded here.
#
# Everything from the file read down to _batch_records is lazy, a batch
# gets built and sent as soon as it's full instead of reading the whole
# file into memory first and only then sending anything. For a
# multi-million-line file that first pass alone can take minutes with
# nothing to show for it, which looks exactly like the producer hanging.
#
# on_batch(batch_number, records_in_batch, failed_in_batch) fires after
# every batch's retries are done. on_attempt (see put_records_with_retry)
# fires after every individual put_records call, so a caller can print
# progress instead of waiting in silence.
# e.g. send(Path("data/events.ndjson"), "adl-dev-trip-events", "eu-central-1", "trip_id")
#   -> {"sent": 4093, "batches": 9}
def send(
    events_path: Path,
    stream_name: str,
    region: str,
    partition_key_field: str,
    client: KinesisClient | None = None,
    on_batch: Callable[[int, int, int], None] = lambda *_: None,
    on_attempt: Callable[[int, int, int], None] = lambda *_: None,
) -> dict[str, int]:
    if client is None:
        client = boto3.client("kinesis", region_name=region)

    records = (
        to_kinesis_record(event, partition_key_field)
        for event in read_events(events_path)
    )

    sent = 0
    permanently_failed = 0
    batch_number = 0
    for batch in _batch_records(records):
        batch_number += 1
        failed = put_records_with_retry(
            client, stream_name, batch, on_attempt=on_attempt
        )
        sent += len(batch)
        permanently_failed += failed
        on_batch(batch_number, len(batch), failed)

    if permanently_failed:
        raise RuntimeError(
            f"{permanently_failed} of {sent} events never made it to "
            f"{stream_name} after retries"
        )

    return {"sent": sent, "batches": batch_number}
