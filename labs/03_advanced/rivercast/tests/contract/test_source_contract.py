"""Cross-adapter contract: live and fixture adapters must be interchangeable.

The live adapter runs against a fake transport that replays the committed
fixture payload — zero network access (rule 3) — and must yield exactly the
same typed measurements and the same metadata schema as the fixture adapter
(rule 5).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rivercast.config import load_config
from rivercast.contracts.raw import RawFetchMetadata
from rivercast.sources import FixtureGaugeSource, GaugeSource, PegelOnlineSource, parse_measurements
from rivercast.sources.pegelonline import HttpResponse

KAUB_UUID = "1d26e504-7f9e-480a-b52c-5932be6549ab"
WINDOW = (
    datetime(2024, 8, 1, tzinfo=UTC),
    datetime(2024, 8, 2, tzinfo=UTC),
)


@pytest.fixture()
def fixture_source(lab_root: Path) -> FixtureGaugeSource:
    return FixtureGaugeSource(lab_root / "data_fixtures" / "pegelonline")


@pytest.fixture()
def replaying_live_source(
    configs_dir: Path, fixture_source: FixtureGaugeSource
) -> PegelOnlineSource:
    """PegelOnlineSource whose transport replays the fixture payload."""
    fixture_payload = fixture_source.fetch_raw(KAUB_UUID, "W", *WINDOW).payload

    def transport(url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        return HttpResponse(status=200, headers={}, body=fixture_payload)

    return PegelOnlineSource(load_config(configs_dir / "local.yaml").source, transport=transport)


def test_both_adapters_satisfy_the_protocol(
    fixture_source: FixtureGaugeSource, replaying_live_source: PegelOnlineSource
) -> None:
    assert isinstance(fixture_source, GaugeSource)
    assert isinstance(replaying_live_source, GaugeSource)


def test_adapters_produce_identical_typed_measurements(
    fixture_source: FixtureGaugeSource, replaying_live_source: PegelOnlineSource
) -> None:
    from_fixture = parse_measurements(fixture_source.fetch_raw(KAUB_UUID, "W", *WINDOW))
    from_live = parse_measurements(replaying_live_source.fetch_raw(KAUB_UUID, "W", *WINDOW))
    assert from_live == from_fixture
    assert len(from_live) == 96


def test_adapters_emit_the_same_metadata_schema(
    fixture_source: FixtureGaugeSource, replaying_live_source: PegelOnlineSource
) -> None:
    meta_fixture = fixture_source.fetch_raw(KAUB_UUID, "W", *WINDOW).metadata
    meta_live = replaying_live_source.fetch_raw(KAUB_UUID, "W", *WINDOW).metadata
    assert type(meta_fixture) is type(meta_live) is RawFetchMetadata
    assert set(meta_fixture.model_dump()) == set(meta_live.model_dump())
    # Same payload bytes -> same checksum, regardless of adapter.
    assert meta_fixture.sha256 == meta_live.sha256


def test_fixture_payload_matches_live_wire_format(fixture_source: FixtureGaugeSource) -> None:
    """Fixture payloads use the exact wire schema of the REST measurements endpoint."""
    rows = json.loads(fixture_source.fetch_raw(KAUB_UUID, "W", *WINDOW).payload)
    assert isinstance(rows, list) and rows
    assert set(rows[0]) == {"timestamp", "value"}
