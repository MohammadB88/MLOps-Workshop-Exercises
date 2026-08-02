"""Bronze archive tests: immutability, idempotency, metadata sidecars."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rivercast.config import load_config
from rivercast.contracts.raw import RawFetch, RawFetchMetadata
from rivercast.ingest import ingest_window
from rivercast.sources import FixtureGaugeSource
from rivercast.storage import LocalObjectStore, RawArchive

KAUB_UUID = "1d26e504-7f9e-480a-b52c-5932be6549ab"
WINDOW = (
    datetime(2024, 8, 1, tzinfo=UTC),
    datetime(2024, 8, 2, tzinfo=UTC),
)


@pytest.fixture()
def zones(configs_dir: Path):
    return load_config(configs_dir / "local.yaml").storage.zones


@pytest.fixture()
def store(tmp_path: Path) -> LocalObjectStore:
    return LocalObjectStore(tmp_path / "artifacts")


@pytest.fixture()
def archive(store: LocalObjectStore, zones) -> RawArchive:
    return RawArchive(store, zones)


def _fetch(payload: bytes, fetched_at: str = "2024-08-02T00:00:00+00:00") -> RawFetch:
    return RawFetch(
        payload=payload,
        metadata=RawFetchMetadata(
            source="fixture",
            station_uuid=KAUB_UUID,
            parameter="W",
            requested_start="2024-08-01T00:00:00+00:00",
            requested_end="2024-08-02T00:00:00+00:00",
            fetched_at_utc=fetched_at,
            http_status=200,
            sha256=hashlib.sha256(payload).hexdigest(),
        ),
    )


def test_store_writes_payload_and_metadata_in_plan_layout(
    archive: RawArchive, store: LocalObjectStore
) -> None:
    result = archive.store(_fetch(b"[]"))
    assert result.created
    assert result.key.startswith(
        f"bronze/source=fixture/parameter=W/station_uuid={KAUB_UUID}/event_date=2024-08-01/"
    )
    assert "fetched_at=20240802T000000Z-" in result.key
    assert ":" not in result.key  # object keys must stay filesystem-safe

    metadata = json.loads(store.get_bytes(result.metadata_key))
    for field in (
        "source",
        "station_uuid",
        "parameter",
        "requested_start",
        "requested_end",
        "fetched_at_utc",
        "http_status",
        "etag",
        "sha256",
        "code_commit",
    ):
        assert field in metadata, field


def test_identical_payload_is_not_duplicated(archive: RawArchive, store: LocalObjectStore) -> None:
    first = archive.store(_fetch(b'[{"timestamp": "2024-08-01T02:00:00+02:00", "value": 1.0}]'))
    second = archive.store(
        _fetch(
            b'[{"timestamp": "2024-08-01T02:00:00+02:00", "value": 1.0}]',
            fetched_at="2024-08-02T06:00:00+00:00",  # later re-fetch, same content
        )
    )
    assert first.created and not second.created
    assert second.key == first.key
    payload_keys = [k for k in store.list_keys() if k.endswith(".json") and ".meta" not in k]
    assert len(payload_keys) == 1


def test_changed_payload_appends_never_overwrites(
    archive: RawArchive, store: LocalObjectStore
) -> None:
    first = archive.store(_fetch(b'[{"timestamp": "2024-08-01T02:00:00+02:00", "value": 1.0}]'))
    revised = archive.store(
        _fetch(
            b'[{"timestamp": "2024-08-01T02:00:00+02:00", "value": 2.0}]',
            fetched_at="2024-08-02T06:00:00+00:00",
        )
    )
    assert revised.created
    assert revised.key != first.key
    # Both revisions of history remain readable.
    assert store.get_bytes(first.key) != store.get_bytes(revised.key)


def test_ingest_window_happy_path(archive: RawArchive, lab_root: Path) -> None:
    source = FixtureGaugeSource(lab_root / "data_fixtures" / "pegelonline")
    outcome = ingest_window(source, archive, KAUB_UUID, "W", *WINDOW)
    assert outcome.parsed_ok
    assert outcome.archive_created
    assert len(outcome.measurements) == 96
    assert outcome.error is None

    # Re-running the same fetch is a no-op at the archive level: same content,
    # no duplicate raw object, identical parsed records.
    repeat = ingest_window(source, archive, KAUB_UUID, "W", *WINDOW)
    assert not repeat.archive_created
    assert repeat.archived_key == outcome.archived_key
    assert repeat.measurements == outcome.measurements


def test_ingest_archives_malformed_payload_without_promoting(
    archive: RawArchive, store: LocalObjectStore
) -> None:
    class BrokenSource:
        def list_stations(self, water: str):  # pragma: no cover - protocol filler
            return []

        def fetch_raw(self, station_uuid, parameter, start, end):
            return _fetch(b"<html>maintenance page</html>")

    outcome = ingest_window(BrokenSource(), archive, KAUB_UUID, "W", *WINDOW)
    assert not outcome.parsed_ok
    assert outcome.measurements == []
    assert outcome.error is not None and "not valid JSON" in outcome.error
    # The bad payload is preserved verbatim for diagnosis.
    assert store.get_bytes(outcome.archived_key) == b"<html>maintenance page</html>"
