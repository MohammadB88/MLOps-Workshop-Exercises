"""Adapter unit tests — zero network access (rule 3); HTTP via fake transports."""

import json
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rivercast.config import load_config
from rivercast.contracts.raw import RawFetch, RawFetchMetadata
from rivercast.sources import (
    FixtureGaugeSource,
    MalformedResponseError,
    PegelOnlineSource,
    SourceError,
    SourceTimeoutError,
    parse_measurements,
)
from rivercast.sources.pegelonline import HttpResponse

KAUB_UUID = "1d26e504-7f9e-480a-b52c-5932be6549ab"
WINDOW = (
    datetime(2024, 8, 1, tzinfo=UTC),
    datetime(2024, 8, 2, tzinfo=UTC),
)


@pytest.fixture()
def source_config(configs_dir: Path):
    config = load_config(configs_dir / "local.yaml")
    # Retries must not sleep for real in unit tests.
    return config.source.model_copy(
        update={
            "retry": config.source.retry.model_copy(
                update={"backoff_initial_seconds": 0.001, "backoff_max_seconds": 0.002}
            )
        }
    )


def _fetch(payload: bytes, source: str = "test") -> RawFetch:
    import hashlib

    return RawFetch(
        payload=payload,
        metadata=RawFetchMetadata(
            source=source,
            station_uuid=KAUB_UUID,
            parameter="W",
            requested_start="2024-08-01T00:00:00+00:00",
            requested_end="2024-08-02T00:00:00+00:00",
            fetched_at_utc="2024-08-02T00:00:00+00:00",
            http_status=200,
            sha256=hashlib.sha256(payload).hexdigest(),
        ),
    )


# -- shared parser ---------------------------------------------------------


def test_parse_measurements_valid_payload() -> None:
    payload = json.dumps(
        [
            {"timestamp": "2024-08-01T02:00:00+02:00", "value": 101.0},
            {"timestamp": "2024-08-01T02:15:00+02:00", "value": 102.5},
        ]
    ).encode()
    measurements = parse_measurements(_fetch(payload))
    assert len(measurements) == 2
    assert measurements[0].timestamp_raw == "2024-08-01T02:00:00+02:00"
    assert measurements[0].timestamp_utc == datetime(2024, 8, 1, 0, 0, tzinfo=UTC)
    assert measurements[0].station_uuid == KAUB_UUID
    assert measurements[1].value == 102.5


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (b"this is not json {", "not valid JSON"),
        (b'{"rows": []}', "not a JSON array"),
        (b'[{"value": 1.0}]', "lacks timestamp/value"),
        (b'[{"timestamp": "yesterday", "value": 1.0}]', "unparseable timestamp"),
        (b'[{"timestamp": "2024-08-01T02:00:00", "value": 1.0}]', "no UTC offset"),
        (b'[{"timestamp": "2024-08-01T02:00:00+02:00", "value": "high"}]', "invalid measurement"),
    ],
)
def test_parse_measurements_rejects_malformed(payload: bytes, match: str) -> None:
    with pytest.raises(MalformedResponseError, match=match):
        parse_measurements(_fetch(payload))


# -- live adapter (fake transport) -----------------------------------------


def _ok(body: bytes, headers: dict[str, str] | None = None) -> HttpResponse:
    return HttpResponse(status=200, headers=headers or {}, body=body)


