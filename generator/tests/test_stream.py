"""Tests for stream.py's batching and partial-failure retry. No real AWS
call here, that part gets proved manually, this is the logic that's
actually worth a test: does chunk_records respect put_records' real
limits, and does put_records_with_retry resend only the records that
failed instead of the whole batch."""

from typing import Any, cast

import pytest
from mypy_boto3_kinesis.client import KinesisClient
from mypy_boto3_kinesis.type_defs import PutRecordsRequestEntryTypeDef

from generator.stream import chunk_records, put_records_with_retry


# A record small enough that only the 500-count limit ever kicks in, not
# the 5 MB one.
def _small_record(i: int) -> PutRecordsRequestEntryTypeDef:
    return {"Data": b"x", "PartitionKey": str(i)}


# A stand-in for boto3's Kinesis client. Takes one canned response per
# call, in order, and remembers what it was sent so a test can check
# that a retry resent only the records that failed. It only needs to
# match put_records, not the whole real client, so it's cast to
# KinesisClient at the call site rather than implementing everything
# that Protocol has.
class _StubKinesisClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls: list[list[PutRecordsRequestEntryTypeDef]] = []

    def put_records(
        self, StreamName: str, Records: list[PutRecordsRequestEntryTypeDef]
    ) -> dict[str, Any]:
        self.calls.append(Records)
        return self._responses.pop(0)


def test_chunk_records_splits_at_500_boundary() -> None:
    records = [_small_record(i) for i in range(1200)]
    batches = chunk_records(records)
    assert [len(batch) for batch in batches] == [500, 500, 200]


def test_chunk_records_splits_on_5mb_before_500_records() -> None:
    # 700 KB a record: 7 fit under the 5 MB cap, an 8th would push a call
    # over it, so the count limit never becomes the reason to split here.
    big_record: PutRecordsRequestEntryTypeDef = {
        "Data": b"x" * 700_000,
        "PartitionKey": "1",
    }
    records = [big_record] * 10

    batches = chunk_records(records)
    assert [len(batch) for batch in batches] == [7, 3]


def test_chunk_records_rejects_a_record_over_1mb() -> None:
    oversized: PutRecordsRequestEntryTypeDef = {
        "Data": b"x" * (1024 * 1024 + 1),
        "PartitionKey": "1",
    }
    with pytest.raises(ValueError, match="1 MB"):
        chunk_records([oversized])


def test_chunk_records_empty_input_gives_no_batches() -> None:
    assert chunk_records([]) == []


def test_put_records_with_retry_resends_only_the_failed_records() -> None:
    records = [_small_record(i) for i in range(3)]

    first_response = {
        "FailedRecordCount": 1,
        "Records": [
            {"SequenceNumber": "1", "ShardId": "shard-1"},
            {
                "ErrorCode": "ProvisionedThroughputExceededException",
                "ErrorMessage": "x",
            },
            {"SequenceNumber": "3", "ShardId": "shard-1"},
        ],
    }
    second_response = {
        "FailedRecordCount": 0,
        "Records": [{"SequenceNumber": "2", "ShardId": "shard-1"}],
    }
    client = _StubKinesisClient([first_response, second_response])
    sleeps: list[float] = []

    failed_count = put_records_with_retry(
        cast(KinesisClient, client), "adl-dev-trip-events", records, sleep=sleeps.append
    )

    assert failed_count == 0
    # First call sent all three; the retry sent only record index 1, the
    # one whose result carried an ErrorCode.
    assert client.calls == [records, [records[1]]]
    assert sleeps == [1.0]


def test_put_records_with_retry_gives_up_after_max_retries() -> None:
    records = [_small_record(0)]
    always_fails = {
        "FailedRecordCount": 1,
        "Records": [{"ErrorCode": "InternalFailure", "ErrorMessage": "x"}],
    }
    client = _StubKinesisClient([always_fails] * 3)

    failed_count = put_records_with_retry(
        cast(KinesisClient, client),
        "adl-dev-trip-events",
        records,
        max_retries=2,
        sleep=lambda _: None,
    )

    # Sent once, then retried twice, then gave up: 3 calls, 1 still failed.
    assert len(client.calls) == 3
    assert failed_count == 1


def test_put_records_with_retry_clean_send_needs_no_retry() -> None:
    records = [_small_record(i) for i in range(2)]
    clean_response = {
        "FailedRecordCount": 0,
        "Records": [
            {"SequenceNumber": "1", "ShardId": "shard-1"},
            {"SequenceNumber": "2", "ShardId": "shard-1"},
        ],
    }
    client = _StubKinesisClient([clean_response])

    failed_count = put_records_with_retry(
        cast(KinesisClient, client),
        "adl-dev-trip-events",
        records,
        sleep=lambda _: None,
    )

    assert failed_count == 0
    assert len(client.calls) == 1
