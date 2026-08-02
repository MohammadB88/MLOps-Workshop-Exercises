"""Assemble the training dataset table and its lineage manifest (Phase 5).

``dataset_id`` is a SHA-256 over the assembled table's content plus the
lineage inputs that don't show up in the values themselves (schema/feature
version, station set, horizons, source checksums) — so the ID changes
whenever source data, features, or code changes, and training twice on
unchanged inputs reproduces the identical ID (Phase 5 acceptance criteria).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from rivercast.contracts.features import FEATURE_VERSION, SCHEMA_VERSION, DatasetManifest
from rivercast.gitinfo import current_commit


def assemble_dataset(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Join features and labels on issue time; label NaNs are kept (not dropped)."""
    if not features.index.equals(labels.index):
        raise ValueError("features and labels must share the exact same issue-time index")
    combined = features.join(labels, how="left")
    combined.index.name = "issue_time_utc"
    return combined


def training_rows(dataset: pd.DataFrame, label_columns: list[str]) -> pd.DataFrame:
    """Rows usable for training: all configured label columns must be non-null.

    Rows with unavailable labels are excluded here but remain in ``dataset``
    for live forecasting (Phase 5 acceptance criteria).
    """
    return dataset.dropna(subset=label_columns)


def _hash_dataframe(frame: pd.DataFrame) -> str:
    # Row order and index matter for reproducibility; a stable byte
    # representation of the sorted-by-index frame keeps the hash deterministic
    # across process runs regardless of upstream construction order.
    ordered = frame.sort_index()
    row_hashes = np.asarray(pd.util.hash_pandas_object(ordered, index=True))
    payload = row_hashes.tobytes()
    payload += ",".join(ordered.columns).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_manifest(
    dataset: pd.DataFrame,
    target_station_uuid: str,
    input_station_uuids: list[str],
    horizons_hours: list[int],
    source_start_utc: datetime,
    source_end_utc: datetime,
    source_checksums: list[str],
    created_at_utc: datetime | None = None,
) -> DatasetManifest:
    lineage_prefix = "|".join(
        [
            f"schema={SCHEMA_VERSION}",
            f"feature={FEATURE_VERSION}",
            f"target={target_station_uuid}",
            f"inputs={','.join(sorted(input_station_uuids))}",
            f"horizons={','.join(str(h) for h in sorted(horizons_hours))}",
            f"checksums={','.join(sorted(source_checksums))}",
        ]
    )
    content_hash = _hash_dataframe(dataset)
    dataset_id = hashlib.sha256((lineage_prefix + "|" + content_hash).encode("utf-8")).hexdigest()

    return DatasetManifest(
        dataset_id=f"sha256:{dataset_id}",
        created_at_utc=(created_at_utc or datetime.now(UTC)).isoformat(timespec="seconds"),
        source_start_utc=source_start_utc.isoformat(),
        source_end_utc=source_end_utc.isoformat(),
        target_station_uuid=target_station_uuid,
        input_station_uuids=sorted(input_station_uuids),
        horizons_hours=sorted(horizons_hours),
        row_count=len(dataset),
        source_checksums=sorted(source_checksums),
        code_commit=current_commit(),
    )
