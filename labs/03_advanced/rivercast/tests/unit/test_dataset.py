"""Dataset assembly and manifest tests: determinism, lineage, content sensitivity."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import pytest

from rivercast.processing.dataset import assemble_dataset, build_manifest

KAUB = "1d26e504-7f9e-480a-b52c-5932be6549ab"
BINGEN = "0309cd61-90c9-470e-99d4-2ee4fb2c5f84"
START = datetime(2024, 8, 1, tzinfo=UTC)


def _dataset(n: int = 5) -> pd.DataFrame:
    index = pd.DatetimeIndex([START + timedelta(hours=i) for i in range(n)], name="issue_time_utc")
    return pd.DataFrame({"kaub_level_t": [float(i) for i in range(n)]}, index=index)


def _manifest_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "target_station_uuid": KAUB,
        "input_station_uuids": [BINGEN],
        "horizons_hours": [6],
        "source_start_utc": START,
        "source_end_utc": START + timedelta(hours=5),
        "source_checksums": ["a" * 64],
        "created_at_utc": START,
    }
    base.update(overrides)
    return base


def test_assemble_requires_matching_index() -> None:
    features = _dataset(5)
    labels = _dataset(4)
    with pytest.raises(ValueError, match="exact same issue-time index"):
        assemble_dataset(features, labels)


def test_manifest_dataset_id_deterministic_for_identical_inputs() -> None:
    dataset = _dataset()
    kwargs = _manifest_kwargs(horizons_hours=[6, 12])
    first = build_manifest(dataset.copy(), **kwargs)
    second = build_manifest(dataset.copy(), **kwargs)
    assert first.dataset_id == second.dataset_id


def test_manifest_dataset_id_insensitive_to_row_order() -> None:
    dataset = _dataset()
    shuffled = dataset.iloc[::-1]
    kwargs = _manifest_kwargs()
    first = build_manifest(dataset, **kwargs)
    second = build_manifest(shuffled, **kwargs)
    assert first.dataset_id == second.dataset_id


def test_manifest_dataset_id_changes_with_content() -> None:
    kwargs = _manifest_kwargs()
    original = build_manifest(_dataset(), **kwargs)
    changed = _dataset()
    changed.iloc[0, 0] = 999.0
    mutated = build_manifest(changed, **kwargs)
    assert original.dataset_id != mutated.dataset_id


def test_manifest_dataset_id_changes_with_feature_version(monkeypatch: pytest.MonkeyPatch) -> None:
    import rivercast.processing.dataset as dataset_module

    kwargs = _manifest_kwargs()
    before = build_manifest(_dataset(), **kwargs)
    monkeypatch.setattr(dataset_module, "FEATURE_VERSION", 2)
    after = build_manifest(_dataset(), **kwargs)
    assert before.dataset_id != after.dataset_id


def test_manifest_dataset_id_changes_with_source_checksums() -> None:
    first = build_manifest(_dataset(), **_manifest_kwargs(source_checksums=["a" * 64]))
    second = build_manifest(_dataset(), **_manifest_kwargs(source_checksums=["b" * 64]))
    assert first.dataset_id != second.dataset_id


def test_manifest_records_lineage_fields() -> None:
    manifest = build_manifest(_dataset(), **_manifest_kwargs(horizons_hours=[12, 6]))
    assert manifest.horizons_hours == [6, 12]  # sorted
    assert manifest.target_station_uuid == KAUB
    assert manifest.input_station_uuids == [BINGEN]
    assert manifest.row_count == 5
    assert manifest.dataset_id.startswith("sha256:")
    assert len(manifest.short_id) == 12