def test_pegelonline_retries_then_succeeds(source_config) -> None:
    calls = []

    def transport(url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.URLError(TimeoutError("simulated timeout"))
        return _ok(b"[]", {"etag": '"abc123"'})

    source = PegelOnlineSource(source_config, transport=transport)
    fetch = source.fetch_raw(KAUB_UUID, "W", *WINDOW)
    assert len(calls) == 3
    assert fetch.metadata.http_status == 200
    assert fetch.metadata.etag == '"abc123"'
    assert fetch.metadata.source == "pegelonline-rest-v2"


def test_pegelonline_timeout_fails_cleanly_after_max_attempts(source_config) -> None:
    calls = []

    def transport(url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        calls.append(url)
        raise TimeoutError("simulated timeout")

    source = PegelOnlineSource(source_config, transport=transport)
    with pytest.raises(SourceTimeoutError, match="failed after 4 attempts"):
        source.fetch_raw(KAUB_UUID, "W", *WINDOW)
    assert len(calls) == source_config.retry.max_attempts


def test_pegelonline_does_not_retry_client_errors(source_config) -> None:
    calls = []

    def transport(url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        calls.append(url)
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]

    source = PegelOnlineSource(source_config, transport=transport)
    with pytest.raises(SourceError, match="HTTP 404"):
        source.fetch_raw(KAUB_UUID, "W", *WINDOW)
    assert len(calls) == 1


def test_pegelonline_requires_aware_datetimes(source_config) -> None:
    source = PegelOnlineSource(source_config, transport=lambda u, h, t: _ok(b"[]"))
    with pytest.raises(SourceError, match="timezone-aware"):
        source.fetch_raw(KAUB_UUID, "W", datetime(2024, 8, 1), WINDOW[1])


def test_pegelonline_metadata_records_request(source_config) -> None:
    source = PegelOnlineSource(source_config, transport=lambda u, h, t: _ok(b"[]"))
    fetch = source.fetch_raw(KAUB_UUID, "W", *WINDOW)
    meta = fetch.metadata
    assert meta.requested_start == "2024-08-01T00:00:00+00:00"
    assert meta.requested_end == "2024-08-02T00:00:00+00:00"
    assert meta.station_uuid == KAUB_UUID
    assert len(meta.sha256) == 64


def test_pegelonline_list_stations_parses_entries(source_config) -> None:
    body = json.dumps(
        [
            {
                "uuid": KAUB_UUID,
                "number": "25700100",
                "shortname": "KAUB",
                "km": 546.23,
                "agency": "STANDORT BINGEN",
                "water": {"shortname": "RHEIN"},
            }
        ]
    ).encode()
    source = PegelOnlineSource(source_config, transport=lambda u, h, t: _ok(body))
    stations = source.list_stations("RHEIN")
    assert len(stations) == 1
    assert stations[0].uuid == KAUB_UUID
    assert stations[0].water == "RHEIN"
    assert stations[0].km == 546.23


# -- fixture adapter --------------------------------------------------------


@pytest.fixture()
def fixture_source(lab_root: Path) -> FixtureGaugeSource:
    return FixtureGaugeSource(lab_root / "data_fixtures" / "pegelonline")


def test_fixture_list_stations_contains_corridor(fixture_source: FixtureGaugeSource) -> None:
    names = {s.shortname for s in fixture_source.list_stations("RHEIN")}
    assert {"MAINZ", "OESTRICH", "BINGEN", "KAUB"} <= names


def test_fixture_fetch_filters_window_and_is_deterministic(
    fixture_source: FixtureGaugeSource,
) -> None:
    first = fixture_source.fetch_raw(KAUB_UUID, "W", *WINDOW)
    second = fixture_source.fetch_raw(KAUB_UUID, "W", *WINDOW)
    assert first.payload == second.payload
    assert first.metadata.sha256 == second.metadata.sha256
    assert first.metadata.fetched_at_utc == second.metadata.fetched_at_utc

    measurements = parse_measurements(first)
    assert len(measurements) == 96  # one UTC day on a 15-minute grid
    assert all(WINDOW[0] <= m.timestamp_utc < WINDOW[1] for m in measurements)


def test_fixture_unknown_station_raises(fixture_source: FixtureGaugeSource) -> None:
    with pytest.raises(SourceError, match="not present in fixtures"):
        fixture_source.fetch_raw("00000000-0000-0000-0000-000000000000", "W", *WINDOW)


def test_fixture_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="no stations_rhein.json"):
        FixtureGaugeSource(tmp_path)
